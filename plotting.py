"""Plotting module for pump performance curves with interpolation."""

import numpy as np
from scipy import interpolate
import database as db


def get_curve_data(pump_curve_id: int) -> dict:
    """Get curve data as numpy arrays for plotting."""
    points = db.get_curve_points(pump_curve_id)
    if not points:
        return None

    return {
        'flow': np.array([p['flow_gpm'] for p in points]),
        'head': np.array([p['head_ft'] for p in points]),
        'power': np.array([p['power_hp'] for p in points if p['power_hp'] is not None]),
        'rpm': np.array([p['rpm'] for p in points]),
    }


def find_parabola_intersection(flow_arr, head_arr, k):
    """
    Find where the parabola H = k*Q² intersects a pump curve.

    Args:
        flow_arr: Array of flow values for the curve
        head_arr: Array of head values for the curve
        k: Coefficient for the parabola H = k*Q²

    Returns:
        (flow, head) at intersection point, or None if not found
    """
    # Create interpolation function for the pump curve
    curve_interp = interpolate.interp1d(flow_arr, head_arr, kind='slinear',
                                         fill_value='extrapolate')

    # Find intersection: curve_head(Q) = k*Q²
    # Solve: curve_head(Q) - k*Q² = 0
    from scipy.optimize import brentq

    def residual(q):
        # if q == 0:
        #     return float('inf')
        if k == float('inf'):
            if q ==0:
                return 0
            return curve_interp(q)
        return curve_interp(q) - k * q * q

    # Search for sign change in the valid flow range
    # q_min = max(flow_arr.min(), 0)
    q_min = flow_arr.min()
    q_max = flow_arr.max()*1.05

    # Sample points to find bracket
    test_points = np.linspace(q_min, q_max, 50)
    for i in range(len(test_points)-1):
        try:
            r1 = residual(test_points[i])
            r2 = residual(test_points[i + 1])

            if r1 * r2 <= 0:  # Sign change found
                q_intersection = brentq(residual, test_points[i], test_points[i + 1])
                h_intersection = curve_interp(q_intersection)
                return q_intersection, h_intersection
        except:
            continue

    return None


def interpolate_curve(curves_data: list[dict], trim_diameters: list[float],
                      target_diameter: float, num_points: int = 50) -> dict:
    """
    Interpolate a new curve for a target trim diameter between existing curves.

    Uses affinity parabola method:
    1. For each point (Q_lower, H_lower) on the lower trim curve
    2. Draw a parabola H = k*Q² through (0,0) and (Q_lower, H_lower)
    3. Find where this parabola intersects the upper trim curve: (Q_upper, H_upper)
    4. Linearly interpolate BOTH flow and head between these two points

    Args:
        curves_data: List of curve data dicts (from get_curve_data)
        trim_diameters: List of trim diameters corresponding to each curve
        target_diameter: The desired trim diameter to interpolate
        num_points: Number of points for the interpolated curve

    Returns:
        Dict with interpolated flow, head, and power arrays
    """
    if len(curves_data) < 2:
        return None

    # Sort by trim diameter (descending - larger diameter = more flow/head)
    sorted_pairs = sorted(zip(trim_diameters, curves_data), key=lambda x: x[0], reverse=True)
    trim_diameters = [p[0] for p in sorted_pairs]
    curves_data = [p[1] for p in sorted_pairs]

    # Find the two closest trim diameters that bracket the target
    lower_idx = None
    upper_idx = None

    for i, d in enumerate(trim_diameters):
        if d >= target_diameter:
            upper_idx = i
        if d <= target_diameter:
            lower_idx = i
            break

    if lower_idx is None or upper_idx is None:
        # Target is outside the range, use closest two
        if target_diameter > trim_diameters[0]:
            upper_idx, lower_idx = 0, 1
        else:
            upper_idx, lower_idx = len(trim_diameters) - 2, len(trim_diameters) - 1

    if upper_idx == lower_idx:
        # Exact match or need adjacent curves
        if upper_idx > 0:
            upper_idx -= 1
        else:
            lower_idx += 1

    upper_curve = curves_data[upper_idx]
    lower_curve = curves_data[lower_idx]
    upper_diameter = trim_diameters[upper_idx]
    lower_diameter = trim_diameters[lower_idx]

    # Calculate interpolation factor based on diameter ratio
    # factor = 0 means lower curve, factor = 1 means upper curve
    if upper_diameter != lower_diameter:
        factor = (target_diameter - lower_diameter) / (upper_diameter - lower_diameter)
    else:
        factor = 0.5

    # Sample points along the LOWER curve
    lower_flow_samples = np.linspace(lower_curve['flow'].min(),
                                      lower_curve['flow'].max(), num_points)

    lower_head_interp = interpolate.interp1d(lower_curve['flow'], lower_curve['head'],
                                              kind='slinear', fill_value='extrapolate')

    interpolated_flow = []
    interpolated_head = []
    power_points_lower = []
    power_points_upper = []

    for q_lower in lower_flow_samples:
        h_lower = float(lower_head_interp(q_lower))

        # Skip if head or flow is non-positive
        # if h_lower <= 0 or q_lower < 0:
        #     continue

        # Calculate k for parabola passing through (0,0) and (q_lower, h_lower)
        # Parabola: H = k * Q²
        k = h_lower / (q_lower * q_lower)

        # Find intersection of this parabola with the upper curve
        intersection = find_parabola_intersection(upper_curve['flow'],
                                                   upper_curve['head'], k)

        if intersection is None:
            continue

        q_upper, h_upper = intersection

        # Linearly interpolate BOTH flow and head between the two points
        q_interp = q_lower + factor * (q_upper - q_lower)
        h_interp = h_lower + factor * (h_upper - h_lower)

        interpolated_flow.append(q_interp)
        interpolated_head.append(h_interp)

        # Store flow points for power interpolation later
        power_points_lower.append(q_lower)
        power_points_upper.append(q_upper)

    if len(interpolated_flow) < 3:
        return None

    interpolated_flow = np.array(interpolated_flow)
    interpolated_head = np.array(interpolated_head)

    # Sort by flow
    sort_idx = np.argsort(interpolated_flow)
    interpolated_flow = interpolated_flow[sort_idx]
    interpolated_head = interpolated_head[sort_idx]
    power_points_lower = np.array(power_points_lower)[sort_idx]
    power_points_upper = np.array(power_points_upper)[sort_idx]

    # Interpolate power if available
    # Use the corresponding flow points on each curve to get power, then interpolate
    interpolated_power = None
    if len(upper_curve['power']) > 0 and len(lower_curve['power']) > 0:
        try:
            upper_power_interp = interpolate.interp1d(
                upper_curve['flow'][:len(upper_curve['power'])],
                upper_curve['power'],
                kind='slinear', fill_value='extrapolate'
            )
            lower_power_interp = interpolate.interp1d(
                lower_curve['flow'][:len(lower_curve['power'])],
                lower_curve['power'],
                kind='slinear', fill_value='extrapolate'
            )

            # Get power at the corresponding flow points on each curve
            lower_power = lower_power_interp(power_points_lower)
            upper_power = upper_power_interp(power_points_upper)

            # Interpolate power between the two curves
            interpolated_power = lower_power + factor * (upper_power - lower_power)
        except:
            interpolated_power = None

    # Calculate average RPM
    avg_rpm = (upper_curve['rpm'].mean() + lower_curve['rpm'].mean()) / 2

    return {
        'flow': interpolated_flow,
        'head': interpolated_head,
        'power': interpolated_power,
        'rpm': avg_rpm,
        'trim_diameter': target_diameter,
        'interpolated_from': (lower_diameter, upper_diameter),
        'factor': factor
    }


def get_available_pumps_for_plotting() -> dict:
    """
    Get available pump names and their RPM options that have curve data.

    Returns:
        Dict mapping pump names to list of available RPMs
    """
    curves = db.get_all_pump_curves()
    pump_rpms = {}

    for c in curves:
        # Check if curve has data points
        points = db.get_curve_points(c['id'])
        if points:
            name = c['name']
            rpm = c['rpm']
            if name not in pump_rpms:
                pump_rpms[name] = set()
            pump_rpms[name].add(rpm)

    # Convert sets to sorted lists
    return {name: sorted(list(rpms)) for name, rpms in pump_rpms.items()}


def get_trim_diameters_for_pump(pump_name: str, rpm: int) -> list[float]:
    """Get all trim diameters for a pump at a specific RPM."""
    curves = db.get_curves_for_pump(pump_name, rpm)
    return sorted([c['trim_diameter'] for c in curves], reverse=True)

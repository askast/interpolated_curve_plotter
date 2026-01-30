"""SQLite database module for storing pump performance data."""

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "pump_data.db"

# Valid RPM choices
VALID_RPMS = [1160, 1760, 3500]


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Pump curves table - each row is a unique curve identified by name + trim + rpm
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pump_curves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trim_diameter REAL NOT NULL,
            rpm INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, trim_diameter, rpm)
        )
    """)

    # Curve points table - performance data points for each pump curve
    # All values stored in US units: GPM, ft, HP
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS curve_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pump_curve_id INTEGER NOT NULL,
            flow_gpm REAL NOT NULL,
            head_ft REAL NOT NULL,
            power_hp REAL,
            rpm REAL NOT NULL,
            FOREIGN KEY (pump_curve_id) REFERENCES pump_curves(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# Pump curve operations
def add_pump_curve(name: str, trim_diameter: float, rpm: int) -> int:
    """Add a new pump curve and return its ID."""
    if rpm not in VALID_RPMS:
        raise ValueError(f"RPM must be one of {VALID_RPMS}")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pump_curves (name, trim_diameter, rpm) VALUES (?, ?, ?)",
        (name, trim_diameter, rpm)
    )
    curve_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return curve_id


def get_all_pump_curves() -> list[dict]:
    """Get all pump curves."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pump_curves ORDER BY name, rpm, trim_diameter DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_pump_curve_by_id(curve_id: int) -> Optional[dict]:
    """Get a pump curve by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pump_curves WHERE id = ?", (curve_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_unique_pump_names() -> list[str]:
    """Get list of unique pump names."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM pump_curves ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [row['name'] for row in rows]


def get_curves_for_pump(name: str, rpm: Optional[int] = None) -> list[dict]:
    """Get all curves for a pump name, optionally filtered by RPM."""
    conn = get_connection()
    cursor = conn.cursor()
    if rpm:
        cursor.execute(
            "SELECT * FROM pump_curves WHERE name = ? AND rpm = ? ORDER BY trim_diameter DESC",
            (name, rpm)
        )
    else:
        cursor.execute(
            "SELECT * FROM pump_curves WHERE name = ? ORDER BY rpm, trim_diameter DESC",
            (name,)
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_pump_curve(curve_id: int) -> None:
    """Delete a pump curve and all its points."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pump_curves WHERE id = ?", (curve_id,))
    conn.commit()
    conn.close()


# Curve points operations
def add_curve_points(pump_curve_id: int, points: list[dict]) -> None:
    """Add multiple curve points for a pump curve.

    Each point dict should have: flow_gpm, head_ft, power_hp (optional), rpm
    All values should already be converted to US units.
    """
    conn = get_connection()
    cursor = conn.cursor()
    for point in points:
        cursor.execute(
            "INSERT INTO curve_points (pump_curve_id, flow_gpm, head_ft, power_hp, rpm) VALUES (?, ?, ?, ?, ?)",
            (pump_curve_id, point['flow_gpm'], point['head_ft'], point.get('power_hp'), point['rpm'])
        )
    conn.commit()
    conn.close()


def get_curve_points(pump_curve_id: int) -> list[dict]:
    """Get all curve points for a pump curve."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM curve_points WHERE pump_curve_id = ? ORDER BY flow_gpm",
        (pump_curve_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_curve_points(pump_curve_id: int) -> None:
    """Clear all curve points for a pump curve."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM curve_points WHERE pump_curve_id = ?", (pump_curve_id,))
    conn.commit()
    conn.close()


# Initialize database on module import
init_db()

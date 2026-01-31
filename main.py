"""Pump Performance Curve Plotter - Main Application with Data Entry and Plotting."""

import customtkinter as ctk
from tkinter import messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import database as db
import plotting


# Unit conversion factors to US units
FLOW_CONVERSIONS = {
    "GPM": 1.0,
    "l/s": 15.850323,
    "l/min": 0.264172,
}

HEAD_CONVERSIONS = {
    "ft": 1.0,
    "m": 3.28084,
}

POWER_CONVERSIONS = {
    "HP": 1.0,
    "W": 0.00134102,
    "kW": 1.34102,
}


def _get_standard_frequency(rpm: int) -> float:
    """Determine standard electrical frequency from pump RPM.

    60 Hz nominal speeds: ~3500, ~1760, ~1160
    50 Hz nominal speeds: ~2900, ~1500, ~950
    """
    rpm_to_freq = [
        (3500, 60), (2900, 50),
        (1760, 60), (1500, 50),
        (1160, 60), (950, 50),
    ]
    closest = min(rpm_to_freq, key=lambda x: abs(x[0] - rpm))
    return closest[1]


class DataEntryFrame(ctk.CTkFrame):
    """Frame for pump data entry."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.current_curve_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.setup_left_panel()
        self.setup_right_panel()
        self.refresh_curve_list()

    def setup_left_panel(self):
        """Setup the left panel with pump curve selection and creation."""
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        left_frame.grid_rowconfigure(3, weight=1)

        # Existing Curves Section
        curves_label = ctk.CTkLabel(
            left_frame, text="Pump Curves", font=ctk.CTkFont(size=16, weight="bold")
        )
        curves_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5))

        curve_list_frame = ctk.CTkFrame(left_frame)
        curve_list_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.curve_listbox = ctk.CTkOptionMenu(
            curve_list_frame,
            values=["-- No Curves --"],
            command=self.on_curve_selected,
            width=250
        )
        self.curve_listbox.grid(row=0, column=0, padx=5, pady=5)

        # New Curve Section
        new_curve_label = ctk.CTkLabel(
            left_frame, text="Add New Curve", font=ctk.CTkFont(size=14, weight="bold")
        )
        new_curve_label.grid(row=2, column=0, columnspan=2, padx=10, pady=(20, 5))

        new_curve_frame = ctk.CTkFrame(left_frame)
        new_curve_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="new")

        ctk.CTkLabel(new_curve_frame, text="Pump Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.pump_name_entry = ctk.CTkEntry(new_curve_frame, width=150)
        self.pump_name_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(new_curve_frame, text="Trim Diameter:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.trim_diameter_entry = ctk.CTkEntry(new_curve_frame, width=150)
        self.trim_diameter_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(new_curve_frame, text="RPM:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.rpm_menu = ctk.CTkOptionMenu(new_curve_frame, values=["1160", "1760", "3500"], width=150)
        self.rpm_menu.grid(row=2, column=1, padx=5, pady=5)
        self.rpm_menu.set("1760")

        btn_frame = ctk.CTkFrame(new_curve_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ctk.CTkButton(btn_frame, text="Add Curve", command=self.add_curve, width=100).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="Delete Selected", command=self.delete_curve, width=100,
                      fg_color="darkred", hover_color="red").grid(row=0, column=1, padx=5)

    def setup_right_panel(self):
        """Setup the right panel with data entry area."""
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(3, weight=1)

        header_label = ctk.CTkLabel(right_frame, text="Performance Data Entry",
                                     font=ctk.CTkFont(size=16, weight="bold"))
        header_label.grid(row=0, column=0, padx=10, pady=(10, 5))

        instructions = ctk.CTkLabel(right_frame,
                                     text="Paste tab-separated data: Flow, Head, Efficiency, Power, RPM\n(Efficiency column will be ignored)",
                                     font=ctk.CTkFont(size=12), text_color="gray")
        instructions.grid(row=1, column=0, padx=10, pady=5)

        # Unit selection frame
        units_frame = ctk.CTkFrame(right_frame)
        units_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        units_frame.grid_columnconfigure((0, 1, 2), weight=1)

        flow_unit_frame = ctk.CTkFrame(units_frame)
        flow_unit_frame.grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkLabel(flow_unit_frame, text="Flow:").grid(row=0, column=0, padx=2)
        self.flow_unit_menu = ctk.CTkOptionMenu(flow_unit_frame, values=list(FLOW_CONVERSIONS.keys()), width=80)
        self.flow_unit_menu.grid(row=0, column=1, padx=2)
        self.flow_unit_menu.set("GPM")

        head_unit_frame = ctk.CTkFrame(units_frame)
        head_unit_frame.grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(head_unit_frame, text="Head:").grid(row=0, column=0, padx=2)
        self.head_unit_menu = ctk.CTkOptionMenu(head_unit_frame, values=list(HEAD_CONVERSIONS.keys()), width=80)
        self.head_unit_menu.grid(row=0, column=1, padx=2)
        self.head_unit_menu.set("ft")

        power_unit_frame = ctk.CTkFrame(units_frame)
        power_unit_frame.grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkLabel(power_unit_frame, text="Power:").grid(row=0, column=0, padx=2)
        self.power_unit_menu = ctk.CTkOptionMenu(power_unit_frame, values=list(POWER_CONVERSIONS.keys()), width=80)
        self.power_unit_menu.grid(row=0, column=1, padx=2)
        self.power_unit_menu.set("HP")

        self.data_textbox = ctk.CTkTextbox(right_frame, width=400, height=300)
        self.data_textbox.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        example_data = "# Example (delete this and paste your data):\n# Flow\tHead\tEfficiency\tPower\tRPM\n100\t50\t75\t10\t1760\n200\t45\t80\t18\t1760\n300\t38\t78\t25\t1760"
        self.data_textbox.insert("1.0", example_data)

        btn_frame = ctk.CTkFrame(right_frame)
        btn_frame.grid(row=4, column=0, padx=10, pady=10)

        ctk.CTkButton(btn_frame, text="Save Data", command=self.save_data, width=120).grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="Load Existing", command=self.load_existing_data, width=120).grid(row=0, column=1, padx=5)
        ctk.CTkButton(btn_frame, text="Clear", command=self.clear_data, width=80).grid(row=0, column=2, padx=5)

        self.status_label = ctk.CTkLabel(right_frame, text="", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=5, column=0, padx=10, pady=5)

    def refresh_curve_list(self):
        curves = db.get_all_pump_curves()
        self.curves_data = {}
        for c in curves:
            label = f"{c['name']} | Ø{c['trim_diameter']} | {c['rpm']} RPM"
            self.curves_data[label] = c['id']

        if curves:
            curve_labels = list(self.curves_data.keys())
            self.curve_listbox.configure(values=curve_labels)
            self.curve_listbox.set(curve_labels[0])
            self.on_curve_selected(curve_labels[0])
        else:
            self.curve_listbox.configure(values=["-- No Curves --"])
            self.curve_listbox.set("-- No Curves --")
            self.current_curve_id = None

    def on_curve_selected(self, selection):
        if selection in self.curves_data:
            self.current_curve_id = self.curves_data[selection]
            self.status_label.configure(text=f"Selected: {selection}")
        else:
            self.current_curve_id = None

    def add_curve(self):
        name = self.pump_name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Pump name is required")
            return
        try:
            diameter = float(self.trim_diameter_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Trim diameter must be a number")
            return

        rpm = int(self.rpm_menu.get())
        try:
            db.add_pump_curve(name, diameter, rpm)
            self.pump_name_entry.delete(0, "end")
            self.trim_diameter_entry.delete(0, "end")
            self.refresh_curve_list()
            new_label = f"{name} | Ø{diameter} | {rpm} RPM"
            if new_label in self.curves_data:
                self.curve_listbox.set(new_label)
                self.on_curve_selected(new_label)
            self.status_label.configure(text=f"Added: {name} Ø{diameter} @ {rpm} RPM")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add curve: {e}")

    def delete_curve(self):
        if self.current_curve_id is None:
            messagebox.showerror("Error", "No curve selected")
            return
        if messagebox.askyesno("Confirm", "Delete this pump curve and all its data?"):
            db.delete_pump_curve(self.current_curve_id)
            self.refresh_curve_list()
            self.status_label.configure(text="Curve deleted")

    def parse_data(self, text):
        flow_factor = FLOW_CONVERSIONS[self.flow_unit_menu.get()]
        head_factor = HEAD_CONVERSIONS[self.head_unit_menu.get()]
        power_factor = POWER_CONVERSIONS[self.power_unit_menu.get()]

        points = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                parts = line.split()
            if len(parts) < 5:
                continue
            try:
                float(parts[0])
            except ValueError:
                continue
            try:
                point = {
                    'flow_gpm': float(parts[0]) * flow_factor,
                    'head_ft': float(parts[1]) * head_factor,
                    'power_hp': float(parts[3]) * power_factor if parts[3] else None,
                    'rpm': float(parts[4])
                }
                points.append(point)
            except ValueError:
                continue
        return points

    def save_data(self):
        if self.current_curve_id is None:
            messagebox.showerror("Error", "Select a pump curve first")
            return
        text = self.data_textbox.get("1.0", "end")
        points = self.parse_data(text)
        if not points:
            messagebox.showerror("Error", "No valid data points found")
            return
        db.clear_curve_points(self.current_curve_id)
        db.add_curve_points(self.current_curve_id, points)
        self.status_label.configure(text=f"Saved {len(points)} data points (converted to US units)")
        messagebox.showinfo("Success", f"Saved {len(points)} data points\nData stored in GPM, ft, HP")

    def load_existing_data(self):
        if self.current_curve_id is None:
            messagebox.showerror("Error", "Select a pump curve first")
            return
        points = db.get_curve_points(self.current_curve_id)
        self.data_textbox.delete("1.0", "end")
        if points:
            self.data_textbox.insert("1.0", "# Flow(GPM)\tHead(ft)\tPower(HP)\tRPM\n")
            for p in points:
                pwr = p['power_hp'] if p['power_hp'] is not None else ""
                self.data_textbox.insert("end", f"{p['flow_gpm']}\t{p['head_ft']}\t{pwr}\t{p['rpm']}\n")
            self.status_label.configure(text=f"Loaded {len(points)} data points (US units)")
            self.flow_unit_menu.set("GPM")
            self.head_unit_menu.set("ft")
            self.power_unit_menu.set("HP")
        else:
            self.status_label.configure(text="No existing data for this curve")

    def clear_data(self):
        self.data_textbox.delete("1.0", "end")


class PlottingFrame(ctk.CTkFrame):
    """Frame for plotting pump curves with interpolation."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_controls()
        self.setup_checkbox_panel()
        self.setup_plot_area()

    def setup_controls(self):
        """Setup the left control panel."""
        control_frame = ctk.CTkScrollableFrame(self, width=260)
        control_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)

        # Pump Selection
        ctk.CTkLabel(control_frame, text="Pump Selection",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, padx=5, pady=(10, 5))

        ctk.CTkLabel(control_frame, text="Pump:").grid(row=1, column=0, padx=5, pady=3, sticky="w")
        self.pump_name_menu = ctk.CTkOptionMenu(control_frame, values=["-- Select --"],
                                                 command=self.on_pump_selected, width=140)
        self.pump_name_menu.grid(row=1, column=1, padx=5, pady=3)

        ctk.CTkLabel(control_frame, text="RPM:").grid(row=2, column=0, padx=5, pady=3, sticky="w")
        self.rpm_menu = ctk.CTkOptionMenu(control_frame, values=["-- Select --"],
                                           command=self.on_rpm_selected, width=140)
        self.rpm_menu.grid(row=2, column=1, padx=5, pady=3)

        ctk.CTkButton(control_frame, text="Plot Curves", command=self.plot_curves,
                      width=180).grid(row=3, column=0, columnspan=2, padx=5, pady=10)

        # Interpolation Section
        ctk.CTkLabel(control_frame, text="Interpolation",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=4, column=0, columnspan=2, padx=5, pady=(20, 5))

        ctk.CTkLabel(control_frame, text="Diameter:").grid(row=5, column=0, padx=5, pady=3, sticky="w")
        self.target_diameter_entry = ctk.CTkEntry(control_frame, width=140)
        self.target_diameter_entry.grid(row=5, column=1, padx=5, pady=3)

        ctk.CTkButton(control_frame, text="Add Interpolated", command=self.add_interpolated_curve,
                      width=180).grid(row=6, column=0, columnspan=2, padx=5, pady=5)

        ctk.CTkButton(control_frame, text="Clear Interpolated", command=self.clear_interpolated,
                      width=180, fg_color="gray", hover_color="darkgray").grid(row=7, column=0, columnspan=2, padx=5, pady=3)

        # Max Motor Power Section
        ctk.CTkLabel(control_frame, text="Max Motor Power",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=8, column=0, columnspan=2, padx=5, pady=(20, 5))

        ctk.CTkLabel(control_frame, text="Power (HP):").grid(row=9, column=0, padx=5, pady=3, sticky="w")
        self.power_limit_entry = ctk.CTkEntry(control_frame, width=140)
        self.power_limit_entry.grid(row=9, column=1, padx=5, pady=3)

        ctk.CTkButton(control_frame, text="Apply Power Limit", command=self.apply_power_limit,
                      width=180).grid(row=10, column=0, columnspan=2, padx=5, pady=5)

        ctk.CTkButton(control_frame, text="Clear Power Limit", command=self.clear_power_limit,
                      width=180, fg_color="gray", hover_color="darkgray").grid(row=11, column=0, columnspan=2, padx=5, pady=3)

        # System Pressure Drop Section
        ctk.CTkLabel(control_frame, text="System Pressure Drop",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=12, column=0, columnspan=2, padx=5, pady=(20, 5))

        drop_frame = ctk.CTkFrame(control_frame)
        drop_frame.grid(row=13, column=0, columnspan=2, padx=5, pady=3, sticky="ew")

        self.pressure_drop_entry = ctk.CTkEntry(drop_frame, width=80)
        self.pressure_drop_entry.grid(row=0, column=0, padx=(5, 3), pady=3)

        self.pressure_drop_unit = ctk.CTkOptionMenu(drop_frame, values=["ft", "psi"], width=60)
        self.pressure_drop_unit.grid(row=0, column=1, padx=3, pady=3)
        self.pressure_drop_unit.set("ft")

        ctk.CTkButton(drop_frame, text="Apply", command=self._apply_pressure_drop,
                      width=60).grid(row=0, column=2, padx=(3, 5), pady=3)

        # Status
        self.status_label = ctk.CTkLabel(control_frame, text="", font=ctk.CTkFont(size=11),
                                          wraplength=240)
        self.status_label.grid(row=14, column=0, columnspan=2, padx=5, pady=10)

        # Refresh pumps list
        self.refresh_pump_list()

    def setup_checkbox_panel(self):
        """Setup the middle panel with trim and interpolated curve checkboxes."""
        cb_frame = ctk.CTkFrame(self, width=250)
        cb_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        cb_frame.grid_propagate(False)

        # Available Trims
        ctk.CTkLabel(cb_frame, text="Trim Diameters",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=10, pady=(10, 5))

        self.trims_scroll = ctk.CTkScrollableFrame(cb_frame, width=230, height=200)
        self.trims_scroll.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        self.trim_checkboxes: dict[float, ctk.BooleanVar] = {}

        # Interpolated Curves
        ctk.CTkLabel(cb_frame, text="Interpolated Curves",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=2, column=0, padx=10, pady=(20, 5))

        self.interp_scroll = ctk.CTkScrollableFrame(cb_frame, width=230, height=200)
        self.interp_scroll.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.interp_checkboxes: list[tuple[float, ctk.BooleanVar]] = []

        cb_frame.grid_rowconfigure(1, weight=1)
        cb_frame.grid_rowconfigure(3, weight=1)

    def setup_plot_area(self):
        """Setup the matplotlib plot area."""
        plot_frame = ctk.CTkFrame(self)
        plot_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        plot_frame.grid_columnconfigure(0, weight=1)
        plot_frame.grid_rowconfigure(0, weight=1)

        # Create matplotlib figure with two subplots
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.fig.set_facecolor('white')

        self.ax_head = self.fig.add_subplot(211)
        self.ax_power = self.fig.add_subplot(212)

        self.setup_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Store interpolated curve data
        self.interpolated_curves = []
        self.power_limit_data = None

    def setup_axes(self):
        """Configure the plot axes appearance."""
        for ax in [self.ax_head, self.ax_power]:
            ax.set_facecolor('white')
            ax.tick_params(colors='black')
            ax.xaxis.label.set_color('black')
            ax.yaxis.label.set_color('black')
            ax.title.set_color('black')
            for spine in ax.spines.values():
                spine.set_color('black')
            ax.grid(True, which='major', alpha=0.3)
            ax.minorticks_on()
            ax.grid(True, which='minor', alpha=0.15, linestyle=':')

        self.ax_head.set_xlabel('Flow (GPM)')
        self.ax_head.set_ylabel('Head (ft)')
        self.ax_head.set_title('Flow vs Head')

        self.ax_power.set_xlabel('Flow (GPM)')
        self.ax_power.set_ylabel('Power (HP)')
        self.ax_power.set_title('Flow vs Power')

        self.fig.tight_layout()

    def refresh_pump_list(self):
        """Refresh the available pumps dropdown."""
        self.pump_data = plotting.get_available_pumps_for_plotting()
        pump_names = list(self.pump_data.keys())

        if pump_names:
            self.pump_name_menu.configure(values=pump_names)
            self.pump_name_menu.set(pump_names[0])
            self.on_pump_selected(pump_names[0])
        else:
            self.pump_name_menu.configure(values=["-- No Data --"])
            self.pump_name_menu.set("-- No Data --")
            self.rpm_menu.configure(values=["-- Select --"])
            self.rpm_menu.set("-- Select --")

    def on_pump_selected(self, pump_name):
        """Handle pump selection - update RPM options."""
        if pump_name in self.pump_data:
            rpms = self.pump_data[pump_name]
            rpm_strs = [str(r) for r in rpms]
            self.rpm_menu.configure(values=rpm_strs)
            self.rpm_menu.set(rpm_strs[0])
            self.on_rpm_selected(rpm_strs[0])

    def on_rpm_selected(self, rpm_str):
        """Handle RPM selection - update available trims checkboxes."""
        if not hasattr(self, 'trims_scroll'):
            return
        # Clear existing checkboxes
        for widget in self.trims_scroll.winfo_children():
            widget.destroy()
        self.trim_checkboxes.clear()
        self.trim_poly_entries: dict[float, tuple[ctk.CTkEntry, ctk.CTkEntry, int]] = {}

        pump_name = self.pump_name_menu.get()
        if pump_name in self.pump_data:
            try:
                rpm = int(rpm_str)
                curves = db.get_curves_for_pump(pump_name, rpm)
                for curve in curves:
                    trim = curve['trim_diameter']
                    curve_id = curve['id']
                    head_deg, power_deg = db.get_poly_degrees(curve_id)

                    row_frame = ctk.CTkFrame(self.trims_scroll)
                    row_frame.pack(anchor="w", padx=2, pady=2, fill="x")

                    var = ctk.BooleanVar(value=True)
                    cb = ctk.CTkCheckBox(row_frame, text=f"Ø{trim}",
                                         variable=var, command=self.plot_curves, width=70)
                    cb.grid(row=0, column=0, padx=2)

                    ctk.CTkLabel(row_frame, text="H:", font=ctk.CTkFont(size=10)).grid(row=0, column=1, padx=(4, 0))
                    head_entry = ctk.CTkEntry(row_frame, width=30, font=ctk.CTkFont(size=10))
                    head_entry.insert(0, str(head_deg))
                    head_entry.grid(row=0, column=2, padx=1)

                    ctk.CTkLabel(row_frame, text="P:", font=ctk.CTkFont(size=10)).grid(row=0, column=3, padx=(4, 0))
                    power_entry = ctk.CTkEntry(row_frame, width=30, font=ctk.CTkFont(size=10))
                    power_entry.insert(0, str(power_deg))
                    power_entry.grid(row=0, column=4, padx=1)

                    # Bind enter key to save and replot
                    head_entry.bind("<Return>", lambda e, cid=curve_id, he=head_entry, pe=power_entry: self._on_poly_degree_changed(cid, he, pe))
                    power_entry.bind("<Return>", lambda e, cid=curve_id, he=head_entry, pe=power_entry: self._on_poly_degree_changed(cid, he, pe))

                    self.trim_checkboxes[trim] = var
                    self.trim_poly_entries[trim] = (head_entry, power_entry, curve_id)
            except ValueError:
                pass

        # Load saved pressure drop for this pump/RPM
        if pump_name in self.pump_data and hasattr(self, 'pressure_drop_entry'):
            try:
                rpm = int(rpm_str)
                self._load_pressure_drop(pump_name, rpm)
            except ValueError:
                pass

    def _apply_pressure_drop(self):
        """Save pressure drop to DB and replot."""
        pump_name = self.pump_name_menu.get()
        rpm_str = self.rpm_menu.get()
        if pump_name == "-- No Data --" or rpm_str == "-- Select --":
            return
        try:
            value = float(self.pressure_drop_entry.get().strip()) if self.pressure_drop_entry.get().strip() else 0.0
            rpm = int(rpm_str)
        except ValueError:
            return
        unit = self.pressure_drop_unit.get()
        db.set_pressure_drop(pump_name, rpm, value, unit)
        self.plot_curves()
        self.status_label.configure(text=f"Pressure drop saved: {value} {unit}")

    def _load_pressure_drop(self, pump_name, rpm):
        """Load pressure drop from DB into UI fields."""
        value, unit = db.get_pressure_drop(pump_name, rpm)
        self.pressure_drop_entry.delete(0, "end")
        if value:
            self.pressure_drop_entry.insert(0, str(value))
        self.pressure_drop_unit.set(unit)

    def _get_pressure_drop_ft(self) -> float:
        """Get system pressure drop converted to ft of head."""
        text = self.pressure_drop_entry.get().strip()
        if not text:
            return 0.0
        try:
            value = float(text)
        except ValueError:
            return 0.0
        if self.pressure_drop_unit.get() == "psi":
            value *= 2.31
        return value

    def _on_poly_degree_changed(self, curve_id, head_entry, power_entry):
        """Save poly degree changes to DB and replot."""
        try:
            head_deg = int(head_entry.get().strip())
            power_deg = int(power_entry.get().strip())
            db.set_poly_degrees(curve_id, head_deg, power_deg)
            self.plot_curves()
        except ValueError:
            pass

    def plot_curves(self):
        """Plot all curves for the selected pump and RPM."""
        pump_name = self.pump_name_menu.get()
        rpm_str = self.rpm_menu.get()

        if pump_name == "-- No Data --" or rpm_str == "-- Select --":
            messagebox.showerror("Error", "Please select a pump and RPM")
            return

        try:
            rpm = int(rpm_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid RPM")
            return

        # Get all curves for this pump/RPM
        curves = db.get_curves_for_pump(pump_name, rpm)
        if not curves:
            messagebox.showerror("Error", "No curves found for this selection")
            return

        # Get system pressure drop in ft
        head_loss_ft = self._get_pressure_drop_ft()

        # Clear previous plots but preserve interpolated curves
        self.ax_head.clear()
        self.ax_power.clear()
        self.setup_axes()

        # Filter to only checked trims
        if self.trim_checkboxes:
            curves = [c for c in curves if self.trim_checkboxes.get(c['trim_diameter'], ctk.BooleanVar(value=True)).get()]

        # Plot each trim diameter
        colors = plt.cm.viridis([i / max(len(curves) - 1, 1) for i in range(len(curves))]) if curves else []

        smoothed_curves_data = []
        smoothed_trim_diameters = []

        for i, curve in enumerate(curves):
            raw_data = plotting.get_curve_data(curve['id'])
            if raw_data is None:
                continue

            label = f"Ø{curve['trim_diameter']}"
            color = colors[i]

            # Get poly degrees from UI entries or DB
            head_deg, power_deg = 6, 4
            if hasattr(self, 'trim_poly_entries') and curve['trim_diameter'] in self.trim_poly_entries:
                he, pe, _ = self.trim_poly_entries[curve['trim_diameter']]
                try:
                    head_deg = int(he.get().strip())
                except ValueError:
                    pass
                try:
                    power_deg = int(pe.get().strip())
                except ValueError:
                    pass

            smooth_data = plotting.get_smoothed_curve_data(curve['id'], head_deg, power_deg)
            if smooth_data is None:
                continue

            # Apply system pressure drop
            raw_head_adj = raw_data['head'] - head_loss_ft
            smooth_data['head'] = smooth_data['head'] - head_loss_ft

            # Plot raw points + smooth fit
            self.ax_head.plot(raw_data['flow'], raw_head_adj, 'o', color=color, markersize=3)
            self.ax_head.plot(smooth_data['flow'], smooth_data['head'], '-', label=label,
                             color=color, linewidth=1)

            if len(raw_data['power']) > 0:
                pflow = raw_data['flow'][:len(raw_data['power'])]
                self.ax_power.plot(pflow, raw_data['power'], 'o', color=color, markersize=3)
            if len(smooth_data['power']) > 0:
                self.ax_power.plot(smooth_data['flow'], smooth_data['power'], '-', label=label,
                                  color=color, linewidth=1)

            smoothed_curves_data.append(smooth_data)
            smoothed_trim_diameters.append(curve['trim_diameter'])

        # Store for use by interpolation and power limit
        self._last_smoothed_curves = smoothed_curves_data
        self._last_smoothed_trims = smoothed_trim_diameters

        # Recompute interpolated curves from current (pressure-drop-adjusted) smoothed data
        if len(smoothed_curves_data) >= 2:
            new_interp = []
            for idx, old in enumerate(self.interpolated_curves):
                td = old['target_diameter']
                interp_data = plotting.interpolate_curve(
                    smoothed_curves_data, smoothed_trim_diameters, td)
                if interp_data is not None:
                    interp_data['target_diameter'] = td
                    new_interp.append(interp_data)
                else:
                    new_interp.append(old)
            self.interpolated_curves = new_interp

        # Re-draw any interpolated curves (respecting checkboxes)
        interp_colors = plt.cm.Set1(np.linspace(0, 1, max(len(self.interpolated_curves), 1)))
        for idx, interp_data in enumerate(self.interpolated_curves):
            # Check if this interpolated curve is visible
            if idx < len(self.interp_checkboxes):
                if not self.interp_checkboxes[idx][1].get():
                    continue

            label = f"Ø{interp_data['target_diameter']} (interp)"
            color = interp_colors[idx % len(interp_colors)]
            self.ax_head.plot(interp_data['flow'], interp_data['head'], '--',
                             label=label, color=color, linewidth=1.2)
            if interp_data['power'] is not None:
                self.ax_power.plot(interp_data['flow'], interp_data['power'], '--',
                                  label=label, color=color, linewidth=1.2)

        # Draw power limit based on max trim curve (smoothed)
        if self.power_limit_data is not None and smoothed_curves_data:
            power_limit = self.power_limit_data['power_limit']
            # Use the largest trim diameter smoothed curve as reference
            max_idx = smoothed_trim_diameters.index(max(smoothed_trim_diameters))
            ref_data = smoothed_curves_data[max_idx]
            if ref_data is not None and len(ref_data['power']) > 0:
                n = min(len(ref_data['flow']), len(ref_data['head']), len(ref_data['power']))
                seg_flow = []
                seg_head = []
                label_used = False
                for i in range(n):
                    q, h, p = float(ref_data['flow'][i]), float(ref_data['head'][i]), float(ref_data['power'][i])
                    if p > power_limit and p > 0:
                        r = (power_limit / p) ** (1.0 / 3.0)
                        seg_flow.append(r * q)
                        seg_head.append(r * r * h)
                    else:
                        if seg_flow:
                            lbl = "Max Motor Power" if not label_used else None
                            label_used = True
                            self.ax_head.plot(seg_flow, seg_head, '-', color='orange', linewidth=1.5, alpha=0.7, label=lbl)
                            seg_flow = []
                            seg_head = []
                if seg_flow:
                    lbl = "Max Motor Power" if not label_used else None
                    self.ax_head.plot(seg_flow, seg_head, '-', color='orange', linewidth=1.5, alpha=0.7, label=lbl)

                self.ax_power.axhline(y=power_limit, color='orange', linestyle='--', linewidth=1,
                                      label=f"Max Motor Power ({power_limit} HP)")

            # Reduced speed motor power limit for each visible interpolated curve,
            # or for max trim if no interpolated curves exist
            # At speed ratio r, available motor power = P_limit * r (linear derating)
            # Pump power at ratio r = P_original * r^3
            # Equilibrium: P_original * r^3 = P_limit * r  =>  r = sqrt(P_limit / P_original)
            visible_interps = []
            for idx, interp_data in enumerate(self.interpolated_curves):
                if idx < len(self.interp_checkboxes) and not self.interp_checkboxes[idx][1].get():
                    continue
                if interp_data['power'] is not None:
                    visible_interps.append(interp_data)

            if visible_interps:
                rs_ref_curves = [(d, d['target_diameter']) for d in visible_interps]
            else:
                # Fall back to max trim smoothed curve
                max_idx = smoothed_trim_diameters.index(max(smoothed_trim_diameters))
                rs_ref_curves = [(smoothed_curves_data[max_idx], max(smoothed_trim_diameters))]

            # Determine standard frequency from RPM
            std_freq = _get_standard_frequency(rpm)

            rs_annotations = []  # collect (tail_q, tail_h, text) for overlap avoidance

            for rs_ref, rs_diam in rs_ref_curves:
                if rs_ref is None or rs_ref.get('power') is None or len(rs_ref['power']) == 0:
                    continue
                rn = min(len(rs_ref['flow']), len(rs_ref['head']), len(rs_ref['power']))
                rs_seg_flow = []
                rs_seg_head = []
                rs_label_used = False
                tail_q = tail_h = tail_r = None
                for i in range(rn):
                    q, h, p = float(rs_ref['flow'][i]), float(rs_ref['head'][i]), float(rs_ref['power'][i])
                    if p > power_limit and p > 0:
                        r = (power_limit / p) ** 0.5
                        rq, rh = r * q, r * r * h
                        rs_seg_flow.append(rq)
                        rs_seg_head.append(rh)
                        tail_q, tail_h, tail_r = rq, rh, r
                    else:
                        if rs_seg_flow:
                            lbl = f"Ø{rs_diam} Reduced Speed Power" if not rs_label_used else None
                            rs_label_used = True
                            self.ax_head.plot(rs_seg_flow, rs_seg_head, '-', color='red', linewidth=1.5, alpha=0.7, label=lbl)
                            rs_seg_flow = []
                            rs_seg_head = []
                if rs_seg_flow:
                    lbl = f"Ø{rs_diam} Reduced Speed Power" if not rs_label_used else None
                    self.ax_head.plot(rs_seg_flow, rs_seg_head, '-', color='red', linewidth=1.5, alpha=0.7, label=lbl)

                if tail_r is not None:
                    min_freq = std_freq * tail_r
                    pct = tail_r * 100
                    txt = f"{min_freq:.1f} Hz\n{pct:.0f}%"
                    rs_annotations.append((tail_q, tail_h, txt))

            # Place annotations with vertical staggering to avoid overlap
            # Sort by head descending so we can offset downward progressively
            rs_annotations.sort(key=lambda a: a[1], reverse=True)
            for ann_idx, (aq, ah, atxt) in enumerate(rs_annotations):
                y_offset = -4 - ann_idx * 28  # stagger each label downward
                self.ax_head.annotate(
                    atxt,
                    xy=(aq, ah),
                    xytext=(8, y_offset), textcoords='offset points',
                    fontsize=8, color='red',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='red', alpha=0.8),
                    arrowprops=dict(arrowstyle='-', color='red', alpha=0.5) if ann_idx > 0 else None,
                )

        self.ax_head.legend(loc='upper right', facecolor='white', edgecolor='black', labelcolor='black')
        self.ax_power.legend(loc='upper left', facecolor='white', edgecolor='black', labelcolor='black')

        # Fix origin at 0,0, let max float with data
        for ax in [self.ax_head, self.ax_power]:
            ax.set_xlim(left=0)
            ax.set_ylim(bottom=0)

        self.fig.tight_layout()
        self.canvas.draw()
        self.status_label.configure(text=f"Plotted {len(curves)} curves for {pump_name} @ {rpm} RPM")

    def add_interpolated_curve(self):
        """Add an interpolated curve for the target diameter."""
        pump_name = self.pump_name_menu.get()
        rpm_str = self.rpm_menu.get()

        if pump_name == "-- No Data --" or rpm_str == "-- Select --":
            messagebox.showerror("Error", "Please select a pump and RPM first")
            return

        try:
            target_diameter = float(self.target_diameter_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid diameter")
            return

        try:
            rpm = int(rpm_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid RPM")
            return

        # Use smoothed curve data for interpolation
        if not hasattr(self, '_last_smoothed_curves') or len(self._last_smoothed_curves) < 2:
            messagebox.showerror("Error", "Need at least 2 trim curves plotted for interpolation. Plot curves first.")
            return

        curves_data = self._last_smoothed_curves
        trim_diameters = self._last_smoothed_trims

        # Perform interpolation
        interp_data = plotting.interpolate_curve(curves_data, trim_diameters, target_diameter)
        if interp_data is None:
            messagebox.showerror("Error", "Interpolation failed")
            return

        interp_data['target_diameter'] = target_diameter
        self.interpolated_curves.append(interp_data)

        # Add checkbox for this interpolated curve
        var = ctk.BooleanVar(value=True)
        cb = ctk.CTkCheckBox(self.interp_scroll, text=f"Ø{target_diameter} (interp)",
                             variable=var, command=self.plot_curves)
        cb.pack(anchor="w", padx=5, pady=2)
        self.interp_checkboxes.append((target_diameter, var))

        self.plot_curves()
        self.status_label.configure(
            text=f"Interpolated Ø{target_diameter} between Ø{interp_data['interpolated_from'][0]} and Ø{interp_data['interpolated_from'][1]}"
        )

    def apply_power_limit(self):
        """Apply max motor power limit to all interpolated curves."""
        try:
            power_limit = float(self.power_limit_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid power limit")
            return

        self.power_limit_data = {
            'power_limit': power_limit,
        }
        self.plot_curves()
        self.status_label.configure(text=f"Max motor power applied: {power_limit} HP")

    def clear_power_limit(self):
        """Clear max motor power limit and replot."""
        self.power_limit_data = None
        self.power_limit_entry.delete(0, "end")
        self.plot_curves()

    def clear_interpolated(self):
        """Clear interpolated curves and replot original data."""
        self.interpolated_curves = []
        for widget in self.interp_scroll.winfo_children():
            widget.destroy()
        self.interp_checkboxes.clear()
        self.plot_curves()


class PumpCurvePlotterApp(ctk.CTk):
    """Main application with tabbed interface."""

    def __init__(self):
        super().__init__()

        self.title("Pump Performance Curve Plotter")
        self.geometry("1200x800")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Add tabs
        self.tabview.add("Plotting")
        self.tabview.add("Data Entry")

        # Configure tab frames
        self.tabview.tab("Data Entry").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Data Entry").grid_rowconfigure(0, weight=1)
        self.tabview.tab("Plotting").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Plotting").grid_rowconfigure(0, weight=1)

        # Create frames for each tab
        self.data_entry_frame = DataEntryFrame(self.tabview.tab("Data Entry"))
        self.data_entry_frame.grid(row=0, column=0, sticky="nsew")

        self.plotting_frame = PlottingFrame(self.tabview.tab("Plotting"))
        self.plotting_frame.grid(row=0, column=0, sticky="nsew")

        # Refresh plotting when switching to plotting tab
        self.tabview.configure(command=self.on_tab_change)

    def on_tab_change(self):
        """Handle tab changes."""
        if self.tabview.get() == "Plotting":
            self.plotting_frame.refresh_pump_list()


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = PumpCurvePlotterApp()
    app.mainloop()


if __name__ == "__main__":
    main()

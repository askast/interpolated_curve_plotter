"""Pump Performance Curve Plotter - Main Application with Data Entry and Plotting."""

import customtkinter as ctk
from tkinter import messagebox
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
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_controls()
        self.setup_plot_area()

    def setup_controls(self):
        """Setup the left control panel."""
        control_frame = ctk.CTkFrame(self, width=280)
        control_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        control_frame.grid_propagate(False)

        # Pump Selection
        ctk.CTkLabel(control_frame, text="Pump Selection",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5))

        ctk.CTkLabel(control_frame, text="Pump Name:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pump_name_menu = ctk.CTkOptionMenu(control_frame, values=["-- Select --"],
                                                 command=self.on_pump_selected, width=150)
        self.pump_name_menu.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(control_frame, text="RPM:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.rpm_menu = ctk.CTkOptionMenu(control_frame, values=["-- Select --"],
                                           command=self.on_rpm_selected, width=150)
        self.rpm_menu.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkButton(control_frame, text="Plot Curves", command=self.plot_curves,
                      width=200).grid(row=3, column=0, columnspan=2, padx=10, pady=15)

        # Available Trims Display
        ctk.CTkLabel(control_frame, text="Available Trim Diameters:",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=4, column=0, columnspan=2, padx=10, pady=(20, 5), sticky="w")

        self.trims_scroll = ctk.CTkScrollableFrame(control_frame, width=240, height=100)
        self.trims_scroll.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.trim_checkboxes: dict[float, ctk.BooleanVar] = {}

        # Interpolation Section
        ctk.CTkLabel(control_frame, text="Interpolation",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=6, column=0, columnspan=2, padx=10, pady=(30, 5))

        ctk.CTkLabel(control_frame, text="Target Diameter:").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        self.target_diameter_entry = ctk.CTkEntry(control_frame, width=150)
        self.target_diameter_entry.grid(row=7, column=1, padx=10, pady=5)

        ctk.CTkButton(control_frame, text="Add Interpolated Curve", command=self.add_interpolated_curve,
                      width=200).grid(row=8, column=0, columnspan=2, padx=10, pady=10)

        ctk.CTkButton(control_frame, text="Clear Interpolated", command=self.clear_interpolated,
                      width=200, fg_color="gray", hover_color="darkgray").grid(row=9, column=0, columnspan=2, padx=10, pady=5)

        # Status
        self.status_label = ctk.CTkLabel(control_frame, text="", font=ctk.CTkFont(size=11),
                                          wraplength=250)
        self.status_label.grid(row=10, column=0, columnspan=2, padx=10, pady=20)

        # Refresh pumps list
        self.refresh_pump_list()

    def setup_plot_area(self):
        """Setup the matplotlib plot area."""
        plot_frame = ctk.CTkFrame(self)
        plot_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        plot_frame.grid_columnconfigure(0, weight=1)
        plot_frame.grid_rowconfigure(0, weight=1)

        # Create matplotlib figure with two subplots
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.fig.set_facecolor('#2b2b2b')

        self.ax_head = self.fig.add_subplot(211)
        self.ax_power = self.fig.add_subplot(212)

        self.setup_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Store interpolated curve data
        self.interpolated_curves = []

    def setup_axes(self):
        """Configure the plot axes appearance."""
        for ax in [self.ax_head, self.ax_power]:
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
            for spine in ax.spines.values():
                spine.set_color('white')
            ax.grid(True, alpha=0.3)

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
        # Clear existing checkboxes
        for widget in self.trims_scroll.winfo_children():
            widget.destroy()
        self.trim_checkboxes.clear()

        pump_name = self.pump_name_menu.get()
        if pump_name in self.pump_data:
            try:
                rpm = int(rpm_str)
                trims = plotting.get_trim_diameters_for_pump(pump_name, rpm)
                for trim in trims:
                    var = ctk.BooleanVar(value=True)
                    cb = ctk.CTkCheckBox(self.trims_scroll, text=f"Ø{trim}",
                                         variable=var, command=self.plot_curves)
                    cb.pack(anchor="w", padx=5, pady=2)
                    self.trim_checkboxes[trim] = var
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

        # Clear previous plots but preserve interpolated curves
        self.ax_head.clear()
        self.ax_power.clear()
        self.setup_axes()

        # Filter to only checked trims
        if self.trim_checkboxes:
            curves = [c for c in curves if self.trim_checkboxes.get(c['trim_diameter'], ctk.BooleanVar(value=True)).get()]

        # Plot each trim diameter
        colors = plt.cm.viridis([i / max(len(curves) - 1, 1) for i in range(len(curves))]) if curves else []

        for i, curve in enumerate(curves):
            data = plotting.get_curve_data(curve['id'])
            if data is None:
                continue

            label = f"Ø{curve['trim_diameter']}"
            color = colors[i]

            self.ax_head.plot(data['flow'], data['head'], 'o-', label=label,
                             color=color, markersize=4, linewidth=2)

            if len(data['power']) > 0:
                self.ax_power.plot(data['flow'][:len(data['power'])], data['power'],
                                  'o-', label=label, color=color, markersize=4, linewidth=2)

        # Re-draw any interpolated curves
        for interp_data in self.interpolated_curves:
            label = f"Ø{interp_data['target_diameter']} (interp)"
            self.ax_head.plot(interp_data['flow'], interp_data['head'], '--',
                             label=label, color='red', linewidth=2.5)
            if interp_data['power'] is not None:
                self.ax_power.plot(interp_data['flow'], interp_data['power'], '--',
                                  label=label, color='red', linewidth=2.5)

        self.ax_head.legend(loc='upper right', facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        self.ax_power.legend(loc='upper left', facecolor='#2b2b2b', edgecolor='white', labelcolor='white')

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

        # Get all curves for interpolation
        curves = db.get_curves_for_pump(pump_name, rpm)
        if len(curves) < 2:
            messagebox.showerror("Error", "Need at least 2 trim curves for interpolation")
            return

        # Get curve data
        curves_data = []
        trim_diameters = []
        for curve in curves:
            data = plotting.get_curve_data(curve['id'])
            if data is not None:
                curves_data.append(data)
                trim_diameters.append(curve['trim_diameter'])

        if len(curves_data) < 2:
            messagebox.showerror("Error", "Need at least 2 curves with data for interpolation")
            return

        # Perform interpolation
        interp_data = plotting.interpolate_curve(curves_data, trim_diameters, target_diameter)
        if interp_data is None:
            messagebox.showerror("Error", "Interpolation failed")
            return

        # Plot the interpolated curve
        label = f"Ø{target_diameter} (interp)"
        self.ax_head.plot(interp_data['flow'], interp_data['head'], '--',
                         label=label, color='red', linewidth=2.5)

        if interp_data['power'] is not None:
            self.ax_power.plot(interp_data['flow'], interp_data['power'], '--',
                              label=label, color='red', linewidth=2.5)

        self.ax_head.legend(loc='upper right', facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        self.ax_power.legend(loc='upper left', facecolor='#2b2b2b', edgecolor='white', labelcolor='white')

        # Fix origin at 0,0, let max float with data
        for ax in [self.ax_head, self.ax_power]:
            ax.set_xlim(left=0)
            ax.set_ylim(bottom=0)

        self.fig.tight_layout()
        self.canvas.draw()

        interp_data['target_diameter'] = target_diameter
        self.interpolated_curves.append(interp_data)
        self.status_label.configure(
            text=f"Interpolated Ø{target_diameter} between Ø{interp_data['interpolated_from'][0]} and Ø{interp_data['interpolated_from'][1]}"
        )

    def clear_interpolated(self):
        """Clear interpolated curves and replot original data."""
        self.interpolated_curves = []
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
        self.tabview.add("Data Entry")
        self.tabview.add("Plotting")

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
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = PumpCurvePlotterApp()
    app.mainloop()


if __name__ == "__main__":
    main()

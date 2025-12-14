#!/usr/bin/env python3
"""
Matplotlib-based plotting for telemetry data with intelligent time axis formatting
"""

import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Matplotlib imports for professional plotting
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates

logger = logging.getLogger(__name__)

class TelemetryPlotter:
    """Professional plotter for telemetry data using matplotlib with intelligent time axis formatting"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF']
        
    def show_plot_dialog(self, preselect_node_id=None, parent_window=None):
        """Show plot configuration dialog
        
        Args:
            preselect_node_id: Optional node ID to pre-select (all others will be deselected)
            parent_window: Optional parent window to position relative to (e.g., node detail window)
        """
        try:
            # First get available nodes
            available_nodes = self.get_available_nodes()
            if not available_nodes:
                tk.messagebox.showwarning("No Data", "No nodes with historical data found.")
                return
                
            # Show configuration dialog
            config = self.show_config_dialog(available_nodes, preselect_node_id, parent_window)
            if not config:
                return  # User cancelled
                
            # Get data based on user selection
            data = self.load_telemetry_data(config['nodes'], config['days'], config['parameter'])
            if not data:
                param_name = config['parameter'].replace('_', ' ').title()
                tk.messagebox.showwarning("No Data", f"No {param_name} data found for selected criteria.")
                return
                
            # Create plot window
            self.create_plot_window(data, config)
            
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            tk.messagebox.showerror("Plot Error", f"Failed to create plot: {e}")
    

    
    def get_available_nodes(self):
        """Get list of nodes that have log data"""
        log_dir = Path(self.config_manager.get('data.log_directory', 'logs'))
        available_nodes = {}
        
        if not log_dir.exists():
            return {}
            
        for node_dir in log_dir.iterdir():
            if not node_dir.is_dir():
                continue
                
            node_id = node_dir.name
            year_dir = node_dir / "2025"
            
            if year_dir.exists() and any(year_dir.glob("*.csv")):
                # Try to get node info from most recent CSV
                node_info = None
                for csv_file in sorted(year_dir.glob("*.csv"), reverse=True):
                    try:
                        with open(csv_file, 'r') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                long_name = row.get('long_name', '').strip()
                                short_name = row.get('short_name', '').strip()
                                if long_name and long_name != 'Unknown Node':
                                    node_info = {'long_name': long_name, 'short_name': short_name}
                                    break
                            if node_info:
                                break
                    except:
                        continue
                
                if not node_info:
                    node_info = {'long_name': 'Unknown', 'short_name': node_id[-4:]}
                    
                available_nodes[node_id] = node_info
        
        return available_nodes
    
    def show_config_dialog(self, available_nodes, preselect_node_id=None, parent_window=None):
        """Show configuration dialog for plot options
        
        Args:
            available_nodes: Dict of available nodes
            preselect_node_id: Optional node ID to pre-select (all others will be deselected)
            parent_window: Optional parent window to position relative to
        """
        dialog = tk.Toplevel(self.parent)
        dialog.title("Plot Configuration")
        dialog.geometry("450x560")  # Reduced from 800 to 560 (30% reduction)
        dialog.configure(bg='#1e1e1e')
        dialog.transient(self.parent)
        dialog.grab_set()
        dialog.resizable(True, True)
        
        # Position dialog relative to parent_window if provided
        if parent_window:
            dialog.update_idletasks()  # Ensure geometry is calculated
            
            # Get parent window position and size
            parent_x = parent_window.winfo_x()
            parent_y = parent_window.winfo_y()
            
            # Position slightly down and to the right (30px down, 40px right)
            x = parent_x + 40
            y = parent_y + 30
            
            dialog.geometry(f"450x560+{x}+{y}")
        
        result = {}
        
        # Title - smaller font
        title_label = tk.Label(dialog, text="Telemetry Plot Configuration", 
                              bg='#1e1e1e', fg='white', font=("Arial", 11, "bold"))  # Reduced from 14 to 11
        title_label.pack(pady=5)  # Reduced padding from 10 to 5
        
        # Parameter selection
        param_frame = tk.LabelFrame(dialog, text="Parameter to Plot", bg='#2d2d2d', fg='white')
        param_frame.pack(fill="x", padx=20, pady=(0, 5))  # Reduced padding
        
        param_var = tk.StringVar(value="temperature")
        param_options = [
            ("Temperature (°C)", "temperature"),
            ("SNR (dB)", "snr"),
            ("Humidity (%)", "humidity"), 
            ("Internal Battery Voltage (V)", "internal_voltage"),
            ("External Battery Voltage (V)", "external_voltage"),
            ("Current (mA)", "current"),
            ("Channel Utilization (%)", "channel_utilization")
        ]
        
        # Create two columns for parameter options
        left_col = tk.Frame(param_frame, bg='#2d2d2d')
        right_col = tk.Frame(param_frame, bg='#2d2d2d')
        left_col.pack(side="left", fill="both", expand=True, padx=(10, 5))
        right_col.pack(side="right", fill="both", expand=True, padx=(5, 10))
        
        for i, (text, value) in enumerate(param_options):
            parent = left_col if i < 3 else right_col
            rb = tk.Radiobutton(parent, text=text, variable=param_var, value=value,
                               bg='#2d2d2d', fg='white', selectcolor='#404040',
                               activebackground='#2d2d2d', activeforeground='white')
            rb.pack(anchor="w", pady=2)
        
        # Time window selection - two column layout
        time_frame = tk.LabelFrame(dialog, text="Time Window", bg='#2d2d2d', fg='white')
        time_frame.pack(fill="x", padx=20, pady=(0, 5))  # Reduced padding
        
        time_var = tk.StringVar(value="7")
        
        # Create two-column layout
        time_cols = tk.Frame(time_frame, bg='#2d2d2d')
        time_cols.pack(fill="x", padx=5, pady=5)
        
        col1 = tk.Frame(time_cols, bg='#2d2d2d')
        col1.pack(side="left", fill="both", expand=True)
        
        col2 = tk.Frame(time_cols, bg='#2d2d2d')
        col2.pack(side="left", fill="both", expand=True)
        
        # Left column options
        left_options = [
            ("Last 24 hours", "1"),
            ("Last 3 days", "3"),
            ("Last week", "7")
        ]
        
        # Right column options
        right_options = [
            ("Last 2 weeks", "14"),
            ("Last month", "30"),
            ("All available", "all")
        ]
        
        for text, value in left_options:
            rb = tk.Radiobutton(col1, text=text, variable=time_var, value=value,
                               bg='#2d2d2d', fg='white', selectcolor='#404040',
                               activebackground='#2d2d2d', activeforeground='white')
            rb.pack(anchor="w", padx=10, pady=2)
        
        for text, value in right_options:
            rb = tk.Radiobutton(col2, text=text, variable=time_var, value=value,
                               bg='#2d2d2d', fg='white', selectcolor='#404040',
                               activebackground='#2d2d2d', activeforeground='white')
            rb.pack(anchor="w", padx=10, pady=2)
        
        # Node selection - restored to original height
        node_frame = tk.LabelFrame(dialog, text="Select Nodes", bg='#2d2d2d', fg='white', height=180)
        node_frame.pack(fill="x", padx=20, pady=(0, 10))
        node_frame.pack_propagate(False)  # Prevent frame from shrinking/expanding
        
        # "Select All" checkbox - default to True unless pre-selecting a specific node
        select_all_default = (preselect_node_id is None)
        select_all_var = tk.BooleanVar(value=select_all_default)
        select_all_cb = tk.Checkbutton(node_frame, text="All Nodes", variable=select_all_var,
                                      bg='#2d2d2d', fg='white', selectcolor='#404040',
                                      activebackground='#2d2d2d', activeforeground='white',
                                      font=("Liberation Sans", 12))
        select_all_cb.pack(anchor="w", padx=10, pady=3)
        
        # Individual node checkboxes
        node_vars = {}
        node_checkboxes = []
        
        # Create scrollable frame for nodes
        canvas = tk.Canvas(node_frame, bg='#2d2d2d', highlightthickness=0, height=130)
        scrollbar = tk.Scrollbar(node_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2d2d2d')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Debug: Log preselection info
        if preselect_node_id:
            logger.info(f"Preselecting node: {preselect_node_id}")
            logger.info(f"Available nodes: {list(available_nodes.keys())}")
        
        for node_id, node_info in available_nodes.items():
            # If preselect_node_id is specified, only select that node
            should_select = (node_id == preselect_node_id) if preselect_node_id else True
            var = tk.BooleanVar(value=should_select)
            node_vars[node_id] = var
            
            # Debug: Log selection decision
            if preselect_node_id:
                logger.debug(f"Node {node_id}: should_select={should_select} (comparing with {preselect_node_id})")
            
            display_name = f"{node_info['long_name']} ({node_info['short_name']})"
            cb = tk.Checkbutton(scrollable_frame, text=display_name, variable=var,
                               bg='#2d2d2d', fg='white', selectcolor='#404040',
                               activebackground='#2d2d2d', activeforeground='white',
                               font=("Liberation Sans", 12))
            cb.pack(anchor="w", padx=10, pady=2)
            node_checkboxes.append(cb)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Select all functionality
        def toggle_all():
            select_all = select_all_var.get()
            for var in node_vars.values():
                var.set(select_all)
        
        select_all_cb.configure(command=toggle_all)
        
        # Buttons - reduced padding
        button_frame = tk.Frame(dialog, bg='#1e1e1e')
        button_frame.pack(fill="x", padx=20, pady=10, side="bottom")  # Reduced padding from 20 to 10
        
        def on_ok():
            selected_nodes = [node_id for node_id, var in node_vars.items() if var.get()]
            if not selected_nodes:
                tk.messagebox.showwarning("No Selection", "Please select at least one node.")
                return
                
            result['nodes'] = selected_nodes
            # Handle 'all' for all available data, otherwise convert to int
            time_value = time_var.get()
            result['days'] = time_value if time_value == 'all' else int(time_value)
            result['parameter'] = param_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Buttons - enlarged for touch input
        tk.Button(button_frame, text="Cancel", command=on_cancel,
                 bg='#404040', fg='white', width=12, height=2).pack(side="right", padx=(10, 0))
        tk.Button(button_frame, text="Plot", command=on_ok,
                 bg='#404040', fg='white', width=12, height=2).pack(side="right")
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result if result else None
    
    def load_telemetry_data(self, selected_nodes, days, parameter):
        """Load telemetry data for selected nodes and time period"""
        log_dir = Path(self.config_manager.get('data.log_directory', 'logs'))
        
        # Calculate date range - use full days (midnight to midnight)
        # End at the END of today (23:59:59)
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if days == 'all':
            # Start from a very early date to capture all data
            start_date = datetime(2020, 1, 1)
        else:
            # Start at the BEGINNING of the start day (00:00:00)
            start_date = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        all_data = {}
        
        for node_id in selected_nodes:
            node_dir = log_dir / node_id
            if not node_dir.exists():
                continue
                
            node_data = []
            node_info = None
            
            # Check 2025 subdirectory
            year_dir = node_dir / "2025"
            if not year_dir.exists():
                continue
                
            # Read files for the selected time period
            current_date = start_date
            while current_date <= end_date:
                csv_file = year_dir / f"{current_date.strftime('%Y%m%d')}.csv"
                if csv_file.exists():
                    data, info = self.read_telemetry_from_csv(csv_file, start_date, end_date, parameter)
                    node_data.extend(data)
                    if info and node_info is None:
                        node_info = info
                current_date += timedelta(days=1)
            
            if node_data:
                # Store both data and node info
                all_data[node_id] = {
                    'data': sorted(node_data, key=lambda x: x[0]),  # Sort by timestamp
                    'info': node_info or {'long_name': 'Unknown', 'short_name': node_id[-4:]}
                }
        
        return all_data
    
    def read_telemetry_from_csv(self, csv_file, start_date, end_date, parameter):
        """Read telemetry data from a single CSV file"""
        data = []
        node_info = None
        
        # Map parameter names to CSV column names
        param_map = {
            'temperature': 'temperature',
            'snr': 'snr',
            'humidity': 'humidity',
            'internal_voltage': 'voltage',
            'external_voltage': 'ch3_voltage',
            'current': 'current',
            'channel_utilization': 'channel_utilization'
        }
        
        csv_column = param_map.get(parameter, parameter)
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        # Parse timestamp
                        timestamp = datetime.fromisoformat(row['iso_time'].replace('Z', '+00:00'))
                        
                        # Check if in date range
                        if not (start_date <= timestamp <= end_date):
                            continue
                        
                        # Get node names (use first valid entry found)
                        if node_info is None:
                            long_name = row.get('long_name', '').strip()
                            short_name = row.get('short_name', '').strip()
                            if long_name and long_name != 'Unknown Node':
                                node_info = {'long_name': long_name, 'short_name': short_name}
                            
                        # Get parameter value from CSV column
                        value_str = row.get(csv_column, '').strip()
                        
                        if value_str and value_str != '':
                            value = float(value_str)
                            data.append((timestamp, value))
                            
                    except (ValueError, KeyError) as e:
                        # Skip malformed rows
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading {csv_file}: {e}")
            
        return data, node_info
    
    def create_plot_window(self, data, config):
        """Create matplotlib plot window with intelligent time axis formatting"""
        # Create window
        plot_window = tk.Toplevel(self.parent)
        
        # Parameter info for axis labels and ranges
        param_info = {
            'temperature': {'name': 'Temperature', 'unit': '°C', 'min_val': 0, 'max_val': 50},
            'snr': {'name': 'SNR', 'unit': 'dB', 'min_val': -15, 'max_val': 15},
            'humidity': {'name': 'Humidity', 'unit': '%', 'min_val': 0, 'max_val': 100},
            'internal_voltage': {'name': 'Internal Battery Voltage', 'unit': 'V', 'min_val': 3.0, 'max_val': 4.5},
            'external_voltage': {'name': 'External Battery Voltage', 'unit': 'V', 'min_val': 10, 'max_val': 15},
            'current': {'name': 'Current', 'unit': 'mA', 'min_val': 0, 'max_val': 200},
            'channel_utilization': {'name': 'Channel Utilization', 'unit': '%', 'min_val': 0, 'max_val': 50}
        }
        
        # Window title
        time_desc = {
            1: "24 Hours", 3: "3 Days", 7: "7 Days", 14: "2 Weeks", 30: "30 Days"
        }
        param_name = param_info[config['parameter']]['name']
        days_text = time_desc.get(config['days'], "All Available" if config['days'] == 'all' else f"{config['days']} Days")
        plot_window.title(f"{param_name} Plot - Last {days_text}")
        plot_window.geometry("1000x700")
        plot_window.configure(bg='#1e1e1e')
        
        # Create matplotlib figure with dark theme
        fig = Figure(figsize=(10, 7), facecolor='#1e1e1e')
        ax = fig.add_subplot(111, facecolor='#2d2d2d')
        
        # Get parameter details
        info = param_info[config['parameter']]
        
        # Plot each node's data and store line references for hover annotations
        plot_lines = []
        for node_id, node_entry in data.items():
            node_data = node_entry['data']
            node_info = node_entry['info']
            
            if not node_data:
                continue
            
            # Extract timestamps and values
            timestamps = [point[0] for point in node_data]
            values = [point[1] for point in node_data]
            
            # Plot with node label
            label = f"{node_info['long_name']} ({node_info['short_name']})"
            line, = ax.plot(timestamps, values, 'o-', label=label, markersize=4, linewidth=1.5, picker=5)
            plot_lines.append((line, timestamps, values, label))
        
        # Configure axes
        ax.set_xlabel('Time', color='white', fontsize=12)
        ax.set_ylabel(f"{info['name']} ({info['unit']})", color='white', fontsize=12)
        ax.set_title(f"{info['name']} vs Time (Last {days_text})",
                     color='white', fontsize=14, fontweight='bold', pad=20)
        
        # Set Y-axis range
        ax.set_ylim(info['min_val'], info['max_val'])
        
        # Use the REQUESTED time window (not actual data span) for consistent formatting
        requested_days = config['days']
        if requested_days == 'all':
            # Calculate actual span for 'all' mode
            all_times = []
            for node_entry in data.values():
                all_times.extend([point[0] for point in node_entry['data']])
            if all_times:
                requested_days = (max(all_times) - min(all_times)).days + 1
            else:
                requested_days = 7  # default
        
        # Format based on requested time window
        if requested_days <= 1:  # 24 hours or less
            # Major ticks every 3 hours at :00, minor every hour
            major_locator = mdates.HourLocator(byhour=range(0, 24, 3))
            minor_locator = mdates.HourLocator()
            formatter = mdates.DateFormatter('%H:%M')
        elif requested_days <= 3:  # 1-3 days
            # Major ticks at midnight each day, minor every 6 hours
            major_locator = mdates.DayLocator()
            minor_locator = mdates.HourLocator(byhour=[0, 6, 12, 18])
            formatter = mdates.DateFormatter('%m/%d\n%H:%M')
        elif requested_days <= 7:  # 3-7 days
            # Major ticks at midnight each day, minor every 6 hours
            major_locator = mdates.DayLocator()
            minor_locator = mdates.HourLocator(byhour=[0, 6, 12, 18])
            formatter = mdates.DateFormatter('%m/%d\n%H:%M')
        elif requested_days <= 14:  # 7-14 days
            # Major ticks at midnight each day, minor every 12 hours
            major_locator = mdates.DayLocator()
            minor_locator = mdates.HourLocator(byhour=[0, 12])
            formatter = mdates.DateFormatter('%m/%d')
        elif requested_days <= 30:  # 14-30 days
            # Major ticks every 2 days, minor daily
            major_locator = mdates.DayLocator(interval=2)
            minor_locator = mdates.DayLocator()
            formatter = mdates.DateFormatter('%m/%d')
        else:  # More than 30 days
            # Major ticks weekly, minor every 2 days
            major_locator = mdates.WeekdayLocator()
            minor_locator = mdates.DayLocator(interval=2)
            formatter = mdates.DateFormatter('%m/%d')
        
        ax.xaxis.set_major_locator(major_locator)
        ax.xaxis.set_major_formatter(formatter)
        if minor_locator:
            ax.xaxis.set_minor_locator(minor_locator)
        
        # Set x-axis limits to show the FULL requested time range (not just data range)
        # This makes data gaps obvious
        now = datetime.now()
        if requested_days == 'all':
            # For 'all', use actual data range
            all_times = []
            for node_entry in data.values():
                all_times.extend([point[0] for point in node_entry['data']])
            if all_times:
                ax.set_xlim(mdates.date2num(min(all_times)), mdates.date2num(max(all_times)))
        else:
            # For specific time windows, show the full requested range
            x_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            x_start = (now - timedelta(days=requested_days)).replace(hour=0, minute=0, second=0, microsecond=0)
            ax.set_xlim(mdates.date2num(x_start), mdates.date2num(x_end))
        
        # Rotate date labels for better readability
        fig.autofmt_xdate(rotation=45, ha='right')
        
        # Style the axes with both major and minor ticks
        ax.tick_params(axis='x', colors='white', labelsize=10, which='major', length=6)
        ax.tick_params(axis='x', colors='white', which='minor', length=3)
        ax.tick_params(axis='y', colors='white', labelsize=10)
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add professional gridlines - major (solid) and minor (dotted, brighter)
        ax.grid(True, which='major', alpha=0.35, color='#888888', linestyle='-', linewidth=0.8)
        ax.grid(True, which='minor', alpha=0.35, color='#777777', linestyle=':', linewidth=0.7)
        
        # Legend with dark theme
        legend = ax.legend(loc='upper left', framealpha=0.9, facecolor='#2d2d2d',
                          edgecolor='white', fontsize=10)
        for text in legend.get_texts():
            text.set_color('white')
        
        # Tight layout to prevent label cutoff
        fig.tight_layout()
        
        # Add hover annotation for data point display
        annot = ax.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                           bbox=dict(boxstyle="round,pad=0.5", fc="#2d2d2d", ec="white", alpha=0.95),
                           arrowprops=dict(arrowstyle="->", color="white"),
                           color='white', fontsize=10, visible=False)
        
        def update_annot(line, x_val, y_val, label):
            """Update annotation with data point info"""
            annot.xy = (x_val, y_val)
            # Format time nicely
            time_str = mdates.num2date(x_val).strftime('%Y-%m-%d %H:%M')
            text = f"{label}\n{time_str}\n{info['name']}: {y_val:.2f} {info['unit']}"
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor('#2d2d2d')
            annot.get_bbox_patch().set_alpha(0.95)
        
        def on_hover(event):
            """Handle mouse hover events"""
            if event.inaxes == ax:
                for line, timestamps, values, label in plot_lines:
                    cont, ind = line.contains(event)
                    if cont:
                        # Get the closest point
                        idx = ind["ind"][0]
                        x_val = mdates.date2num(timestamps[idx])
                        y_val = values[idx]
                        update_annot(line, x_val, y_val, label)
                        annot.set_visible(True)
                        canvas.draw_idle()
                        return
            annot.set_visible(False)
            canvas.draw_idle()
        
        # Embed matplotlib figure in tkinter window
        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Connect hover event
        canvas.mpl_connect("motion_notify_event", on_hover)
        
        # Add navigation toolbar (zoom, pan, save)
        toolbar = NavigationToolbar2Tk(canvas, plot_window)
        toolbar.config(background='#2d2d2d')
        toolbar._message_label.config(background='#2d2d2d', foreground='white')
        toolbar.update()
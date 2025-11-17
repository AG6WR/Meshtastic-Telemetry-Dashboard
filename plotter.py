#!/usr/bin/env python3
"""
Simple tkinter-based plotting for telemetry data
"""

import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TelemetryPlotter:
    """Simple plotter for telemetry data using tkinter Canvas"""
    
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
            ("Voltage (V)", "voltage"),
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
        
        # Time window selection
        time_frame = tk.LabelFrame(dialog, text="Time Window", bg='#2d2d2d', fg='white')
        time_frame.pack(fill="x", padx=20, pady=(0, 5))  # Reduced padding
        
        time_var = tk.StringVar(value="7")
        time_options = [
            ("Last 24 hours", "1"),
            ("Last 3 days", "3"), 
            ("Last week", "7"),
            ("Last 2 weeks", "14"),
            ("Last month", "30")
        ]
        
        for text, value in time_options:
            rb = tk.Radiobutton(time_frame, text=text, variable=time_var, value=value,
                               bg='#2d2d2d', fg='white', selectcolor='#404040',
                               activebackground='#2d2d2d', activeforeground='white')
            rb.pack(anchor="w", padx=10, pady=2)
        
        # Node selection - reduced height for smaller displays
        node_frame = tk.LabelFrame(dialog, text="Select Nodes", bg='#2d2d2d', fg='white', height=180)  # Reduced from 300 to 180
        node_frame.pack(fill="x", padx=20, pady=(0, 10))  # Reduced bottom padding from 20 to 10
        node_frame.pack_propagate(False)  # Prevent frame from shrinking/expanding
        
        # "Select All" checkbox - default to True unless pre-selecting a specific node
        select_all_default = (preselect_node_id is None)
        select_all_var = tk.BooleanVar(value=select_all_default)
        select_all_cb = tk.Checkbutton(node_frame, text="All Nodes", variable=select_all_var,
                                      bg='#2d2d2d', fg='white', selectcolor='#404040',
                                      activebackground='#2d2d2d', activeforeground='white')
        select_all_cb.pack(anchor="w", padx=10, pady=3)  # Reduced padding from 5 to 3
        
        # Individual node checkboxes
        node_vars = {}
        node_checkboxes = []
        
        # Create scrollable frame for nodes with reduced height
        canvas = tk.Canvas(node_frame, bg='#2d2d2d', highlightthickness=0, height=130)  # Reduced from 220 to 130
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
                               activebackground='#2d2d2d', activeforeground='white')
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
            result['days'] = int(time_var.get())
            result['parameter'] = param_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        tk.Button(button_frame, text="Cancel", command=on_cancel,
                 bg='#404040', fg='white', width=10, height=2).pack(side="right", padx=(10, 0))
        tk.Button(button_frame, text="Plot", command=on_ok,
                 bg='#404040', fg='white', width=10, height=2).pack(side="right")
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return result if result else None
    
    def load_telemetry_data(self, selected_nodes, days, parameter):
        """Load telemetry data for selected nodes and time period"""
        log_dir = Path(self.config_manager.get('data.log_directory', 'logs'))
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
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
            'voltage': 'voltage',  # Will be handled specially below
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
                            
                        # Get parameter value
                        # Special handling for voltage: prefer ch3_voltage (external) over voltage (internal)
                        # This matches the card view logic in get_battery_percentage_display()
                        if parameter == 'voltage':
                            value_str = row.get('ch3_voltage', '').strip()
                            if not value_str or value_str == '':
                                value_str = row.get('voltage', '').strip()
                        else:
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
        """Create the plot window with telemetry data"""
        # Create window
        plot_window = tk.Toplevel(self.parent)
        
        # Parameter info
        param_info = {
            'temperature': {'name': 'Temperature', 'unit': '°C', 'min_val': 0, 'max_val': 50, 'auto_scale': False},
            'snr': {'name': 'SNR', 'unit': 'dB', 'min_val': -15, 'max_val': 15, 'auto_scale': False},
            'humidity': {'name': 'Humidity', 'unit': '%', 'min_val': 0, 'max_val': 100, 'auto_scale': False},
            'voltage': {'name': 'Voltage', 'unit': 'V', 'min_val': 10, 'max_val': 15, 'auto_scale': False},
            'current': {'name': 'Current', 'unit': 'mA', 'min_val': 0, 'max_val': 200, 'auto_scale': False},
            'channel_utilization': {'name': 'Channel Utilization', 'unit': '%', 'min_val': 0, 'max_val': 50, 'auto_scale': False}
        }
        
        # Dynamic title based on time window
        time_desc = {
            1: "24 Hours",
            3: "3 Days", 
            7: "7 Days",
            14: "2 Weeks",
            30: "30 Days"
        }
        
        param_name = param_info[config['parameter']]['name']
        days_text = time_desc.get(config['days'], f"{config['days']} Days")
        title = f"{param_name} Plot - Last {days_text}"
        plot_window.title(title)
        plot_window.geometry("900x600")
        plot_window.configure(bg='#1e1e1e')
        
        # Create canvas
        canvas = tk.Canvas(plot_window, bg='#2d2d2d', highlightthickness=0)
        canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Plot after window is visible
        plot_window.after(100, lambda: self.draw_plot(canvas, data, config, param_info[config['parameter']]))
    
    def draw_plot(self, canvas, data, config, param_info):
        """Draw the telemetry plot on canvas"""
        canvas.update_idletasks()
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
            
        # Margins
        margin_left = 80
        margin_right = 250  # Extra space for legend outside plot area
        margin_top = 40
        margin_bottom = 60
        
        plot_width = width - margin_left - margin_right
        plot_height = height - margin_top - margin_bottom
        
        if plot_width <= 0 or plot_height <= 0:
            return
            
        # Clear canvas
        canvas.delete("all")
        
        # Find overall time range
        all_times = []
        for node_entry in data.values():
            node_data = node_entry['data']
            all_times.extend([point[0] for point in node_data])
            
        if not all_times:
            canvas.create_text(width//2, height//2, text="No data to plot", fill="white", font=("Arial", 14))
            return
            
        min_time = min(all_times)
        max_time = max(all_times)
        time_range = (max_time - min_time).total_seconds()
        
        # Y-axis: dynamic range based on parameter
        min_val = param_info['min_val']
        max_val = param_info['max_val']
        unit = param_info['unit']
        
        # Auto-scaling for certain parameters
        if param_info.get('auto_scale', False):
            # Find actual data range
            all_values = []
            for node_entry in data.values():
                node_data = node_entry['data']
                all_values.extend([point[1] for point in node_data])
            
            if all_values:
                data_min = min(all_values)
                data_max = max(all_values)
                
                # Apply minimum range requirement
                min_range = param_info.get('min_range', 1)
                if (data_max - data_min) < min_range:
                    center = (data_max + data_min) / 2
                    min_val = max(0, center - min_range / 2)
                    max_val = min_val + min_range
                else:
                    # Add 5% padding
                    padding = (data_max - data_min) * 0.05
                    min_val = max(0, data_min - padding)
                    max_val = data_max + padding
        
        # Draw axes
        # Y-axis
        canvas.create_line(margin_left, margin_top, margin_left, height - margin_bottom, fill="white", width=2)
        # X-axis  
        canvas.create_line(margin_left, height - margin_bottom, width - margin_right, height - margin_bottom, fill="white", width=2)
        
        # Y-axis labels
        num_ticks = 6
        step = (max_val - min_val) / (num_ticks - 1)
        for i in range(num_ticks):
            val = min_val + i * step
            y = height - margin_bottom - (val - min_val) / (max_val - min_val) * plot_height
            canvas.create_line(margin_left - 5, y, margin_left + 5, y, fill="white")
            canvas.create_text(margin_left - 15, y, text=f"{val:.1f}{unit}", fill="white", anchor="e", font=("Arial", 10))
        
        # X-axis labels (show dates)
        num_labels = 7  # Show 7 date labels
        for i in range(num_labels + 1):
            label_time = min_time + timedelta(seconds=time_range * i / num_labels)
            x = margin_left + (i / num_labels) * plot_width
            canvas.create_line(x, height - margin_bottom - 5, x, height - margin_bottom + 5, fill="white")
            canvas.create_text(x, height - margin_bottom + 20, text=label_time.strftime("%m/%d"), 
                             fill="white", anchor="center", font=("Arial", 10))
        
        # Plot title
        time_desc = {
            1: "24 Hours",
            3: "3 Days", 
            7: "7 Days",
            14: "2 Weeks",
            30: "30 Days"
        }
        days_text = time_desc.get(config['days'], f"{config['days']} Days")
        title_text = f"{param_info['name']} vs Time (Last {days_text})"
        canvas.create_text(width//2, 20, text=title_text, 
                         fill="white", font=("Arial", 16, "bold"))
        
        # Plot data for each node
        color_idx = 0
        legend_y = margin_top + 20
        
        for node_id, node_entry in data.items():
            node_data = node_entry['data']
            node_info = node_entry['info']
            
            if not node_data:
                continue
                
            color = self.colors[color_idx % len(self.colors)]
            color_idx += 1
            
            # Draw data points and lines
            points = []
            for timestamp, value in node_data:
                # Skip points outside the Y-axis range
                if value < min_val or value > max_val:
                    continue
                
                # Convert to canvas coordinates
                time_offset = (timestamp - min_time).total_seconds()
                x = margin_left + (time_offset / time_range) * plot_width
                y = height - margin_bottom - (value - min_val) / (max_val - min_val) * plot_height
                
                points.append((x, y))
                
                # Draw point
                canvas.create_oval(x-2, y-2, x+2, y+2, fill=color, outline=color)
            
            # Skip connecting lines - plot points only
            
            # Legend - positioned outside plot area (right side)
            legend_x = margin_left + plot_width + 20  # Start 20px to the right of plot area
            canvas.create_line(legend_x, legend_y, legend_x + 20, legend_y, fill=color, width=3)
            
            # Format legend text: "Long Name (short)"
            long_name = node_info['long_name']
            short_name = node_info['short_name']
            legend_text = f"{long_name} ({short_name})"
            
            canvas.create_text(legend_x + 25, legend_y, text=legend_text, 
                             fill="white", anchor="w", font=("Arial", 10))
            legend_y += 20
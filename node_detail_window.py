"""
Node Detail Window for displaying detailed information about a single node
"""
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from datetime import datetime


class NodeDetailWindow:
    """Window displaying detailed information for a single Meshtastic node"""
    
    def __init__(self, parent, node_id: str, node_data: dict, 
                 on_logs=None, on_csv=None, on_plot=None):
        """
        Create a node detail window
        
        Args:
            parent: Parent dashboard instance
            node_id: Node ID (with ! prefix)
            node_data: Dictionary containing node information
            on_logs: Callback for logs button
            on_csv: Callback for CSV button
            on_plot: Callback for plot button
        """
        self.parent = parent
        self.node_id = node_id
        self.node_data = node_data
        self.on_logs = on_logs
        self.on_csv = on_csv
        self.on_plot = on_plot
        
        # Debug: Log callback status
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"NodeDetailWindow callbacks: logs={on_logs is not None}, csv={on_csv is not None}, plot={on_plot is not None}")
        
        # Get parent's color scheme BEFORE creating window
        self.colors = parent.colors
        logger.info(f"NodeDetailWindow colors loaded: {len(self.colors)} colors available")
        
        # Create top-level window - use exact same pattern as working Plot dialog
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Node Details: {node_id}")
        self.window.geometry("420x550+50+50")  # 420x550 - width increased to show scrollbar
        self.window.configure(bg=self.colors['bg_main'])
        logger.info(f"NodeDetailWindow window created and configured")
        
        # Make window modal - wrap in try/except for Linux compatibility
        try:
            logger.info(f"NodeDetailWindow attempting transient()...")
            self.window.transient(self.parent)
            logger.info(f"NodeDetailWindow transient() succeeded")
            
            logger.info(f"NodeDetailWindow attempting grab_set()...")
            self.window.grab_set()
            logger.info(f"NodeDetailWindow grab_set() succeeded")
        except Exception as e:
            logger.warning(f"NodeDetailWindow modal setup failed (non-critical): {e}")
            # Continue anyway - window will still work, just not modal
        
        # Create UI
        logger.info(f"NodeDetailWindow creating button bar...")
        self._create_button_bar()  # Buttons at top
        logger.info(f"NodeDetailWindow button bar created")
        
        # Create scrollable canvas for content
        logger.info(f"NodeDetailWindow creating canvas and scrollbar...")
        canvas = tk.Canvas(self.window, bg=self.colors['bg_main'], highlightthickness=0)
        scrollbar = tk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_main'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        logger.info(f"NodeDetailWindow canvas packed")
        
        # Enable mousewheel scrolling for Windows and Linux
        self._bind_mousewheel(canvas)
        
        # Add content to scrollable frame
        logger.info(f"NodeDetailWindow creating content sections...")
        self._create_header()
        logger.info(f"NodeDetailWindow header created")
        self._create_general_info()
        logger.info(f"NodeDetailWindow general info created")
        self._create_environmental_section()
        logger.info(f"NodeDetailWindow environmental section created")
        self._create_device_telemetry()
        logger.info(f"NodeDetailWindow device telemetry created")
        self._create_motion_section()
        logger.info(f"NodeDetailWindow motion section created")
        
        # Force update to ensure widgets are rendered
        logger.info(f"NodeDetailWindow forcing widget update...")
        self.window.update_idletasks()
        logger.info(f"NodeDetailWindow initialization complete")
    
    def _create_button_bar(self):
        """Create button bar at top"""
        button_frame = tk.Frame(self.window, bg=self.colors['bg_frame'], padx=10, pady=10)
        button_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # No font specified - use default tkinter button font like main dashboard
        
        # Use EXACT same pattern as working main dashboard buttons:
        # - command= parameter set directly in Button constructor
        # - Create and pack in one statement
        # - Use actual method references, not conditionals
        
        btn_config = {
            'bg': self.colors['button_bg'],
            'fg': self.colors['button_fg']
        }
        
        # Create buttons with command set directly like working dashboard buttons
        if self.on_logs:
            tk.Button(button_frame, text="Logs", command=self.on_logs, **btn_config).pack(side="left", padx=(0, 5))
        
        if self.on_csv:
            tk.Button(button_frame, text="CSV", command=self.on_csv, **btn_config).pack(side="left", padx=(0, 5))
        
        if self.on_plot:
            tk.Button(button_frame, text="Plot", command=self.on_plot, **btn_config).pack(side="left", padx=(0, 5))
        
        # CLOSE BUTTON  
        tk.Button(button_frame, text="Close", command=self.window.destroy, **btn_config).pack(side="right")
    
    def _create_header(self):
        """Create header with node name and ID"""
        header_frame = tk.Frame(self.scrollable_frame, bg=self.colors['bg_frame'], padx=15, pady=10)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Node name (long name)
        name = self.node_data.get('Node LongName', 'Unknown')
        name_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        name_label = tk.Label(header_frame, text=name,
                             bg=self.colors['bg_frame'],
                             fg=self.colors['fg_normal'],
                             font=name_font)
        name_label.pack(anchor="w")
        
        # Node ID and short name
        short_name = self.node_data.get('Node ShortName', 'N/A')
        id_font = tkfont.Font(family="Consolas", size=11)
        id_label = tk.Label(header_frame, text=f"{self.node_id} ({short_name})",
                           bg=self.colors['bg_frame'],
                           fg=self.colors['fg_secondary'],
                           font=id_font)
        id_label.pack(anchor="w", pady=(3, 0))
    
    def _create_general_info(self):
        """Create general info section"""
        section_frame = tk.Frame(self.scrollable_frame, bg=self.colors['bg_main'], padx=15, pady=6)
        section_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Section title
        title_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title_label = tk.Label(section_frame, text="General Information",
                              bg=self.colors['bg_main'],
                              fg=self.colors['fg_normal'],
                              font=title_font)
        title_label.pack(anchor="w", pady=(0, 4))
        
        content_frame = tk.Frame(section_frame, bg=self.colors['bg_frame'], padx=10, pady=6)
        content_frame.pack(fill="x")
        
        font_label = tkfont.Font(family="Segoe UI", size=11)
        font_value = tkfont.Font(family="Segoe UI", size=11)
        
        # Status - check Last Heard to determine actual status
        last_heard = self.node_data.get('Last Heard', 0)
        import time
        time_since_heard = time.time() - last_heard if last_heard else float('inf')
        stale_threshold = 960  # 16 minutes (accommodates 15-min telemetry intervals)
        
        if time_since_heard < stale_threshold:
            status = "Online"
            status_color = self.colors['fg_good']
        else:
            status = "Offline"
            status_color = self.colors['fg_bad']
        
        self._add_info_row(content_frame, "Status:", status, font_label, font_value, status_color)
        
        # Last heard
        if last_heard:
            heard_dt = datetime.fromtimestamp(last_heard)
            heard_str = heard_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            heard_str = "Never"
        self._add_info_row(content_frame, "Last Heard:", heard_str, font_label, font_value)
        
        # Hardware model
        hw_model = self.node_data.get('Hardware Model', 'Unknown')
        self._add_info_row(content_frame, "Hardware:", hw_model, font_label, font_value)
        
        # Uptime - convert seconds to human readable
        uptime_seconds = self.node_data.get('Uptime')
        if uptime_seconds:
            uptime_str = self._format_uptime(uptime_seconds)
            self._add_info_row(content_frame, "Uptime:", uptime_str, font_label, font_value)
    
    def _create_environmental_section(self):
        """Create environmental telemetry section"""
        # Check if any environmental data exists
        has_env = any([
            self.node_data.get('Temperature') is not None,
            self.node_data.get('Humidity') is not None,
            self.node_data.get('Pressure') is not None
        ])
        
        if not has_env:
            return
        
        section_frame = tk.Frame(self.scrollable_frame, bg=self.colors['bg_main'], padx=15, pady=6)
        section_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Section title
        title_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title_label = tk.Label(section_frame, text="Environmental Telemetry",
                              bg=self.colors['bg_main'],
                              fg=self.colors['fg_normal'],
                              font=title_font)
        title_label.pack(anchor="w", pady=(0, 4))
        
        content_frame = tk.Frame(section_frame, bg=self.colors['bg_frame'], padx=10, pady=6)
        content_frame.pack(fill="x")
        
        font_label = tkfont.Font(family="Segoe UI", size=11)
        font_value = tkfont.Font(family="Segoe UI", size=11)
        
        # Temperature
        temp = self.node_data.get('Temperature')
        if temp is not None:
            temp_text = f"{temp:.1f}°C"
            temp_color = self._get_temp_color(temp)
            self._add_info_row(content_frame, "Temperature:", temp_text, font_label, font_value, temp_color)
        
        # Humidity
        humidity = self.node_data.get('Humidity')
        if humidity is not None:
            humidity_text = f"{humidity:.1f}%"
            humidity_color = self._get_humidity_color(humidity)
            self._add_info_row(content_frame, "Humidity:", humidity_text, font_label, font_value, humidity_color)
        
        # Pressure
        pressure = self.node_data.get('Pressure')
        if pressure is not None:
            pressure_text = f"{pressure:.1f} hPa"
            self._add_info_row(content_frame, "Pressure:", pressure_text, font_label, font_value)
    
    def _create_device_telemetry(self):
        """Create device telemetry section"""
        section_frame = tk.Frame(self.scrollable_frame, bg=self.colors['bg_main'], padx=15, pady=6)
        section_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Section title
        title_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title_label = tk.Label(section_frame, text="Device Telemetry",
                              bg=self.colors['bg_main'],
                              fg=self.colors['fg_normal'],
                              font=title_font)
        title_label.pack(anchor="w", pady=(0, 4))
        
        content_frame = tk.Frame(section_frame, bg=self.colors['bg_frame'], padx=10, pady=6)
        content_frame.pack(fill="x")
        
        font_label = tkfont.Font(family="Segoe UI", size=11)
        font_value = tkfont.Font(family="Segoe UI", size=11)
        
        # === Meshtastic Internal Battery ===
        internal_battery = self.node_data.get('Battery Level')
        internal_voltage = self.node_data.get('Internal Battery Voltage')
        
        if internal_battery is not None or internal_voltage is not None:
            # Section header for internal battery
            internal_header = tk.Label(content_frame, text="Meshtastic Internal Battery:",
                                      bg=self.colors['bg_frame'],
                                      fg=self.colors['fg_secondary'],
                                      font=tkfont.Font(family="Segoe UI", size=10, slant="italic"))
            internal_header.pack(anchor="w", pady=(0, 2))
            
            # Internal battery percentage
            if internal_battery is not None:
                battery_text = f"{internal_battery}%"
                battery_color = self._get_battery_color(internal_battery)
                self._add_info_row(content_frame, "  Charge:", battery_text, font_label, font_value, battery_color)
            
            # Internal battery voltage
            if internal_voltage is not None:
                voltage_text = f"{internal_voltage:.2f}V"
                voltage_color = self.colors['fg_normal']
                self._add_info_row(content_frame, "  Voltage:", voltage_text, font_label, font_value, voltage_color)
        
        # === ICP Main Battery (External via Ch3) ===
        ch3_voltage = self.node_data.get('Ch3 Voltage')
        ch3_current = self.node_data.get('Ch3 Current')
        
        if ch3_voltage is not None or ch3_current is not None:
            # Add spacing
            spacer = tk.Frame(content_frame, bg=self.colors['bg_frame'], height=10)
            spacer.pack(fill="x")
            
            # Section header for external battery
            external_header = tk.Label(content_frame, text="Main System Battery:",
                                      bg=self.colors['bg_frame'],
                                      fg=self.colors['fg_secondary'],
                                      font=tkfont.Font(family="Segoe UI", size=10, slant="italic"))
            external_header.pack(anchor="w", pady=(0, 2))
            
            # Calculate percentage from voltage using parent's data collector
            if ch3_voltage is not None and hasattr(self.parent, 'data_collector') and self.parent.data_collector:
                battery_pct = self.parent.data_collector.voltage_to_percentage(ch3_voltage)
                if battery_pct is not None:
                    pct_text = f"{battery_pct}%"
                    pct_color = self._get_battery_color(battery_pct)
                    self._add_info_row(content_frame, "  Charge:", pct_text, font_label, font_value, pct_color)
            
            # Ch3 voltage (for reference)
            if ch3_voltage is not None:
                ch3_text = f"{ch3_voltage:.2f}V"
                voltage_color = self._get_voltage_color(ch3_voltage)
                self._add_info_row(content_frame, "  Voltage:", ch3_text, font_label, font_value, voltage_color)
            
            # Ch3 current
            if ch3_current is not None:
                current_text = f"{ch3_current:.0f}mA"
                self._add_info_row(content_frame, "  Current:", current_text, font_label, font_value)
        
        # Channel Utilization
        channel_util = self.node_data.get('Channel Utilization')
        if channel_util is not None:
            # Add spacing before other metrics
            if internal_battery or ch3_voltage:
                spacer = tk.Frame(content_frame, bg=self.colors['bg_frame'], height=10)
                spacer.pack(fill="x")
            
            util_text = f"{channel_util:.1f}%"
            self._add_info_row(content_frame, "Ch. Utilization:", util_text, font_label, font_value)
        
        # SNR
        snr = self.node_data.get('SNR')
        if snr is not None:
            snr_text = f"{snr:.1f} dB"
            snr_color = self._get_snr_color(snr)
        else:
            snr_text = "N/A"
            snr_color = self.colors['fg_secondary']
        self._add_info_row(content_frame, "SNR:", snr_text, font_label, font_value, snr_color)
        
        # Old voltage field (for backward compatibility with nodes that don't have internal battery voltage)
        voltage = self.node_data.get('Voltage')
        if voltage is not None and internal_voltage is None:
            voltage_text = f"{voltage:.2f}V"
            voltage_color = self._get_voltage_color(voltage)
            self._add_info_row(content_frame, "Voltage:", voltage_text, font_label, font_value, voltage_color)
    
    def _create_motion_section(self):
        """Create motion detection section"""
        last_motion = self.node_data.get('Last Motion')
        if last_motion is None:
            return
        
        section_frame = tk.Frame(self.scrollable_frame, bg=self.colors['bg_main'], padx=15, pady=6)
        section_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Section title
        title_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        title_label = tk.Label(section_frame, text="Motion Detection",
                              bg=self.colors['bg_main'],
                              fg=self.colors['fg_normal'],
                              font=title_font)
        title_label.pack(anchor="w", pady=(0, 4))
        
        content_frame = tk.Frame(section_frame, bg=self.colors['bg_frame'], padx=10, pady=6)
        content_frame.pack(fill="x")
        
        font_label = tkfont.Font(family="Segoe UI", size=11)
        font_value = tkfont.Font(family="Segoe UI", size=11)
        
        # Last motion time
        motion_dt = datetime.fromtimestamp(last_motion)
        motion_str = motion_dt.strftime('%Y-%m-%d %H:%M:%S')
        self._add_info_row(content_frame, "Last Motion:", motion_str, font_label, font_value)
    
    def _add_info_row(self, parent, label_text, value_text, font_label, font_value, value_color=None):
        """Add an info row with label and value"""
        parent_bg = parent.cget('bg')
        row_frame = tk.Frame(parent, bg=parent_bg)
        row_frame.pack(fill="x", pady=2)
        
        label = tk.Label(row_frame, text=label_text,
                        bg=parent_bg,
                        fg=self.colors['fg_secondary'],
                        font=font_label, width=15, anchor="w")
        label.pack(side="left")
        
        if value_color is None:
            value_color = self.colors['fg_normal']
        
        value = tk.Label(row_frame, text=value_text,
                        bg=parent_bg,
                        fg=value_color,
                        font=font_value, anchor="w")
        value.pack(side="left", padx=(5, 0))
    
    def _get_battery_color(self, battery):
        """Get color for battery level"""
        if battery > 50:
            return self.colors['fg_good']     # Green for >50%
        elif battery >= 25:
            return self.colors['fg_warning']  # Yellow for 25-50%
        else:
            return self.colors['fg_bad']      # Red for 0-25%
    
    def _format_uptime(self, seconds):
        """Convert seconds to human readable uptime string"""
        if not seconds or seconds < 0:
            return "Unknown"
        
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")
        
        return " ".join(parts)
    
    def _get_voltage_color(self, voltage):
        """Get color for voltage level"""
        if voltage >= 4.0:
            return self.colors['fg_good']
        elif voltage >= 3.5:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_bad']
    
    def _get_temp_color(self, temp):
        """Get color for temperature"""
        if temp > 40 or temp < 0:
            return self.colors['fg_bad']
        elif temp > 30:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_good']
    
    def _get_snr_color(self, snr):
        """Get color for SNR - matches dashboard thresholds"""
        if snr > 5:
            return self.colors['fg_good']      # Green - Good signal (above +5dB)
        elif snr >= -10:
            return self.colors['fg_yellow']    # Yellow - OK signal (-10dB to +5dB)
        else:
            return self.colors['fg_bad']       # Red - Bad signal (below -10dB)
    
    def _get_humidity_color(self, humidity):
        """Get color for humidity - matches card view"""
        if humidity < 20 or humidity > 60:
            return self.colors['fg_warning']  # Yellow for dry or humid
        else:
            return self.colors['fg_good']     # Green for normal (20-60%)
    
    def _bind_mousewheel(self, canvas):
        """Bind mousewheel to canvas for scrolling - supports both Windows and Linux"""
        def _on_mousewheel(event):
            # Windows/Mac
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _on_linux_scroll_up(event):
            # Linux scroll up
            canvas.yview_scroll(-1, "units")
        
        def _on_linux_scroll_down(event):
            # Linux scroll down
            canvas.yview_scroll(1, "units")
        
        # Bind for Windows/Mac
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Bind for Linux (Button-4 = scroll up, Button-5 = scroll down)
        canvas.bind_all("<Button-4>", _on_linux_scroll_up)
        canvas.bind_all("<Button-5>", _on_linux_scroll_down)
        
        # Clean up binding when window is closed
        def _on_closing():
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
            self.window.destroy()
        
        self.window.protocol("WM_DELETE_WINDOW", _on_closing)

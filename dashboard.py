"""
Enhanced Dashboard GUI for Meshtastic Monitoring
Features: DDd:HHh:MMm:SSs time format, configurable settings, alert indicators
"""

import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, font as tkfont, ttk
from datetime import datetime, timedelta
import threading
import time
import subprocess
import logging
from typing import Dict, Any, Optional

from config_manager import ConfigManager
from data_collector import DataCollector
from plotter import TelemetryPlotter

logger = logging.getLogger(__name__)

class SettingsDialog:
    """Configuration dialog for dashboard settings"""
    
    def __init__(self, parent, config_manager: ConfigManager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Dashboard Settings")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+{}+{}".format(
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))
        
        self.create_widgets()
        self.load_current_values()
    
    def create_widgets(self):
        """Create dialog widgets"""
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Connection tab
        conn_frame = ttk.Frame(notebook)
        notebook.add(conn_frame, text="Connection")
        self.create_connection_tab(conn_frame)
        
        # Dashboard tab  
        dash_frame = ttk.Frame(notebook)
        notebook.add(dash_frame, text="Dashboard")
        self.create_dashboard_tab(dash_frame)
        
        # Alerts tab
        alert_frame = ttk.Frame(notebook)
        notebook.add(alert_frame, text="Alerts")
        self.create_alerts_tab(alert_frame)
        
        # Email tab
        email_frame = ttk.Frame(notebook)
        notebook.add(email_frame, text="Email")
        self.create_email_tab(email_frame)
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Button(button_frame, text="Test Email", command=self.test_email).pack(side="left", padx=(0, 5))
        tk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right")
        tk.Button(button_frame, text="Apply", command=self.apply).pack(side="right", padx=(0, 5))
        tk.Button(button_frame, text="OK", command=self.ok).pack(side="right", padx=(0, 5))
    
    def create_connection_tab(self, parent):
        """Create connection settings tab"""
        # TCP/IP Settings
        tcp_group = ttk.LabelFrame(parent, text="Meshtastic TCP/IP Interface")
        tcp_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(tcp_group, text="Host/IP Address:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.tcp_host = tk.Entry(tcp_group, width=20)
        self.tcp_host.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(tcp_group, text="Port:").grid(row=0, column=2, sticky="w", padx=(20, 5), pady=5)
        self.tcp_port = tk.Entry(tcp_group, width=8)
        self.tcp_port.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        
        tcp_group.grid_columnconfigure(1, weight=1)
        
        # Connection Settings
        conn_group = ttk.LabelFrame(parent, text="Connection Options")
        conn_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(conn_group, text="Connection Timeout:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.conn_timeout = tk.Entry(conn_group, width=10)
        self.conn_timeout.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        tk.Label(conn_group, text="seconds").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        tk.Label(conn_group, text="Retry Interval:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.retry_interval = tk.Entry(conn_group, width=10)
        self.retry_interval.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        tk.Label(conn_group, text="seconds").grid(row=1, column=2, sticky="w", padx=5, pady=5)
    
    def create_dashboard_tab(self, parent):
        """Create dashboard settings tab"""
        # Refresh Settings
        refresh_group = ttk.LabelFrame(parent, text="Refresh Settings")
        refresh_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(refresh_group, text="Refresh Rate:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.refresh_rate = tk.Entry(refresh_group, width=10)
        self.refresh_rate.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        tk.Label(refresh_group, text="seconds").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        # Display Settings
        display_group = ttk.LabelFrame(parent, text="Display Options")
        display_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(display_group, text="Time Format:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.time_format = ttk.Combobox(display_group, values=["DDd:HHh:MMm:SSs", "Seconds", "Minutes"], width=15)
        self.time_format.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        tk.Label(display_group, text="Stale Row Threshold:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.stale_row_seconds = tk.Entry(display_group, width=10)
        self.stale_row_seconds.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        tk.Label(display_group, text="seconds").grid(row=1, column=2, sticky="w", padx=5, pady=5)
    
    def create_alerts_tab(self, parent):
        """Create alerts settings tab"""
        # Enable/Disable
        tk.Checkbutton(parent, text="Enable Alert System", variable=tk.BooleanVar(), name="alerts_enabled").pack(anchor="w", padx=5, pady=5)
        
        # Alert Rules
        rules_group = ttk.LabelFrame(parent, text="Alert Thresholds")
        rules_group.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Node Offline
        offline_frame = tk.Frame(rules_group)
        offline_frame.pack(fill="x", padx=5, pady=2)
        self.offline_enabled = tk.BooleanVar()
        tk.Checkbutton(offline_frame, text="Node Offline Alert", variable=self.offline_enabled).pack(side="left")
        tk.Label(offline_frame, text="After:").pack(side="left", padx=(20, 5))
        self.offline_threshold = tk.Entry(offline_frame, width=8)
        self.offline_threshold.pack(side="left", padx=5)
        tk.Label(offline_frame, text="minutes").pack(side="left", padx=5)
        
        # Low Voltage
        voltage_frame = tk.Frame(rules_group)
        voltage_frame.pack(fill="x", padx=5, pady=2)
        self.voltage_enabled = tk.BooleanVar()
        tk.Checkbutton(voltage_frame, text="Low Voltage Alert", variable=self.voltage_enabled).pack(side="left")
        tk.Label(voltage_frame, text="Below:").pack(side="left", padx=(20, 5))
        self.voltage_threshold = tk.Entry(voltage_frame, width=8)
        self.voltage_threshold.pack(side="left", padx=5)
        tk.Label(voltage_frame, text="volts").pack(side="left", padx=5)
        
        # High Temperature
        temp_frame = tk.Frame(rules_group)
        temp_frame.pack(fill="x", padx=5, pady=2)
        self.temp_enabled = tk.BooleanVar()
        tk.Checkbutton(temp_frame, text="High Temperature Alert", variable=self.temp_enabled).pack(side="left")
        tk.Label(temp_frame, text="Above:").pack(side="left", padx=(20, 5))
        self.temp_threshold = tk.Entry(temp_frame, width=8)
        self.temp_threshold.pack(side="left", padx=5)
        tk.Label(temp_frame, text="°C").pack(side="left", padx=5)
    
    def create_email_tab(self, parent):
        """Create email settings tab"""
        # Enable Email
        self.email_enabled = tk.BooleanVar()
        tk.Checkbutton(parent, text="Enable Email Alerts", variable=self.email_enabled).pack(anchor="w", padx=5, pady=5)
        
        # SMTP Settings
        smtp_group = ttk.LabelFrame(parent, text="SMTP Configuration")
        smtp_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(smtp_group, text="SMTP Server:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.smtp_server = tk.Entry(smtp_group, width=30)
        self.smtp_server.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        tk.Label(smtp_group, text="Port:").grid(row=0, column=2, sticky="w", padx=(10, 5), pady=2)
        self.smtp_port = tk.Entry(smtp_group, width=8)
        self.smtp_port.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        tk.Label(smtp_group, text="Username:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.smtp_username = tk.Entry(smtp_group, width=30)
        self.smtp_username.grid(row=1, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        
        tk.Label(smtp_group, text="Password:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.smtp_password = tk.Entry(smtp_group, width=30, show="*")
        self.smtp_password.grid(row=2, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        
        tk.Label(smtp_group, text="From Address:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.from_address = tk.Entry(smtp_group, width=30)
        self.from_address.grid(row=3, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        
        tk.Label(smtp_group, text="To Addresses:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.to_addresses = tk.Entry(smtp_group, width=30)
        self.to_addresses.grid(row=4, column=1, columnspan=3, sticky="ew", padx=5, pady=2)
        tk.Label(smtp_group, text="(comma-separated)").grid(row=5, column=1, sticky="w", padx=5, pady=(0, 5))
        
        smtp_group.grid_columnconfigure(1, weight=1)
        
        self.use_tls = tk.BooleanVar(value=True)
        tk.Checkbutton(smtp_group, text="Use TLS encryption", variable=self.use_tls).grid(row=6, column=1, sticky="w", padx=5, pady=5)
    
    def load_current_values(self):
        """Load current configuration values into dialog"""
        # Connection settings
        self.tcp_host.insert(0, self.config_manager.get('meshtastic.interface.host', '192.168.1.91'))
        self.tcp_port.insert(0, str(self.config_manager.get('meshtastic.interface.port', 4403)))
        self.conn_timeout.insert(0, str(self.config_manager.get('meshtastic.connection_timeout', 30)))
        self.retry_interval.insert(0, str(self.config_manager.get('meshtastic.retry_interval', 60)))
        
        # Dashboard settings
        refresh_ms = self.config_manager.get('dashboard.refresh_rate_ms', 5000)
        self.refresh_rate.insert(0, str(refresh_ms // 1000))
        self.time_format.set(self.config_manager.get('dashboard.time_format', 'DDd:HHh:MMm:SSs'))
        self.stale_row_seconds.insert(0, str(self.config_manager.get('dashboard.stale_row_seconds', 300)))
        
        # Alert settings
        self.offline_enabled.set(self.config_manager.get('alerts.rules.node_offline.enabled', True))
        offline_seconds = self.config_manager.get('alerts.rules.node_offline.threshold_seconds', 960)
        self.offline_threshold.insert(0, str(offline_seconds // 60))
        
        self.voltage_enabled.set(self.config_manager.get('alerts.rules.low_voltage.enabled', True))
        self.voltage_threshold.insert(0, str(self.config_manager.get('alerts.rules.low_voltage.threshold_volts', 11.0)))
        
        self.temp_enabled.set(self.config_manager.get('alerts.rules.high_temperature.enabled', True))
        self.temp_threshold.insert(0, str(self.config_manager.get('alerts.rules.high_temperature.threshold_celsius', 35)))
        
        # Email settings
        self.email_enabled.set(self.config_manager.get('alerts.email_enabled', False))
        self.smtp_server.insert(0, self.config_manager.get('alerts.email_config.smtp_server', 'smtp.mail.me.com'))
        self.smtp_port.insert(0, str(self.config_manager.get('alerts.email_config.smtp_port', 587)))
        self.smtp_username.insert(0, self.config_manager.get('alerts.email_config.username', ''))
        self.smtp_password.insert(0, self.config_manager.get('alerts.email_config.password', ''))
        self.from_address.insert(0, self.config_manager.get('alerts.email_config.from_address', ''))
        to_addrs = self.config_manager.get('alerts.email_config.to_addresses', [])
        self.to_addresses.insert(0, ', '.join(to_addrs))
        self.use_tls.set(self.config_manager.get('alerts.email_config.use_tls', True))
    
    def test_email(self):
        """Test email configuration"""
        try:
            # Save current values temporarily
            self.save_values()
            
            # Import and test
            from alert_system import AlertManager
            alert_config = self.config_manager.get_section('alerts')
            alert_manager = AlertManager(alert_config)
            
            if alert_manager.test_email():
                messagebox.showinfo("Email Test", "Test email sent successfully! Check your inbox.")
            else:
                messagebox.showerror("Email Test", "Failed to send test email. Check your configuration and logs.")
                
        except Exception as e:
            messagebox.showerror("Email Test", f"Email test failed: {e}")
    
    def save_values(self):
        """Save dialog values to configuration"""
        try:
            # Connection settings
            self.config_manager.set('meshtastic.interface.host', self.tcp_host.get())
            self.config_manager.set('meshtastic.interface.port', int(self.tcp_port.get()))
            self.config_manager.set('meshtastic.connection_timeout', int(self.conn_timeout.get()))
            self.config_manager.set('meshtastic.retry_interval', int(self.retry_interval.get()))
            
            # Dashboard settings
            refresh_seconds = int(self.refresh_rate.get())
            self.config_manager.set('dashboard.refresh_rate_ms', refresh_seconds * 1000)
            self.config_manager.set('dashboard.time_format', self.time_format.get())
            self.config_manager.set('dashboard.stale_row_seconds', int(self.stale_row_seconds.get()))
            
            # Alert settings
            self.config_manager.set('alerts.rules.node_offline.enabled', self.offline_enabled.get())
            offline_minutes = int(self.offline_threshold.get())
            self.config_manager.set('alerts.rules.node_offline.threshold_seconds', offline_minutes * 60)
            
            self.config_manager.set('alerts.rules.low_voltage.enabled', self.voltage_enabled.get())
            self.config_manager.set('alerts.rules.low_voltage.threshold_volts', float(self.voltage_threshold.get()))
            
            self.config_manager.set('alerts.rules.high_temperature.enabled', self.temp_enabled.get())
            self.config_manager.set('alerts.rules.high_temperature.threshold_celsius', float(self.temp_threshold.get()))
            
            # Email settings
            self.config_manager.set('alerts.email_enabled', self.email_enabled.get())
            self.config_manager.set('alerts.email_config.smtp_server', self.smtp_server.get())
            self.config_manager.set('alerts.email_config.smtp_port', int(self.smtp_port.get()))
            self.config_manager.set('alerts.email_config.username', self.smtp_username.get())
            self.config_manager.set('alerts.email_config.password', self.smtp_password.get())
            self.config_manager.set('alerts.email_config.from_address', self.from_address.get())
            
            to_addrs = [addr.strip() for addr in self.to_addresses.get().split(',') if addr.strip()]
            self.config_manager.set('alerts.email_config.to_addresses', to_addrs)
            self.config_manager.set('alerts.email_config.use_tls', self.use_tls.get())
            
            # Save to file
            self.config_manager.save_config()
            
        except ValueError as e:
            messagebox.showerror("Configuration Error", f"Invalid value: {e}")
            return False
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Failed to save configuration: {e}")
            return False
        
        return True
    
    def ok(self):
        """OK button handler"""
        if self.save_values():
            self.result = True
            self.dialog.destroy()
    
    def apply(self):
        """Apply button handler"""
        self.save_values()
    
    def cancel(self):
        """Cancel button handler"""
        self.result = False
        self.dialog.destroy()

class EnhancedDashboard(tk.Tk):
    """Enhanced dashboard with configurable settings and alert integration"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize configuration
        self.config_manager = ConfigManager()
        self.data_collector = None
        self.plotter = TelemetryPlotter(self, self.config_manager)
        
        # UI State
        self.nodes = {}
        self.row_labels = {}
        self.selected_node_id = None
        self.last_refresh = 0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize GUI
        self.setup_gui()
        self.start_data_collection()
        
        # Schedule first refresh
        self.after(1000, self.refresh)
    
    def setup_gui(self):
        """Setup the GUI"""
        # Window settings
        self.title("Enhanced Meshtastic Monitor")
        geometry = self.config_manager.get('dashboard.window_geometry', '1600x800')
        self.geometry(geometry)
        
        # Dark theme colors
        self.colors = {
            'bg_main': '#1e1e1e',        # Dark background
            'bg_frame': '#2d2d2d',       # Slightly lighter for frames
            'bg_stale': '#3d2d2d',       # Dark red-tinted for stale rows
            'bg_selected': '#1a237e',    # Very dark blue for selected row
            'fg_normal': '#ffffff',       # White text
            'fg_secondary': '#b0b0b0',   # Light gray for secondary text
            'button_bg': '#404040',      # Button background
            'button_fg': '#ffffff',      # Button text
            'fg_good': '#228B22',        # Forest green - for positive status/values
            'fg_bad': '#DC143C'          # Crimson - for negative status/values
        }
        
        # Configure main window
        self.configure(bg=self.colors['bg_main'])
        
        # Fonts
        base_family = "Consolas" if sys.platform.startswith("win") else "Courier New"
        self.font_base = tkfont.Font(family=base_family, size=10)
        self.font_bold = tkfont.Font(family=base_family, size=10, weight="bold")
        self.font_italic = tkfont.Font(family=base_family, size=10, slant="italic")
        self.font_title = tkfont.Font(family=base_family, size=18, weight="bold")
        
        # Title frame
        title_frame = tk.Frame(self, bg=self.colors['bg_main'])
        title_frame.pack(fill="x", padx=8, pady=(8, 0))
        
        title_label = tk.Label(title_frame, 
                              text="CERT ICP Telemetry Dashboard",
                              font=self.font_title,
                              bg=self.colors['bg_main'], 
                              fg=self.colors['fg_normal'],
                              anchor="center")
        title_label.pack(expand=True, pady=(0, 8))
        
        # Header frame
        header_frame = tk.Frame(self, bg=self.colors['bg_main'])
        header_frame.pack(fill="x", padx=8, pady=(8, 4))
        
        self.status_label = tk.Label(header_frame, text="Initializing...", anchor="w", 
                                    bg=self.colors['bg_main'], fg=self.colors['fg_normal'])
        self.status_label.pack(side="left", fill="x", expand=True)
        
        # Control buttons
        controls_frame = tk.Frame(self, bg=self.colors['bg_main'])
        controls_frame.pack(fill="x", padx=8, pady=(0, 6))
        
        tk.Button(controls_frame, text="Settings", command=self.open_settings,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg']).pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Refresh", command=self.force_refresh,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg']).pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Plot", command=self.show_plot,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg']).pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Node Alerts", command=self.open_node_alerts,
                 bg='#ff6b35', fg='white').pack(side="left", padx=(0, 5))
        self.btn_logs = tk.Button(controls_frame, text="Open Logs", command=self.open_logs_folder, state="disabled",
                                 bg=self.colors['button_bg'], fg=self.colors['button_fg'])
        self.btn_logs.pack(side="left", padx=(0, 5))
        self.btn_csv = tk.Button(controls_frame, text="Today's CSV", command=self.open_today_csv, state="disabled",
                                bg=self.colors['button_bg'], fg=self.colors['button_fg'])
        self.btn_csv.pack(side="left")
        
        # Connection status
        conn_frame = tk.Frame(controls_frame, bg=self.colors['bg_main'])
        conn_frame.pack(side="right")
        
        tk.Label(conn_frame, text="Connection:", bg=self.colors['bg_main'], 
                fg=self.colors['fg_secondary']).pack(side="left", padx=(0, 5))
        self.conn_status = tk.Label(conn_frame, text="Disconnected", fg=self.colors['fg_bad'],
                                   bg=self.colors['bg_main'])
        self.conn_status.pack(side="left")
        
        # Table frame
        self.table_frame = tk.Frame(self, bg=self.colors['bg_frame'])
        self.table_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Setup table columns
        self.setup_table()
        
        # Protocol for window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_table(self):
        """Setup the data table"""
        # Column definitions: (title, key, width_chars, anchor, is_numeric)
        self.COLUMNS = [
            ("Node ID", "id", 10, "w", False),
            ("Name", "long", 18, "w", False), 
            ("Short", "short", 8, "center", False),
            ("Status", "status", 12, "center", False),
            ("Last Heard", "last_heard", 18, "center", False),
            ("SNR dB", "SNR", 8, "e", True),
            ("Temp °C", "Temperature", 8, "e", True),
            ("Hum %", "Humidity", 8, "e", True),
            ("Volt V", "Voltage", 8, "e", True),
            ("Curr mA", "Current", 8, "e", True),
            ("Batt %", "Battery Level", 8, "e", True),
            ("Util %", "Channel Utilization", 8, "e", True),
            ("Uptime", "Uptime", 16, "center", False),
        ]
        
        # Calculate column widths
        char_width = self.font_base.measure("0")
        
        # Configure column weights
        for col_idx, (title, key, width_chars, anchor, is_num) in enumerate(self.COLUMNS):
            pixel_width = char_width * width_chars + 10
            self.table_frame.grid_columnconfigure(col_idx, minsize=pixel_width, weight=0)
        
        # Create headers
        self.header_labels = []
        for col_idx, (title, key, width_chars, anchor, is_num) in enumerate(self.COLUMNS):
            header = tk.Label(self.table_frame, text=title, font=self.font_bold,
                            borderwidth=1, relief="groove", anchor=anchor, padx=3, pady=2,
                            bg=self.colors['button_bg'], fg=self.colors['fg_normal'])
            header.grid(row=0, column=col_idx, sticky="nsew", padx=1, pady=1)
            self.header_labels.append(header)
    
    def start_data_collection(self):
        """Start the data collection system"""
        try:
            self.data_collector = DataCollector()
            
            # Start in separate thread to avoid blocking GUI
            threading.Thread(target=self.data_collector.start, daemon=True).start()
            
            logger.info("Data collection started")
        except Exception as e:
            logger.error(f"Failed to start data collection: {e}")
            messagebox.showerror("Startup Error", f"Failed to start data collection: {e}")
    
    def refresh(self):
        """Refresh the dashboard display"""
        try:
            if not self.data_collector:
                self.after(5000, self.refresh)
                return
            
            # Get current data
            nodes_data = self.data_collector.get_nodes_data()
            connection_status = self.data_collector.get_connection_status()
            
            # Update connection status
            if connection_status['connected']:
                interface_info = connection_status.get('interface_info', {})
                conn_type = interface_info.get('type', 'unknown')
                if conn_type == 'tcp':
                    conn_text = f"TCP {interface_info.get('host', '')}:{interface_info.get('port', '')}"
                else:
                    conn_text = f"{conn_type.upper()}"
                self.conn_status.config(text=f"Connected ({conn_text})", fg=self.colors['fg_good'])
            else:
                self.conn_status.config(text="Disconnected", fg=self.colors['fg_bad'])
            
            # Update nodes display
            self.update_nodes_display(nodes_data)
            
            # Update status
            now = datetime.now()
            node_count = len(nodes_data)
            online_count = self.count_online_nodes(nodes_data)
            self.status_label.config(text=f"Updated: {now.strftime('%Y-%m-%d %H:%M:%S')} | Nodes: {node_count} ({online_count} online)")
            
            # Schedule next refresh
            refresh_ms = self.config_manager.get('dashboard.refresh_rate_ms', 5000)
            self.after(refresh_ms, self.refresh)
            
        except Exception as e:
            logger.error(f"Error during refresh: {e}")
            self.after(5000, self.refresh)  # Retry in 5 seconds
    
    def update_nodes_display(self, nodes_data: Dict[str, Any]):
        """Update the nodes table display"""
        try:
            current_time = time.time()
            
            # Sort nodes by status (online first), then by name
            sorted_nodes = sorted(nodes_data.items(), key=lambda x: (
                self.get_node_sort_key(x[1], current_time),
                x[1].get('Node LongName', 'Unknown')
            ))
            
            # Remove rows for nodes that no longer exist
            existing_node_ids = set(nodes_data.keys())
            for node_id in list(self.row_labels.keys()):
                if node_id not in existing_node_ids:
                    for label in self.row_labels[node_id]:
                        label.destroy()
                    del self.row_labels[node_id]
            
            # Update/create rows
            for row_idx, (node_id, node_data) in enumerate(sorted_nodes, start=1):
                if node_id not in self.row_labels:
                    # Create new row
                    row_labels = []
                    for col_idx, (title, key, width_chars, anchor, is_num) in enumerate(self.COLUMNS):
                        label = tk.Label(self.table_frame, text="", font=self.font_base,
                                       borderwidth=1, relief="groove", anchor=anchor, padx=3, pady=1,
                                       bg=self.colors['bg_frame'], fg=self.colors['fg_normal'])
                        label.grid(row=row_idx, column=col_idx, sticky="nsew", padx=1, pady=1)
                        label.bind("<Button-1>", lambda e, nid=node_id: self.select_node(nid))
                        row_labels.append(label)
                    self.row_labels[node_id] = row_labels
                
                # Update row position
                for col_idx, label in enumerate(self.row_labels[node_id]):
                    label.grid_configure(row=row_idx)
                
                # Update row data
                self.update_row_data(node_id, node_data, current_time)
            
            # Auto-select first node if none selected (enables log buttons)
            if nodes_data and not self.selected_node_id:
                first_node_id = next(iter(nodes_data.keys()))
                self.select_node(first_node_id)
            
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def update_row_data(self, node_id: str, node_data: Dict[str, Any], current_time: float):
        """Update data for a single row"""
        try:
            row_labels = self.row_labels[node_id]
            
            # Determine row background color based on selection and age
            if node_id == self.selected_node_id:
                row_bg = self.colors['bg_selected']  # Very dark blue for selected row
            else:
                last_heard = node_data.get('Last Heard', 0)
                age_seconds = current_time - last_heard if last_heard else float('inf')
                stale_threshold = self.config_manager.get('dashboard.stale_row_seconds', 300)
                
                if age_seconds > stale_threshold:
                    row_bg = self.colors['bg_stale']  # Dark red-tinted for stale
                else:
                    row_bg = self.colors['bg_frame']  # Normal dark background
            
            # Update each column
            for col_idx, (title, key, width_chars, anchor, is_num) in enumerate(self.COLUMNS):
                label = row_labels[col_idx]
                text, font, fg = self.get_cell_content(node_id, node_data, key, current_time)
                
                # Truncate text to fit column
                max_chars = width_chars - 1
                if len(text) > max_chars:
                    text = text[:max_chars-1] + "…"
                
                label.config(text=text, font=font, fg=fg, bg=row_bg)
                
        except Exception as e:
            logger.error(f"Error updating row for {node_id}: {e}")
    
    def get_cell_content(self, node_id: str, node_data: Dict[str, Any], key: str, current_time: float):
        """Get content for a table cell"""
        text = "—"
        font = self.font_base
        fg = self.colors['fg_normal']  # Default to white text for dark theme
        
        try:
            if key == "id":
                text = node_id[1:] if node_id.startswith('!') else node_id
            elif key == "long":
                text = node_data.get('Node LongName', 'Unknown')
            elif key == "short":
                text = node_data.get('Node ShortName', 'Unk')
            elif key == "status":
                last_heard = node_data.get('Last Heard', 0)
                if last_heard:
                    age = current_time - last_heard
                    if age < 900:  # 15 minutes
                        text = "Online"
                        fg = self.colors['fg_good']  # Forest green
                    elif age < 3600:  # 1 hour
                        text = "Missed"  
                        fg = "yellow"
                    else:
                        text = "Offline"
                        fg = self.colors['fg_bad']  # Crimson
                else:
                    text = "Unknown"
                    fg = "gray"
            elif key == "last_heard":
                last_heard = node_data.get('Last Heard')
                if last_heard:
                    dt = datetime.fromtimestamp(last_heard)
                    text = dt.strftime('%d %b %H:%M') + "hrs"
                    
                    # Apply stale styling if > 31 minutes old
                    age_seconds = current_time - last_heard
                    stale_threshold = 31 * 60  # 31 minutes in seconds
                    if age_seconds > stale_threshold:
                        fg = "gray"
                        font = self.font_italic
                else:
                    text = "Never"
            elif key == "Uptime":
                uptime = node_data.get('Uptime')
                if uptime is not None:
                    text = self.format_duration(int(uptime))
            else:
                # Regular data field
                value = node_data.get(key)
                if value is not None:
                    if isinstance(value, (int, float)):
                        if key == 'SNR':
                            # SNR color coding based on signal quality
                            text = f"{value:.1f}"
                            if value > 5:
                                fg = self.colors['fg_good']  # Forest green - Good signal (above +5dB)
                            elif value >= -10:
                                fg = "yellow"   # Yellow - OK signal (-10dB to +5dB) 
                            else:
                                fg = self.colors['fg_bad']  # Crimson - Bad signal (below -10dB)
                        elif key == 'Temperature':
                            # Temperature color coding based on value ranges
                            text = f"{value:.1f}"
                            if value > 40 or value < 0:
                                fg = self.colors['fg_bad']  # Red for extreme temps (>40°C or <0°C)
                            elif value >= 30:
                                fg = "yellow"   # Yellow for warm temps (30-40°C)
                            else:
                                fg = self.colors['fg_good']  # Green for normal temps (0-30°C)
                        elif key == 'Voltage':
                            # Voltage fallback: use Ch3 Voltage if main Voltage is null/0
                            display_voltage = value
                            if value is None or value == 0.0:
                                ch3_voltage = node_data.get('Ch3 Voltage')
                                if ch3_voltage is not None and ch3_voltage != 0.0:
                                    display_voltage = ch3_voltage
                            
                            if display_voltage is not None and display_voltage != 0.0:
                                # Voltage color coding based on battery health ranges
                                text = f"{display_voltage:.2f}"
                                if display_voltage < 11.0 or display_voltage > 14.5:
                                    fg = self.colors['fg_bad']  # Red for dangerous voltages
                                elif display_voltage < 12.0:
                                    fg = "yellow"   # Yellow for low battery (11-12V)
                                elif display_voltage <= 14.0:
                                    fg = self.colors['fg_good']  # Green for good battery (12-14V)
                                else:
                                    fg = "yellow"   # Yellow for slightly high (14-14.5V)
                            else:
                                text = "—"  # No voltage data available
                        elif key == 'Channel Utilization':
                            text = f"{value:.1f}"  # Display as percentage to nearest tenth
                        elif key in ['Humidity', 'Battery Level']:
                            text = f"{value:.0f}"
                        elif key == 'Current':
                            text = f"{value:.0f}"
                        else:
                            text = str(value)
                    else:
                        text = str(value)
                
                # Apply styling based on telemetry data age
                field_times = node_data.get('Field Times', {})
                field_time = field_times.get(key, 0)
                if field_time and key in ['SNR', 'Temperature', 'Voltage', 'Humidity', 'Channel Utilization', 'Current']:
                    field_age = current_time - field_time
                    stale_threshold = 31 * 60  # 31 minutes in seconds
                    
                    if field_age > stale_threshold:
                        # Stale data: gray + italic
                        fg = "gray"
                        font = self.font_italic
                    else:
                        # Fresh telemetry data: bold font
                        font = self.font_bold
                
        except Exception as e:
            logger.error(f"Error getting cell content for {key}: {e}")
            text = "Error"
            fg = self.colors['fg_bad']  # Crimson - consistent with other error colors
        
        return text, font, fg
    
    def format_duration(self, seconds: int) -> str:
        """Format duration according to configured format"""
        time_format = self.config_manager.get('dashboard.time_format', 'DDd:HHh:MMm:SSs')
        
        if time_format in ['DD:HH:MM:SS', 'DDd:HHh:MMm:SSs']:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{days:02d}d:{hours:02d}h:{minutes:02d}m:{secs:02d}s"
        elif time_format == 'Minutes':
            return f"{seconds // 60}m"
        else:  # Seconds
            return f"{seconds}s"
    
    def get_node_sort_key(self, node_data: Dict[str, Any], current_time: float):
        """Get sort key for node (online nodes first)"""
        last_heard = node_data.get('Last Heard', 0)
        if last_heard:
            age = current_time - last_heard
            if age < 300:  # Online (last 5 minutes)
                return 0
            elif age < 3600:  # Recent (last hour)
                return 1
            else:  # Offline
                return 2
        else:
            return 3  # Never heard
    
    def count_online_nodes(self, nodes_data: Dict[str, Any]) -> int:
        """Count nodes that are currently online"""
        current_time = time.time()
        online_count = 0
        
        for node_data in nodes_data.values():
            last_heard = node_data.get('Last Heard', 0)
            if last_heard and (current_time - last_heard) < 300:  # 5 minutes
                online_count += 1
        
        return online_count
    
    def select_node(self, node_id: str):
        """Select a node row"""
        self.selected_node_id = node_id
        
        # Update button states
        if node_id:
            self.btn_logs.config(state="normal")
            self.btn_csv.config(state="normal")
        else:
            self.btn_logs.config(state="disabled")
            self.btn_csv.config(state="disabled")
        
        # Force display refresh to update row highlighting
        self.force_refresh()
    
    def force_refresh(self):
        """Force an immediate refresh"""
        self.refresh()
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.config_manager)
        self.wait_window(dialog.dialog)
        
        if dialog.result:
            # Configuration changed, restart data collector if needed
            messagebox.showinfo("Settings", "Settings saved. Restart the application for all changes to take effect.")
    
    def open_logs_folder(self):
        """Open logs folder for selected node"""
        if not self.selected_node_id:
            return
        
        log_dir = self.config_manager.get('data.log_directory', 'logs')
        clean_id = self.selected_node_id[1:] if self.selected_node_id.startswith('!') else self.selected_node_id
        node_log_path = os.path.join(log_dir, clean_id)
        
        if os.path.exists(node_log_path):
            self.open_path(node_log_path)
        else:
            messagebox.showinfo("No Logs", f"No log directory found for {self.selected_node_id}")
    
    def open_today_csv(self):
        """Open today's CSV file for selected node"""
        if not self.selected_node_id:
            return
        
        log_dir = self.config_manager.get('data.log_directory', 'logs')
        clean_id = self.selected_node_id[1:] if self.selected_node_id.startswith('!') else self.selected_node_id
        today = datetime.now()
        csv_path = os.path.join(log_dir, clean_id, today.strftime('%Y'), today.strftime('%Y%m%d') + '.csv')
        
        if os.path.exists(csv_path):
            self.open_path(csv_path)
        else:
            messagebox.showinfo("No CSV", f"No CSV file found for today for {self.selected_node_id}")
    
    def open_path(self, path: str):
        """Open file or folder in system default application"""
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Open Error", f"Could not open {path}: {e}")
    
    def show_plot(self):
        """Show temperature plot for last week"""
        try:
            self.plotter.show_plot_dialog()
        except Exception as e:
            logger.error(f"Error showing plot: {e}")
            messagebox.showerror("Plot Error", f"Failed to show plot: {e}")
    
    def open_node_alerts(self):
        """Open node-specific alert configuration dialog"""
        try:
            from node_alert_config import NodeAlertConfigDialog
            
            # Get current nodes data
            if self.data_collector:
                nodes_data = self.data_collector.get_nodes_data()
            else:
                # Fallback to loading from JSON file
                try:
                    with open('latest_data.json', 'r') as f:
                        nodes_data = json.load(f)
                except FileNotFoundError:
                    messagebox.showerror("Error", "No node data available. Please wait for data collection to start.")
                    return
            
            # Create and show dialog
            dialog = NodeAlertConfigDialog(self, nodes_data)
            self.wait_window(dialog.dialog)
            
            # If settings were saved, update alert system
            if dialog.result:
                # Save settings to config file
                os.makedirs('config', exist_ok=True)
                with open('config/node_alert_settings.json', 'w') as f:
                    json.dump(dialog.result, f, indent=2)
                
                # Note: Alert system will automatically reload settings on next check
                
                messagebox.showinfo("Settings Saved", 
                                  "Node alert settings have been updated!")
                
        except ImportError:
            messagebox.showerror("Error", "Node alert configuration module not found")
        except Exception as e:
            logger.error(f"Error opening node alerts: {e}")
            messagebox.showerror("Error", f"Failed to open node alerts: {e}")
    
    def on_closing(self):
        """Handle application closing"""
        try:
            # Save window geometry
            self.config_manager.set('dashboard.window_geometry', self.geometry())
            self.config_manager.save_config()
            
            # Stop data collection
            if self.data_collector:
                self.data_collector.stop()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        self.destroy()

def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        app = EnhancedDashboard()
        app.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Application Error", f"Fatal error: {e}")

if __name__ == "__main__":
    main()
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
from node_detail_window import NodeDetailWindow

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
        
        # Telemetry tab
        telemetry_frame = ttk.Frame(notebook)
        notebook.add(telemetry_frame, text="Telemetry")
        self.create_telemetry_tab(telemetry_frame)
        
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
        
        tk.Label(display_group, text="Motion Display Duration:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.motion_display_seconds = tk.Entry(display_group, width=10)
        self.motion_display_seconds.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        tk.Label(display_group, text="seconds (show motion indicator)").grid(row=2, column=2, sticky="w", padx=5, pady=5)
    
    def create_telemetry_tab(self, parent):
        """Create telemetry field settings tab"""
        info_label = tk.Label(parent, text="Select which telemetry fields to display in card view:", 
                             font=('Arial', 10, 'bold'))
        info_label.pack(anchor="w", padx=5, pady=(5, 15))
        
        # Telemetry field checkboxes
        self.telemetry_vars = {}
        fields_frame = tk.Frame(parent)
        fields_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        telemetry_fields = [
            ("voltage", "⚡ Voltage", "Show battery/power voltage readings"),
            ("temperature", "🌡 Temperature", "Show temperature sensor readings"),
            ("humidity", "💧 Humidity", "Show humidity sensor readings"),
            ("pressure", "🌪 Pressure", "Show atmospheric pressure readings"),
            ("battery", "🔋 Battery", "Show battery percentage levels"),
            ("snr", "📶 SNR", "Show signal-to-noise ratio"),
            ("channel_utilization", "📻 Channel Usage", "Show mesh channel utilization"),
            ("current", "⚡ Current", "Show current consumption readings"),
            ("uptime", "⏰ Uptime", "Show device uptime information")
        ]
        
        for i, (field_key, display_name, description) in enumerate(telemetry_fields):
            # Create frame for each field
            field_frame = tk.Frame(fields_frame)
            field_frame.pack(fill="x", pady=3)
            
            # Checkbox variable
            var = tk.BooleanVar()
            self.telemetry_vars[field_key] = var
            
            # Checkbox
            cb = tk.Checkbutton(field_frame, text=display_name, variable=var, 
                               font=('Arial', 10, 'bold'), width=20, anchor='w')
            cb.pack(side="left")
            
            # Description
            desc_label = tk.Label(field_frame, text=description, 
                                 font=('Arial', 9), fg='gray')
            desc_label.pack(side="left", padx=(10, 0))
    
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
        self.motion_display_seconds.insert(0, str(self.config_manager.get('dashboard.motion_display_seconds', 900)))
        
        # Telemetry field settings
        telemetry_config = self.config_manager.get('dashboard.telemetry_fields', {})
        for field_key, var in self.telemetry_vars.items():
            var.set(telemetry_config.get(field_key, True))
        
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
            self.config_manager.set('dashboard.motion_display_seconds', int(self.motion_display_seconds.get()))
            
            # Telemetry field settings
            telemetry_fields = {}
            for field_key, var in self.telemetry_vars.items():
                telemetry_fields[field_key] = var.get()
            self.config_manager.set('dashboard.telemetry_fields', telemetry_fields)
            
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
        self.card_widgets = {}  # Cache for card widgets to prevent flickering
        self.last_node_data = {}  # Track last data for each node to detect changes
        self.flash_timers = {}  # Track active flash timers
        self.selected_node_id = None
        self.last_refresh = 0
        self.view_mode = "table"  # "table" or "cards"
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Initialize GUI
        self.setup_gui()
        self.start_data_collection()
        
        # Initial display update
        self.after(1000, self.refresh_display)
    
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
            'fg_warning': '#FFA500',     # Orange - for warning status/values
            'fg_yellow': '#FFFF00',      # Yellow - for caution status/values
            'fg_bad': '#DC143C'          # Crimson - for negative status/values
        }
        
        # Configure main window
        self.configure(bg=self.colors['bg_main'])
        
        # Fonts - larger for better readability on small screens
        base_family = "Consolas" if sys.platform.startswith("win") else "Courier New"
        self.font_base = tkfont.Font(family=base_family, size=11)
        self.font_bold = tkfont.Font(family=base_family, size=11, weight="bold")
        self.font_data = tkfont.Font(family=base_family, size=11)  # Consistent data font - changed from 12 to 11
        self.font_data_bold = tkfont.Font(family=base_family, size=11, weight="bold")  # Bold data - changed from 12 to 11
        self.font_italic = tkfont.Font(family=base_family, size=11, slant="italic")
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
        
        # Connection status - moved to header frame for small displays
        conn_frame = tk.Frame(header_frame, bg=self.colors['bg_main'])
        conn_frame.pack(side="right")
        
        tk.Label(conn_frame, text="Connection:", bg=self.colors['bg_main'], 
                fg=self.colors['fg_secondary']).pack(side="left", padx=(0, 5))
        self.conn_status = tk.Label(conn_frame, text="Disconnected", fg=self.colors['fg_bad'],
                                   bg=self.colors['bg_main'])
        self.conn_status.pack(side="left")
        
        # Control buttons
        controls_frame = tk.Frame(self, bg=self.colors['bg_main'])
        controls_frame.pack(fill="x", padx=8, pady=(0, 6))
        
        tk.Button(controls_frame, text="Settings", command=self.open_settings,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg']).pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Refresh", command=self.force_refresh,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg']).pack(side="left", padx=(0, 5))
        self.view_btn = tk.Button(controls_frame, text="Cards", command=self.toggle_view,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg'])
        self.view_btn.pack(side="left", padx=(0, 5))
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
        
        # Table frame
        self.table_frame = tk.Frame(self, bg=self.colors['bg_frame'])
        self.table_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Card container frame (initially hidden)
        self.setup_card_container()
        
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
    
    def setup_card_container(self):
        """Setup the scrollable card container"""
        # Main card container (not packed initially)
        self.card_container = tk.Frame(self, bg=self.colors['bg_main'])
        
        # Create scrollable canvas for cards
        self.card_canvas = tk.Canvas(self.card_container, bg=self.colors['bg_main'], highlightthickness=0)
        self.card_scrollbar = tk.Scrollbar(self.card_container, orient="vertical", command=self.card_canvas.yview)
        self.card_scrollable_frame = tk.Frame(self.card_canvas, bg=self.colors['bg_main'])
        
        self.card_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all"))
        )
        
        self.card_canvas.create_window((0, 0), window=self.card_scrollable_frame, anchor="nw")
        self.card_canvas.configure(yscrollcommand=self.card_scrollbar.set)
        
        # Pack canvas and scrollbar
        self.card_canvas.pack(side="left", fill="both", expand=True)
        self.card_scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def on_mousewheel(event):
            self.card_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.card_canvas.bind("<MouseWheel>", on_mousewheel)
    
    def start_data_collection(self):
        """Start the data collection system"""
        try:
            self.data_collector = DataCollector()
            
            # Register callback for data changes (event-driven updates)
            self.data_collector.set_data_change_callback(self.on_data_changed)
            
            # Start in separate thread to avoid blocking GUI
            threading.Thread(target=self.data_collector.start, daemon=True).start()
            
            logger.info("Data collection started")
        except Exception as e:
            logger.error(f"Failed to start data collection: {e}")
            messagebox.showerror("Startup Error", f"Failed to start data collection: {e}")
    
    def on_data_changed(self):
        """Callback when data changes - schedule GUI update"""
        # Schedule update on GUI thread (thread-safe)
        self.after(0, self.refresh_display)
    
    def refresh_display(self):
        """Refresh the dashboard display (event-driven, called when data changes)"""
        try:
            if not self.data_collector:
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
            
        except Exception as e:
            logger.error(f"Error during refresh: {e}")
    
    def update_nodes_display(self, nodes_data: Dict[str, Any]):
        """Update the nodes display (table or cards based on view mode)"""
        try:
            if self.view_mode == "cards":
                # Display cards view
                self.display_card_view(nodes_data)
            else:
                # Display table view
                self.update_table_display(nodes_data)
            
            # Auto-select first node if none selected (enables log buttons)
            if nodes_data and not self.selected_node_id:
                first_node_id = next(iter(nodes_data.keys()))
                self.select_node(first_node_id)
                
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def update_table_display(self, nodes_data: Dict[str, Any]):
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
                
        except Exception as e:
            logger.error(f"Error updating table display: {e}")
    
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
                        fg = self.colors['fg_yellow']  # Yellow
                    else:
                        text = "Offline"
                        fg = self.colors['fg_bad']  # Crimson
                else:
                    text = "Unknown"
                    fg = self.colors['fg_secondary']  # Gray
            elif key == "last_heard":
                last_heard = node_data.get('Last Heard')
                if last_heard:
                    dt = datetime.fromtimestamp(last_heard)
                    text = dt.strftime('%d %b %H:%M') + "hrs"
                    
                    # Apply stale styling if > 31 minutes old
                    age_seconds = current_time - last_heard
                    stale_threshold = 31 * 60  # 31 minutes in seconds
                    if age_seconds > stale_threshold:
                        fg = self.colors['fg_secondary']  # Gray
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
                                fg = self.colors['fg_yellow']  # Yellow - OK signal (-10dB to +5dB) 
                            else:
                                fg = self.colors['fg_bad']  # Crimson - Bad signal (below -10dB)
                        elif key == 'Temperature':
                            # Temperature color coding based on value ranges
                            text = f"{value:.1f}"
                            if value > 40 or value < 0:
                                fg = self.colors['fg_bad']  # Red for extreme temps (>40°C or <0°C)
                            elif value >= 30:
                                fg = self.colors['fg_warning']  # Orange for warm temps (30-40°C)
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
                                    fg = self.colors['fg_warning']  # Orange for low battery (11-12V)
                                elif display_voltage <= 14.0:
                                    fg = self.colors['fg_good']  # Green for good battery (12-14V)
                                else:
                                    fg = self.colors['fg_warning']  # Orange for slightly high (14-14.5V)
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
                        fg = self.colors['fg_secondary']  # Gray
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
        self.refresh_display()
    
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
    
    def display_card_view(self, nodes_data: Dict[str, Any]):
        """Display nodes as cards in a grid layout - only update changed cards"""
        # Filter out nodes with no last heard history (but allow recent ones even if timestamp is 0)
        # If a node has ANY data fields, show it
        filtered_nodes = {}
        for node_id, node_data in nodes_data.items():
            last_heard = node_data.get('Last Heard')
            # Show node if: it has a last heard time > 0, OR it has any telemetry data
            has_data = any(node_data.get(field) is not None 
                          for field in ['Voltage', 'Temperature', 'SNR', 'Battery Level'])
            if (last_heard is not None and last_heard > 0) or has_data:
                filtered_nodes[node_id] = node_data
        
        # Sort nodes like in table view
        current_time = time.time()
        sorted_nodes = sorted(filtered_nodes.items(), key=lambda x: (
            self.get_node_sort_key(x[1], current_time),
            x[1].get('Node LongName', 'Unknown')
        ))
        
        # Check which nodes have changed data
        changed_nodes = set()
        for node_id, node_data in sorted_nodes:
            if node_id not in self.last_node_data or self.last_node_data[node_id] != node_data:
                changed_nodes.add(node_id)
                self.last_node_data[node_id] = node_data.copy()
        
        # If layout needs rebuild (new/removed nodes or first time)
        existing_nodes = set(self.card_widgets.keys())
        current_nodes = set(dict(sorted_nodes).keys())
        
        if existing_nodes != current_nodes or not self.card_widgets:
            # Full rebuild needed
            for widget in self.card_scrollable_frame.winfo_children():
                widget.destroy()
            self.card_widgets.clear()
            
            # Calculate grid layout - 3 cards across for wide screens, adjust for 80% width
            window_width = self.winfo_width()
            # Use 3 columns if width > 900, 2 if width > 600, else 1
            # Default 1600x800 window should easily support 3 columns
            if window_width > 900:
                cards_per_row = 3
                card_width = 280  # Fits 3 across with padding
            elif window_width > 600:
                cards_per_row = 2
                card_width = 320
            else:
                cards_per_row = 1
                card_width = 380
            
            # Create cards in grid layout
            current_row_frame = None
            current_col = 0
            
            for node_id, node_data in sorted_nodes:
                # Create new row frame if needed
                if current_col == 0:
                    current_row_frame = tk.Frame(self.card_scrollable_frame, bg=self.colors['bg_main'])
                    current_row_frame.pack(fill="x", padx=5, pady=2)
                
                # Create card - mark as changed if it's new
                is_changed = node_id in changed_nodes
                self.create_node_card(current_row_frame, node_id, node_data, current_col, card_width, is_changed)
                
                current_col += 1
                if current_col >= cards_per_row:
                    current_col = 0
        else:
            # Update only changed cards
            for node_id in changed_nodes:
                if node_id in self.card_widgets and node_id in filtered_nodes:
                    self.update_node_card(node_id, filtered_nodes[node_id], current_time, is_changed=True)
    
    def create_node_card(self, parent, node_id: str, node_data: Dict[str, Any], col: int, card_width: int, is_changed: bool = False):
        """Create a compact card for a single node"""
        # Status colors
        status_colors = {
            'Online': self.colors['fg_good'],
            'Offline': self.colors['fg_bad']
        }
        
        # Determine node status
        current_time = time.time()
        last_heard = node_data.get('Last Heard', 0)
        time_diff = current_time - last_heard if last_heard else float('inf')
        status = "Online" if time_diff <= 300 else "Offline"  # 5 minutes threshold
        
        # Main card frame - start with flash color if changed
        bg_color = '#1a4d7a' if is_changed else self.colors['bg_frame']  # Dark blue flash
        card_frame = tk.Frame(parent, bg=bg_color, relief='raised', bd=2, width=card_width)
        card_frame.pack(side="left", padx=4, pady=3)
        card_frame.pack_propagate(True)
        
        # Header row - Name, NodeID, Status
        header_frame = tk.Frame(card_frame, bg=bg_color)
        header_frame.pack(fill="x", padx=6, pady=(3, 1))
        
        # Left side - Node name and ID
        left_header = tk.Frame(header_frame, bg=bg_color)
        left_header.pack(side="left")
        
        # Node name (bold, larger)
        long_name = node_data.get('Node LongName', 'Unknown')
        display_name = long_name.replace("AG6WR-", "") if long_name.startswith("AG6WR-") else long_name
        name_label = tk.Label(left_header, text=display_name, 
                             bg=bg_color, fg=self.colors['fg_normal'], 
                             font=self.font_bold)
        name_label.pack(side="left")
        
        # NodeID (smaller, gray)
        short_name = node_data.get('Node ShortName', node_id[-4:])
        nodeid_label = tk.Label(left_header, text=f"({short_name})",
                               bg=bg_color, fg=self.colors['fg_secondary'],
                               font=self.font_base)
        nodeid_label.pack(side="left", padx=(4, 0))
        
        # Right side - Status only (no dynamic timer)
        right_header = tk.Frame(header_frame, bg=bg_color)
        right_header.pack(side="right")
        
        # Status (colored, bold)
        status_label = tk.Label(right_header, text=status,
                               bg=bg_color, fg=status_colors.get(status, self.colors['fg_normal']),
                               font=self.font_data_bold)
        status_label.pack(anchor="e")
        
        # Last Heard row - fixed height area for all cards (uniform height)
        # Always 16px high to maintain uniform card heights, but only show content for offline nodes
        lastheard_frame = tk.Frame(card_frame, bg=bg_color, height=16)
        lastheard_frame.pack(fill="x", padx=6)
        lastheard_frame.pack_propagate(False)
        
        # For offline nodes, show static last heard timestamp
        heard_label = None
        if status == "Offline" and last_heard:
            from datetime import datetime
            heard_dt = datetime.fromtimestamp(last_heard)
            heard_text = f"Last heard: {heard_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            # Small font for compact display
            small_font = tkfont.Font(family="Consolas" if sys.platform.startswith("win") else "Courier New", size=9)
            heard_label = tk.Label(lastheard_frame, text=heard_text,
                                  bg=bg_color, fg=self.colors['fg_bad'],
                                  font=small_font)
            heard_label.pack(anchor="w", side="left")
        
        # Determine if data is stale (use grey color for stale data)
        is_stale = status == "Offline"
        stale_color = self.colors['fg_secondary']  # Grey for stale data
        
        # Metrics row 1 - Primary metrics (tighter spacing)
        metrics1_frame = tk.Frame(card_frame, bg=bg_color)
        metrics1_frame.pack(fill="x", padx=6, pady=1)
        
        # Adjust column widths for 80% card width (110 -> 88)
        col1_frame = tk.Frame(metrics1_frame, bg=bg_color, width=88, height=25)
        col1_frame.pack(side="left")
        col1_frame.pack_propagate(False)
        
        col2_frame = tk.Frame(metrics1_frame, bg=bg_color, width=88, height=25)
        col2_frame.pack(side="left", padx=(6, 0))
        col2_frame.pack_propagate(False)
        
        col3_frame = tk.Frame(metrics1_frame, bg=bg_color, width=88, height=25)
        col3_frame.pack(side="left", padx=(6, 0))
        col3_frame.pack_propagate(False)
        
        # Voltage in column 1
        voltage = node_data.get('Voltage')
        voltage_label = None
        if voltage is not None:
            voltage_text, voltage_color = self.get_voltage_display(voltage)
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else voltage_color
            voltage_label = tk.Label(col1_frame, text=voltage_text,
                                    bg=bg_color, fg=display_color,
                                    font=self.font_data_bold, anchor='w')
            voltage_label.pack(fill="both", expand=True)
        
        # Temperature in column 2
        temp = node_data.get('Temperature')
        temp_label = None
        if temp is not None:
            # Match table view: Red if >40°C or <0°C, Yellow if 30-40°C, Green if 0-30°C
            if temp > 40 or temp < 0:
                temp_color = self.colors['fg_bad']  # Red for extreme temps
            elif temp >= 30:
                temp_color = self.colors['fg_warning']  # Orange for warm temps (30-40°C)
            else:
                temp_color = self.colors['fg_good']  # Green for normal temps (0-30°C)
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else temp_color
            temp_text = f"T: {temp:.1f}°C"
            temp_label = tk.Label(col2_frame, text=temp_text,
                                 bg=bg_color, fg=display_color,
                                 font=self.font_data_bold, anchor='w')
            temp_label.pack(fill="both", expand=True)
        
        # Channel Utilization in column 3
        channel_util = node_data.get('Channel Utilization')
        util_label = None
        if channel_util is not None:
            util_color = self.colors['fg_bad'] if channel_util > 80 else self.colors['fg_warning'] if channel_util > 50 else self.colors['fg_good']
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else util_color
            util_text = f"Ch: {channel_util:.1f}%"
            util_label = tk.Label(col3_frame, text=util_text,
                                 bg=bg_color, fg=display_color,
                                 font=self.font_data, anchor='w')
            util_label.pack(fill="both", expand=True)
        
        # Metrics row 2 - Secondary metrics (tighter spacing)
        metrics2_frame = tk.Frame(card_frame, bg=bg_color)
        metrics2_frame.pack(fill="x", padx=6, pady=(1, 3))
        
        # Create aligned columns for row 2
        row2_col1_frame = tk.Frame(metrics2_frame, bg=bg_color, width=100, height=25)  # Increased from 88 to 100
        row2_col1_frame.pack(side="left")
        row2_col1_frame.pack_propagate(False)
        
        row2_col2_frame = tk.Frame(metrics2_frame, bg=bg_color, width=88, height=25)
        row2_col2_frame.pack(side="left", padx=(6, 0))
        row2_col2_frame.pack_propagate(False)
        
        # SNR in first column - Bars only, no dB value
        # Create multi-colored bars using multiple labels
        snr = node_data.get('SNR')
        snr_label = None
        if snr is not None:
            # Create container for SNR display with multiple colored elements
            snr_container = tk.Frame(row2_col1_frame, bg=bg_color)
            snr_container.pack(fill="both", expand=True, anchor='w')
            
            # Icon - using text instead of emoji for Linux compatibility
            icon_label = tk.Label(snr_container, text="SNR:", bg=bg_color, 
                                 fg=self.colors['fg_secondary'], font=self.font_data)
            icon_label.pack(side="left", padx=0)  # No padding
            
            # Get bar colors based on SNR level
            # Use pipe characters with different colors - all same width and baseline
            bar_chars = "||||"  # Four identical pipes/bars
            bar_colors = self.get_signal_bar_colors(snr)
            
            # Debug: print what we're doing
            logger.debug(f"SNR {snr}: bar_colors = {bar_colors}")
            
            # Create smaller font for narrower bars
            bar_font = tkfont.Font(family="Consolas" if sys.platform.startswith("win") else "Courier New", 
                                  size=9)  # Smaller than data font
            
            # Create each bar with its own color - NO spacing between bars
            # No anchor specified - use default center alignment to match text baseline
            for i, (char, color) in enumerate(zip(bar_chars, bar_colors)):
                bar_label = tk.Label(snr_container, text=char, bg=bg_color,
                                   fg=color, font=bar_font, padx=0, pady=0)
                bar_label.pack(side="left", padx=0, pady=0)
            
            snr_label = snr_container  # Store container reference
        
        # Battery in second column
        battery = node_data.get('Battery Level')
        battery_label = None
        if battery is not None:
            # Red <10%, Orange 10-20%, Yellow 20-40%, Green 40-100%
            if battery < 10:
                battery_color = self.colors['fg_bad']  # Red for critical
            elif battery < 20:
                battery_color = self.colors['fg_warning']  # Orange for low
            elif battery < 40:
                battery_color = self.colors['fg_yellow']  # Yellow for caution
            else:
                battery_color = self.colors['fg_good']  # Green for good
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else battery_color
            battery_text = f"Bat: {battery:.0f}%"
            battery_label = tk.Label(row2_col2_frame, text=battery_text,
                                   bg=bg_color, fg=display_color,
                                   font=self.font_data, anchor='w')
            battery_label.pack(fill="both", expand=True)
        
        # Metrics row 3 - Motion detection (fixed height for uniform cards)
        # Always create frame with fixed height, but only show content for online nodes with recent motion
        metrics3_frame = tk.Frame(card_frame, bg=bg_color, height=20)
        metrics3_frame.pack(fill="x", padx=6, pady=(1, 3))
        metrics3_frame.pack_propagate(False)
        
        motion_label = None
        last_motion = node_data.get('Last Motion')
        # Only show motion for online nodes
        if status == "Online" and last_motion:
            motion_display_duration = self.config_manager.get('dashboard.motion_display_seconds', 900)  # Default 15 minutes
            time_since_motion = current_time - last_motion
            
            if time_since_motion <= motion_display_duration:
                # Motion indicator - using text instead of emoji for Linux compatibility
                motion_text = "Motion detected"
                motion_label = tk.Label(metrics3_frame, text=motion_text,
                                       bg=bg_color, fg=self.colors['fg_good'],
                                       font=self.font_data, anchor='w')
                motion_label.pack(fill="both", expand=True)
        
        # Click handler for showing node detail window
        def on_card_click(event):
            self.show_node_detail(node_id)
        
        # Bind click to card frame and all children recursively
        def bind_click_recursive(widget):
            widget.bind("<Button-1>", on_card_click)
            for child in widget.winfo_children():
                bind_click_recursive(child)
        
        bind_click_recursive(card_frame)
        
        # Store widget references for updates
        self.card_widgets[node_id] = {
            'frame': card_frame,
            'header_frame': header_frame,
            'left_header': left_header,
            'right_header': right_header,
            'lastheard_frame': lastheard_frame,
            'metrics1_frame': metrics1_frame,
            'metrics2_frame': metrics2_frame,
            'metrics3_frame': metrics3_frame,
            'col1_frame': col1_frame,
            'col2_frame': col2_frame,
            'col3_frame': col3_frame,
            'row2_col1_frame': row2_col1_frame,
            'row2_col2_frame': row2_col2_frame,
            'name_label': name_label,
            'nodeid_label': nodeid_label,
            'status_label': status_label,
            'heard_label': heard_label,
            'voltage_label': voltage_label,
            'temp_label': temp_label,
            'util_label': util_label,
            'snr_label': snr_label,
            'battery_label': battery_label,
            'motion_label': motion_label,
        }
        
        # Schedule flash removal if this is a changed card
        if is_changed:
            self.flash_card(node_id, card_frame)
    
    def update_node_card(self, node_id: str, node_data: Dict[str, Any], current_time: float, is_changed: bool = False):
        """Update existing card without recreating it (prevents flickering)"""
        if node_id not in self.card_widgets:
            return
            
        card_info = self.card_widgets[node_id]
        
        # Flash the card if data changed
        if is_changed:
            self.flash_card(node_id, card_info['frame'])
        
        # Update node name if it changed (e.g., from "Unknown Node" to actual name)
        long_name = node_data.get('Node LongName', 'Unknown')
        display_name = long_name.replace("AG6WR-", "") if long_name.startswith("AG6WR-") else long_name
        card_info['name_label'].config(text=display_name)
        
        # Update short name if it changed
        short_name = node_data.get('Node ShortName', node_id[-4:])
        card_info['nodeid_label'].config(text=f"({short_name})")
        
        # Update status
        last_heard = node_data.get('Last Heard', 0)
        time_diff = current_time - last_heard if last_heard else float('inf')
        status = "Online" if time_diff <= 300 else "Offline"
        
        status_colors = {
            'Online': self.colors['fg_good'],
            'Offline': self.colors['fg_bad']
        }
        
        card_info['status_label'].config(text=status, fg=status_colors.get(status, self.colors['fg_normal']))
        
        # Update static timestamp for offline nodes, hide for online nodes
        if status == "Offline" and last_heard:
            from datetime import datetime
            heard_dt = datetime.fromtimestamp(last_heard)
            heard_text = f"Last heard: {heard_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            
            if card_info['heard_label']:
                # Update existing label and make it visible
                card_info['heard_label'].config(text=heard_text, fg=self.colors['fg_bad'])
                card_info['heard_label'].pack(anchor="w", side="left")
            else:
                # Create label if it doesn't exist
                small_font = tkfont.Font(family="Consolas" if sys.platform.startswith("win") else "Courier New", size=9)
                heard_label = tk.Label(card_info['lastheard_frame'], text=heard_text,
                                      bg=card_info['lastheard_frame']['bg'], 
                                      fg=self.colors['fg_bad'],
                                      font=small_font)
                heard_label.pack(anchor="w", side="left")
                card_info['heard_label'] = heard_label
        elif card_info['heard_label']:
            # Online node - hide the label by unpacking it (but keep frame at fixed height)
            card_info['heard_label'].pack_forget()
        
        # Determine if data is stale (use grey color for stale data)
        is_stale = status == "Offline"
        stale_color = self.colors['fg_secondary']  # Grey for stale data
        
        # Update telemetry fields
        voltage = node_data.get('Voltage')
        if voltage is not None and card_info['voltage_label']:
            voltage_text, voltage_color = self.get_voltage_display(voltage)
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else voltage_color
            card_info['voltage_label'].config(text=voltage_text, fg=display_color)
            
        temp = node_data.get('Temperature')
        if temp is not None and card_info['temp_label']:
            # Match table view: Red if >40°C or <0°C, Orange if 30-40°C, Green if 0-30°C
            if temp > 40 or temp < 0:
                temp_color = self.colors['fg_bad']  # Red for extreme temps
            elif temp >= 30:
                temp_color = self.colors['fg_warning']  # Orange for warm temps
            else:
                temp_color = self.colors['fg_good']  # Green for normal temps
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else temp_color
            temp_text = f"T: {temp:.1f}°C"
            card_info['temp_label'].config(text=temp_text, fg=display_color)
            
        channel_util = node_data.get('Channel Utilization')
        if channel_util is not None and card_info['util_label']:
            util_color = self.colors['fg_bad'] if channel_util > 80 else self.colors['fg_warning'] if channel_util > 50 else self.colors['fg_good']
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else util_color
            util_text = f"Ch: {channel_util:.1f}%"
            card_info['util_label'].config(text=util_text, fg=display_color)
            
        snr = node_data.get('SNR')
        if snr is not None and card_info['snr_label']:
            # SNR label is now a container with multiple labels
            # Destroy old content and recreate with new colors
            snr_container = card_info['snr_label']
            for widget in snr_container.winfo_children():
                widget.destroy()
            
            # Get current background color
            current_bg = snr_container['bg']
            
            # Icon - using text instead of emoji for Linux compatibility
            icon_label = tk.Label(snr_container, text="SNR:", bg=current_bg,
                                 fg=self.colors['fg_secondary'], font=self.font_data)
            icon_label.pack(side="left", padx=0)  # No padding
            
            # Get bar colors based on SNR level
            # Use pipe characters with different colors - all same width and baseline
            bar_chars = "||||"  # Four identical pipes/bars
            bar_colors = self.get_signal_bar_colors(snr)
            
            # Create smaller bold font for wider bars
            bar_font = tkfont.Font(family="Consolas" if sys.platform.startswith("win") else "Courier New", 
                                  size=9, weight="bold")  # Bold for wider pipes
            
            # Create each bar with its own color - NO spacing between bars
            # No anchor specified - use default center alignment to match text baseline
            for char, color in zip(bar_chars, bar_colors):
                bar_label = tk.Label(snr_container, text=char, bg=current_bg,
                                   fg=color, font=bar_font, padx=0, pady=0)
                bar_label.pack(side="left", padx=0, pady=0)
            
        battery = node_data.get('Battery Level')
        if battery is not None and card_info['battery_label']:
            # Red <10%, Orange 10-20%, Yellow 20-40%, Green 40-100%
            if battery < 10:
                battery_color = self.colors['fg_bad']  # Red for critical
            elif battery < 20:
                battery_color = self.colors['fg_warning']  # Orange for low
            elif battery < 40:
                battery_color = self.colors['fg_yellow']  # Yellow for caution
            else:
                battery_color = self.colors['fg_good']  # Green for good
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else battery_color
            battery_text = f"Bat: {battery:.0f}%"
            card_info['battery_label'].config(text=battery_text, fg=display_color)
        
        # Motion detection - show/hide based on recency AND online status
        last_motion = node_data.get('Last Motion')
        motion_display_duration = self.config_manager.get('dashboard.motion_display_seconds', 900)  # Default 15 minutes
        
        # Only show motion for ONLINE nodes with recent motion
        if status == "Online" and last_motion and (current_time - last_motion) <= motion_display_duration:
            # Motion is recent and node is online - show indicator (using text instead of emoji for Linux)
            if card_info['motion_label']:
                # Update existing label
                card_info['motion_label'].config(text="Motion detected", fg=self.colors['fg_good'])
                card_info['motion_label'].pack(fill="both", expand=True)
            else:
                # Create new motion label in existing metrics3_frame
                motion_label = tk.Label(card_info['metrics3_frame'], text="👀 Motion detected",
                                       bg=card_info['metrics3_frame']['bg'], 
                                       fg=self.colors['fg_good'],
                                       font=self.font_data, anchor='w')
                motion_label.pack(fill="both", expand=True)
                card_info['motion_label'] = motion_label
        elif card_info['motion_label']:
            # Motion is stale or node is offline - hide indicator
            card_info['motion_label'].pack_forget()
    
    def show_node_detail(self, node_id: str):
        """Show detailed information window for a node"""
        # Get fresh data from data_collector instead of self.nodes
        nodes_data = self.data_collector.get_nodes_data()
        
        if node_id not in nodes_data:
            logger.warning(f"Cannot show detail for unknown node: {node_id}")
            return
        
        node_data = nodes_data[node_id]
        
        # Create detail window
        detail_window = NodeDetailWindow(self, node_id, node_data)
        
        # Wire up button actions using stored button references
        detail_window.btn_logs.configure(command=lambda: self.open_logs_folder(node_id))
        detail_window.btn_csv.configure(command=lambda: self.open_today_csv(node_id))
        detail_window.btn_plot.configure(command=lambda: self.show_plot_for_node(node_id, detail_window.window))
    
    def show_plot_for_node(self, node_id: str, parent_window=None):
        """Show telemetry plot for a specific node
        
        Args:
            node_id: The node ID to plot
            parent_window: Optional parent window to position relative to
        """
        logger.info(f"Showing plot dialog for node: {node_id}")
        if self.plotter:
            # Pre-select this node in the plotter dialog
            # Strip the '!' prefix if present, as log directories don't use it
            clean_node_id = node_id.lstrip('!')
            self.plotter.show_plot_dialog(preselect_node_id=clean_node_id, parent_window=parent_window)
        else:
            messagebox.showwarning("Plotter Not Available", 
                                 "The telemetry plotter is not initialized.")
    
    def open_today_csv(self, node_id: str):
        """Open today's CSV file for the node in the default editor"""
        # Get the logs directory from config
        logs_dir = self.config_manager.get('data_collector.log_directory', 'logs')
        
        # Build path to today's CSV
        from datetime import datetime
        today_str = datetime.now().strftime('%Y-%m-%d')
        csv_path = os.path.join(logs_dir, f"{node_id}_{today_str}.csv")
        
        if not os.path.exists(csv_path):
            messagebox.showwarning("File Not Found", 
                                 f"No CSV file found for today:\n{csv_path}")
            return
        
        # Open with default application
        try:
            if sys.platform.startswith('win'):
                os.startfile(csv_path)
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', csv_path])
            else:
                subprocess.run(['xdg-open', csv_path])
        except Exception as e:
            messagebox.showerror("Error Opening File", 
                               f"Could not open CSV file:\n{str(e)}")
    
    def open_logs_folder(self, node_id: str):
        """Open the logs directory in the file explorer"""
        logs_dir = self.config_manager.get('data_collector.log_directory', 'logs')
        
        if not os.path.exists(logs_dir):
            messagebox.showwarning("Directory Not Found", 
                                 f"Logs directory does not exist:\n{logs_dir}")
            return
        
        try:
            if sys.platform.startswith('win'):
                os.startfile(logs_dir)
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', logs_dir])
            else:
                subprocess.run(['xdg-open', logs_dir])
        except Exception as e:
            messagebox.showerror("Error Opening Folder", 
                               f"Could not open logs folder:\n{str(e)}")
    
    def flash_card(self, node_id: str, card_frame):
        """Flash card background to indicate update - dark blue for 1 second"""
        # Cancel any existing flash timer for this card
        if node_id in self.flash_timers:
            self.after_cancel(self.flash_timers[node_id])
        
        # Function to restore normal background
        def restore_bg():
            card_info = self.card_widgets.get(node_id)
            if card_info:
                normal_bg = self.colors['bg_frame']
                card_frame.config(bg=normal_bg)
                # Update all child frames
                for key in ['header_frame', 'left_header', 'right_header', 
                           'lastheard_frame',
                           'metrics1_frame', 'metrics2_frame', 'metrics3_frame',
                           'col1_frame', 'col2_frame', 'col3_frame',
                           'row2_col1_frame', 'row2_col2_frame']:
                    if key in card_info and card_info[key]:
                        card_info[key].config(bg=normal_bg)
                # Update all labels
                for key in ['name_label', 'nodeid_label', 'status_label', 'heard_label',
                           'voltage_label', 'temp_label', 'util_label',
                           'battery_label', 'motion_label']:
                    if key in card_info and card_info[key]:
                        card_info[key].config(bg=normal_bg)
                
                # Update SNR container and all its child labels
                if 'snr_label' in card_info and card_info['snr_label']:
                    card_info['snr_label'].config(bg=normal_bg)
                    # Update all bar labels inside the SNR container
                    for child in card_info['snr_label'].winfo_children():
                        if isinstance(child, tk.Label):
                            child.config(bg=normal_bg)
            if node_id in self.flash_timers:
                del self.flash_timers[node_id]
        
        # Schedule restoration after 1 second
        self.flash_timers[node_id] = self.after(1000, restore_bg)
    
    def get_voltage_display(self, voltage: float):
        """Get voltage display with appropriate color coding"""
        if voltage is not None:
            # Match table view: Red if <11V or >14.5V, Yellow if 11-12V or 14-14.5V, Green if 12-14V
            if voltage < 11.0 or voltage > 14.5:
                color = self.colors['fg_bad']  # Red for dangerous voltages
            elif voltage < 12.0 or voltage > 14.0:
                color = self.colors['fg_warning']  # Orange for low battery or slightly high
            else:
                color = self.colors['fg_good']  # Green for good battery (12-14V)
            return f"V: {voltage:.1f}V", color
        else:
            return "V: No voltage", self.colors['fg_secondary']
    
    def get_signal_bars(self, snr: float):
        """Convert SNR to visual signal bar representation using increasing height bars
        Builds string with 'on' bars (bright) and 'off' bars (dim unicode chars)"""
        
        # Use progressively taller bars for "on" and light/outline versions for "off"
        # ▁▃▅█ for on, ▔ (small top line) for off, or just spaces
        if snr >= 10:
            # All 4 bars on
            return "▁▃▅█", self.colors['fg_good']
        elif snr >= 5:
            # 3 bars on, 1 off - but since we can't mix colors in one label,
            # use dimmer color for entire thing to show 3/4 strength
            return "▁▃▅▔", '#90EE90'  
        elif snr >= 0:
            # 2 bars on, 2 off
            return "▁▃▔▔", '#ffaa00'
        elif snr >= -5:
            # 1 bar on, 3 off
            return "▁▔▔▔", '#ff6b35'
        else:
            # All bars off
            return "▔▔▔▔", '#666666'
    
    def get_signal_bar_colors(self, snr: float):
        """Return list of colors for each of the 4 signal bars based on SNR
        White for 'on' bars, black for 'off' bars"""
        white = '#FFFFFF'
        black = '#000000'
        
        if snr >= 10:
            # All 4 bars on (white)
            return [white, white, white, white]
        elif snr >= 5:
            # 3 bars on, last one off
            return [white, white, white, black]
        elif snr >= 0:
            # 2 bars on, last two off
            return [white, white, black, black]
        elif snr >= -5:
            # 1 bar on, last three off
            return [white, black, black, black]
        else:
            # All bars off (black)
            return [black, black, black, black]
    
    def format_time_ago(self, seconds: float):
        """Format time difference as human readable string"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h"
        else:
            return f"{int(seconds // 86400)}d"
    
    def toggle_view(self):
        """Toggle between table and card view"""
        if self.view_mode == "table":
            self.view_mode = "cards"
            self.view_btn.config(text="Table")
            self.table_frame.pack_forget()
            self.card_container.pack(fill="both", expand=True, padx=8, pady=8)
        else:
            self.view_mode = "table"
            self.view_btn.config(text="Cards")
            self.card_container.pack_forget()
            self.table_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Force a refresh to update the display
        self.force_refresh()
    
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
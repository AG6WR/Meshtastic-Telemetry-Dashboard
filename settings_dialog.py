"""
settings_dialog.py - Settings Dialog for Meshtastic Dashboard

This module contains the SettingsDialog class extracted from dashboard.py
as part of Phase 2 modularization. The dialog handles all configuration
settings including connection, dashboard display, telemetry, alerts, 
email, and logging.

This class can be reused by both Tkinter and (future) Qt implementations,
as Qt can embed Tkinter dialogs if needed during transition.

Usage:
    from settings_dialog import SettingsDialog
    
    dialog = SettingsDialog(parent_window, config_manager)
    parent_window.wait_window(dialog.dialog)
    if dialog.result:
        # Settings were saved
        pass
"""

import sys
import logging
import tkinter as tk
from tkinter import messagebox, ttk

from config_manager import ConfigManager

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
        # Configure tab style with narrower font to prevent button growth
        style = ttk.Style()
        style.configure('TNotebook.Tab', font=("Liberation Sans", 12))
        
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
        
        # Logging tab
        logging_frame = ttk.Frame(notebook)
        notebook.add(logging_frame, text="Logging")
        self.create_logging_tab(logging_frame)
        
        # Buttons - enlarged for touch input
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 11))
        
        tk.Button(button_frame, text="Test Email", command=self.test_email,
                 width=12, height=2).pack(side="left", padx=(0, 5))
        tk.Button(button_frame, text="Cancel", command=self.cancel,
                 width=10, height=2).pack(side="right")
        tk.Button(button_frame, text="Apply", command=self.apply,
                 width=10, height=2).pack(side="right", padx=(0, 5))
        tk.Button(button_frame, text="OK", command=self.ok,
                 width=10, height=2).pack(side="right", padx=(0, 5))
    
    def create_connection_tab(self, parent):
        """Create connection settings tab"""
        # Connection Type Selection
        type_group = ttk.LabelFrame(parent, text="Connection Type")
        type_group.pack(fill="x", padx=5, pady=5)
        
        self.conn_type = tk.StringVar(value="tcp")
        
        type_frame = tk.Frame(type_group)
        type_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Radiobutton(type_frame, text="TCP/IP Network", variable=self.conn_type, value="tcp",
                      command=self._toggle_connection_fields).pack(side="left", padx=10)
        tk.Radiobutton(type_frame, text="USB/Serial Port", variable=self.conn_type, value="serial",
                      command=self._toggle_connection_fields).pack(side="left", padx=10)
        
        # TCP/IP Settings
        self.tcp_group = ttk.LabelFrame(parent, text="Meshtastic TCP/IP Interface")
        self.tcp_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(self.tcp_group, text="Host/IP Address:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.tcp_host = tk.Entry(self.tcp_group, width=20)
        self.tcp_host.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(self.tcp_group, text="Port:").grid(row=0, column=2, sticky="w", padx=(20, 5), pady=5)
        self.tcp_port = tk.Entry(self.tcp_group, width=8)
        self.tcp_port.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        
        self.tcp_group.grid_columnconfigure(1, weight=1)
        
        # USB/Serial Settings
        self.serial_group = ttk.LabelFrame(parent, text="USB/Serial Interface")
        self.serial_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(self.serial_group, text="Serial Port:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        # Create frame for port selector and refresh button
        port_frame = tk.Frame(self.serial_group)
        port_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        self.serial_port = ttk.Combobox(port_frame, width=18)
        self.serial_port.pack(side="left", fill="x", expand=True)
        
        refresh_btn = tk.Button(port_frame, text="↻", width=3, command=self._refresh_serial_ports)
        refresh_btn.pack(side="left", padx=(5, 0))
        
        tk.Label(self.serial_group, text="(e.g., COM3 on Windows, /dev/ttyUSB0 on Linux)").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        
        tk.Label(self.serial_group, text="Baud Rate:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.serial_baud = ttk.Combobox(self.serial_group, values=["9600", "19200", "38400", "57600", "115200"], width=10)
        self.serial_baud.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.serial_baud.set("115200")
        
        self.serial_group.grid_columnconfigure(1, weight=1)
        
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
        
        tk.Label(display_group, text="Temperature Unit:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.temp_unit = ttk.Combobox(display_group, values=["Celsius (°C)", "Fahrenheit (°F)"], state="readonly", width=15)
        self.temp_unit.grid(row=3, column=1, sticky="w", padx=5, pady=5)
    
    def create_telemetry_tab(self, parent):
        """Create telemetry field settings tab"""
        info_label = tk.Label(parent, text="Select which telemetry fields to display in card view:", 
                             font=('Liberation Sans', 11, 'bold'))
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
                               font=('Liberation Sans', 11, 'bold'), width=20, anchor='w')
            cb.pack(side="left")
            
            # Description
            desc_label = tk.Label(field_frame, text=description, 
                                 font=('Liberation Sans', 10), fg='gray')
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
        # Info label showing offline status threshold (hardcoded at 16 minutes)
        tk.Label(offline_frame, text="(Offline status threshold: 16 min)", 
                fg="#808080", font=("TkDefaultFont", 8)).pack(side="left", padx=(10, 0))
        
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
    
    def create_logging_tab(self, parent):
        """Create logging settings tab"""
        # Log Level Group
        level_group = ttk.LabelFrame(parent, text="Log Level")
        level_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(level_group, text="Select logging verbosity:").pack(anchor="w", padx=5, pady=(5, 0))
        
        self.log_level = ttk.Combobox(level_group, values=[
            "Disable Logging",
            "CRITICAL",
            "ERROR",
            "WARNING",
            "INFO",
            "DEBUG"
        ], state="readonly", width=20)
        self.log_level.pack(anchor="w", padx=5, pady=5)
        
        # Help text
        help_text = (
            "DEBUG: Most verbose - shows all diagnostic details\n"
            "INFO: Normal operation messages and updates\n"
            "WARNING: Unexpected events that don't stop operation\n"
            "ERROR: Serious problems that prevent features from working\n"
            "CRITICAL: Severe errors that may crash the application\n"
            "Disable Logging: Turn off all logging output"
        )
        help_label = tk.Label(level_group, text=help_text, justify="left", font=("TkDefaultFont", 8))
        help_label.pack(anchor="w", padx=5, pady=(0, 5))
        
        # Log Retention Group
        retention_group = ttk.LabelFrame(parent, text="Log File Retention")
        retention_group.pack(fill="x", padx=5, pady=5)
        
        tk.Label(retention_group, text="Delete log files older than:").pack(anchor="w", padx=5, pady=(5, 0))
        
        self.log_retention_days = ttk.Combobox(retention_group, values=[
            "5 days",
            "30 days",
            "60 days",
            "90 days",
            "360 days",
            "Forever"
        ], state="readonly", width=20)
        self.log_retention_days.pack(anchor="w", padx=5, pady=5)
        
        retention_help = tk.Label(retention_group, 
            text="Application logs (meshtastic_monitor.log) will be cleaned up automatically.\n"
                 "Node CSV logs are managed separately by the Data settings.",
            justify="left", font=("TkDefaultFont", 8))
        retention_help.pack(anchor="w", padx=5, pady=(0, 5))
    
    def _refresh_serial_ports(self):
        """Refresh the list of available serial ports"""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            port_list = [port.device for port in sorted(ports)]
            
            if not port_list:
                # No ports found, provide common defaults
                if sys.platform.startswith('win'):
                    port_list = ['COM3', 'COM4', 'COM5']
                else:
                    port_list = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']
            
            # Update combobox values
            self.serial_port['values'] = port_list
            
            # If no current value and ports available, select first one
            if not self.serial_port.get() and port_list:
                self.serial_port.set(port_list[0])
                
        except Exception as e:
            logger.warning(f"Failed to enumerate serial ports: {e}")
            # Provide defaults on error
            if sys.platform.startswith('win'):
                self.serial_port['values'] = ['COM3', 'COM4', 'COM5']
            else:
                self.serial_port['values'] = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0']
    
    def _toggle_connection_fields(self):
        """Show/hide connection fields based on selected type"""
        conn_type = self.conn_type.get()
        if conn_type == "tcp":
            self.tcp_group.pack(fill="x", padx=5, pady=5, after=self.tcp_group.master.winfo_children()[0])
            self.serial_group.pack_forget()
        else:  # serial
            self.serial_group.pack(fill="x", padx=5, pady=5, after=self.serial_group.master.winfo_children()[0])
            self.tcp_group.pack_forget()
    
    def load_current_values(self):
        """Load current configuration values into dialog"""
        # Connection settings
        interface_type = self.config_manager.get('meshtastic.interface.type', 'tcp')
        self.conn_type.set(interface_type)
        
        self.tcp_host.insert(0, self.config_manager.get('meshtastic.interface.host', '192.168.1.91'))
        self.tcp_port.insert(0, str(self.config_manager.get('meshtastic.interface.port', 4403)))
        
        # Load serial port and refresh available ports
        self._refresh_serial_ports()
        saved_serial_port = self.config_manager.get('meshtastic.interface.serial_port', '')
        if saved_serial_port:
            self.serial_port.set(saved_serial_port)
        self.serial_baud.set(str(self.config_manager.get('meshtastic.interface.baud', 115200)))
        
        self.conn_timeout.insert(0, str(self.config_manager.get('meshtastic.connection_timeout', 30)))
        self.retry_interval.insert(0, str(self.config_manager.get('meshtastic.retry_interval', 60)))
        
        # Toggle connection fields based on type
        self._toggle_connection_fields()
        
        # Dashboard settings
        self.time_format.set(self.config_manager.get('dashboard.time_format', 'DDd:HHh:MMm:SSs'))
        self.stale_row_seconds.insert(0, str(self.config_manager.get('dashboard.stale_row_seconds', 300)))
        self.motion_display_seconds.insert(0, str(self.config_manager.get('dashboard.motion_display_seconds', 900)))
        
        # Temperature unit setting
        temp_unit_value = self.config_manager.get('dashboard.temperature_unit', 'C')
        self.temp_unit.set('Celsius (°C)' if temp_unit_value == 'C' else 'Fahrenheit (°F)')
        
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
        
        # Logging settings
        log_level = self.config_manager.get('logging.level', 'INFO')
        if log_level == 'NOTSET':
            self.log_level.set('Disable Logging')
        else:
            self.log_level.set(log_level)
        
        retention_days = self.config_manager.get('logging.retention_days', -1)
        if retention_days == -1:
            self.log_retention_days.set('Forever')
        else:
            self.log_retention_days.set(f'{retention_days} days')
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
            conn_type = self.conn_type.get()
            self.config_manager.set('meshtastic.interface.type', conn_type)
            
            if conn_type == 'tcp':
                self.config_manager.set('meshtastic.interface.host', self.tcp_host.get())
                self.config_manager.set('meshtastic.interface.port', int(self.tcp_port.get()))
            else:  # serial
                self.config_manager.set('meshtastic.interface.serial_port', self.serial_port.get())
                self.config_manager.set('meshtastic.interface.baud', int(self.serial_baud.get()))
            
            self.config_manager.set('meshtastic.connection_timeout', int(self.conn_timeout.get()))
            self.config_manager.set('meshtastic.retry_interval', int(self.retry_interval.get()))
            
            # Dashboard settings
            self.config_manager.set('dashboard.time_format', self.time_format.get())
            self.config_manager.set('dashboard.stale_row_seconds', int(self.stale_row_seconds.get()))
            self.config_manager.set('dashboard.motion_display_seconds', int(self.motion_display_seconds.get()))
            
            # Temperature unit setting
            temp_unit_value = 'C' if 'Celsius' in self.temp_unit.get() else 'F'
            self.config_manager.set('dashboard.temperature_unit', temp_unit_value)
            
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
            
            # Logging settings
            log_level_value = self.log_level.get()
            if log_level_value == 'Disable Logging':
                self.config_manager.set('logging.level', 'NOTSET')
            else:
                self.config_manager.set('logging.level', log_level_value)
            
            retention_value = self.log_retention_days.get()
            if retention_value == 'Forever':
                self.config_manager.set('logging.retention_days', -1)
            else:
                days = int(retention_value.split()[0])
                self.config_manager.set('logging.retention_days', days)
            
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

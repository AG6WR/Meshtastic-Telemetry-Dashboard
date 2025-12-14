"""
Enhanced Dashboard GUI for Meshtastic Monitoring
Features: DDd:HHh:MMm:SSs time format, configurable settings, alert indicators

IMPORTANT BUG FIX NOTES (recurring issue):
-------------------------
CARD BLUE BACKGROUND BUG - Fixed multiple times, keep this note!

Root Cause:
- When cards are created during full rebuild (initial startup or layout change),
  the code was checking if node_id is in changed_nodes and setting is_changed=True
- At startup, self.last_node_data is empty, so ALL nodes appear "changed"
- This caused all cards to be created with bg_color = self.colors['bg_selected'] (blue)
  instead of bg_color = self.colors['bg_frame'] (dark grey)
- Labels then showed blue background until first data update called update_node_card()

The Fix:
- In display_card_view(), during full rebuild (when existing_nodes != current_nodes),
  ALWAYS create cards with is_changed=False
- The blue flash should ONLY happen in update_node_card() when data actually changes,
  NOT during initial card creation
- Line ~1522: self.create_node_card(..., is_changed=False)  # Always False during rebuild

This bug has recurred multiple times during development. The key insight:
- Initial card creation = normal background (dark grey)
- Data updates = blue flash via update_node_card()
- Never flash during rebuild/initial display
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
from pubsub import pub

from config_manager import ConfigManager
from data_collector import DataCollector
from plotter import TelemetryPlotter
from node_detail_window import NodeDetailWindow
from message_dialog import MessageDialog
from message_manager import MessageManager
from message_viewer import MessageViewer
from card_field_registry import CardFieldRegistry

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
        
        # Logging tab
        logging_frame = ttk.Frame(notebook)
        notebook.add(logging_frame, text="Logging")
        self.create_logging_tab(logging_frame)
        
        # Buttons - enlarged for touch input
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
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
    
    def _refresh_serial_ports(self):
        """Refresh the list of available serial ports"""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            port_list = [port.device for port in sorted(ports)]
            
            if not port_list:
                # No ports found, provide common defaults
                import sys
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
            import sys
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

# Version number - update manually with each release
VERSION = "1.2.0b"

def get_version_info():
    """Get version information"""
    return f"v{VERSION}"

class EnhancedDashboard(tk.Tk):
    """Enhanced dashboard with configurable settings and alert integration"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize configuration
        self.config_manager = ConfigManager()
        self.message_manager = MessageManager(self.config_manager)
        self.data_collector = None
        self.plotter = TelemetryPlotter(self, self.config_manager)
        self.field_registry = CardFieldRegistry(self)  # Field update registry
        
        # UI State
        self.nodes = {}
        self.row_labels = {}
        self.card_widgets = {}  # Cache for card widgets to prevent flickering
        self.last_node_data = {}  # Track last data for each node to detect changes
        self.flash_timers = {}  # Track active flash timers for cards
        self.selected_node_id = None
        self.last_refresh = 0
        self.view_mode = "cards"  # "table" or "cards" - default to cards view
        self.current_cards_per_row = 0  # Track current column count for resize detection
        
        # Message tracking
        self.recent_messages = []  # List of (from_name, to_name, text) tuples - last 3
        self.notification_banner = None  # Single banner frame at bottom
        self.notification_label = None  # Label showing scrolling messages
        self.notification_index = 0  # Current message being displayed
        self.notification_timer = None  # Timer for rotating messages
        self.message_timers = {}  # {node_id: timer_id}
        self.unread_messages = {}  # node_id -> list of unread messages
        self.message_flash_state = {}  # node_id -> True/False for blue/grey flash
        
        # Subscribe to critical connection errors
        pub.subscribe(self._on_critical_error, "meshtastic.connection.critical_error")
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        
        # Log motion display configuration
        motion_duration = self.config_manager.get('dashboard.motion_display_seconds', 900)
        logger.info(f"Motion display configuration: motion_display_seconds={motion_duration} ({motion_duration/60:.1f} minutes)")
        
        # Initialize GUI
        self.setup_gui()
        self.start_data_collection()
        
        # Load unread messages from storage
        self._load_unread_messages()
        
        # Initial display update
        self.after(1000, self.refresh_display)
        
        # Start periodic refresh timer (every 15 minutes) to catch status changes
        # This ensures nodes transition to offline even when no new telemetry arrives
        self.start_periodic_refresh()
        
        # Start message flash animation timer (1 second cycle)
        self._start_message_flash_timer()
        
        # Start log cleanup timer (daily)
        self.after(60000, self.cleanup_old_logs)  # Start after 1 minute, then runs daily
    
    def setup_gui(self):
        """Setup the GUI"""
        # Window settings
        self.title("Enhanced Meshtastic Monitor")
        
        # Set geometry for 1280x720 touchscreen display (leave room for Pi menu bar)
        # Default windowed size fits 3x3 card grid with controls
        geometry = self.config_manager.get('dashboard.window_geometry', '1200x660')
        self.geometry(geometry)
        
        # Enable fullscreen mode by default (hides Pi OS menubar)
        # F11 toggles fullscreen on/off
        self.is_fullscreen = True
        self.attributes('-fullscreen', True)
        self.bind('<F11>', self._toggle_fullscreen)
        
        # Escape exits fullscreen and restores normal window, or dismisses active menu
        def escape_handler(e):
            # First check if there's an active menu to dismiss
            if self.active_menu:
                try:
                    self.active_menu.unpost()
                    self.active_menu = None
                except:
                    pass
            # Otherwise, exit fullscreen if active
            elif self.is_fullscreen:
                self.is_fullscreen = False
                self.attributes('-fullscreen', False)
                self.attributes('-zoomed', False)  # Unset zoomed state on Linux
                self.state('normal')
                self.wm_geometry('')  # Clear geometry to reset window manager state
                geometry = self.config_manager.get('dashboard.window_geometry', '1200x660')
                self.geometry(geometry)
                self._update_fullscreen_button_text()
        
        self.bind('<Escape>', escape_handler)
        
        # Dark theme color palette
        # Usage: self.colors['key_name'] to reference colors throughout the application
        self.colors = {
            'bg_main': '#1e1e1e',        # Main window background
            'bg_frame': '#2d2d2d',       # Card/frame background (normal state)
            'bg_local_node': '#1e2d1e',  # Local node card background (dark green tint)
            'bg_stale': '#3d2d2d',       # Table rows with stale data (dark red tint)
            'bg_selected': '#1a237e',    # Selected table rows and flash effect (very dark blue)
            'fg_normal': '#ffffff',      # Primary text color (white)
            'fg_secondary': '#b0b0b0',   # Labels and stale data text (light gray)
            'button_bg': '#404040',      # Button backgrounds
            'button_fg': '#ffffff',      # Button text
            'fg_good': '#228B22',        # Positive values: Online status, high battery, good SNR (forest green)
            'fg_warning': '#FFA500',     # Warning values: Medium battery, elevated temps (orange)
            'fg_yellow': '#FFFF00',      # Caution values: Moderate concerns (yellow)
            'fg_bad': '#FF6B9D'          # Negative values: Offline status, low battery, errors (coral pink - better contrast than crimson)
        }
        
        # Configure main window
        self.configure(bg=self.colors['bg_main'])
        
        # Fonts - larger for better readability on small screens
        base_family = "Consolas" if sys.platform.startswith("win") else "Courier New"
        self.font_base = tkfont.Font(family=base_family, size=11)
        self.font_bold = tkfont.Font(family=base_family, size=11, weight="bold")
        self.font_data = tkfont.Font(family=base_family, size=12)  # Card view data font
        self.font_data_bold = tkfont.Font(family=base_family, size=12, weight="bold")  # Card view bold data
        self.font_card_header = tkfont.Font(family=base_family, size=14, weight="bold")  # Card header 14pt
        self.font_card_line2 = tkfont.Font(family=base_family, size=10)  # Card line 2 (Motion/Last Heard) 10pt - matches line 4
        self.font_card_line3 = tkfont.Font(family=base_family, size=14, weight="bold")  # Card line 3 (V/I/T) 14pt
        self.font_card_label = tkfont.Font(family=base_family, size=8)  # Card labels 8pt small (for "ICP Batt:", "Ch:", etc.)
        self.font_card_value = tkfont.Font(family=base_family, size=11, weight="bold")  # Card values 11pt bold (for data values)
        self.font_italic = tkfont.Font(family=base_family, size=11, slant="italic")
        self.font_title = tkfont.Font(family=base_family, size=18, weight="bold")
        
        # Title frame
        title_frame = tk.Frame(self, bg=self.colors['bg_main'])
        title_frame.pack(fill="x", padx=8, pady=(8, 0))
        
        # Title and version in same row
        title_container = tk.Frame(title_frame, bg=self.colors['bg_main'])
        title_container.pack(expand=True)
        
        title_label = tk.Label(title_container, 
                              text="CERT ICP Telemetry Dashboard",
                              font=self.font_title,
                              bg=self.colors['bg_main'], 
                              fg=self.colors['fg_normal'])
        title_label.pack(side="left", pady=(0, 8))
        
        # Version info
        version = get_version_info()
        version_label = tk.Label(title_container,
                                text=f" {version}",
                                font=self.font_base,
                                bg=self.colors['bg_main'],
                                fg=self.colors['fg_secondary'])
        version_label.pack(side="left", pady=(0, 8), padx=(8, 0))
        
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
        
        # Control buttons - enlarged for touch input (48x48px minimum)
        controls_frame = tk.Frame(self, bg=self.colors['bg_main'])
        controls_frame.pack(fill="x", padx=8, pady=(0, 6))
        
        tk.Button(controls_frame, text="Settings", command=self.open_settings,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                 width=9, height=2).pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Refresh", command=self.force_refresh,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                 width=9, height=2).pack(side="left", padx=(0, 5))
        # Button shows action (where you'll go) - starts as "Table" since default is cards
        self.view_btn = tk.Button(controls_frame, text="Table", command=self.toggle_view,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                 width=9, height=2)
        self.view_btn.pack(side="left", padx=(0, 5))
        
        # Messages button with unread count badge
        self.messages_btn = tk.Button(controls_frame, text="Messages", command=self.open_messages,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                 width=11, height=2)
        self.messages_btn.pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Plot", command=self.show_plot,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                 width=9, height=2).pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Node Alerts", command=self.open_node_alerts,
                 bg=self.colors['fg_warning'], fg='white',
                 width=11, height=2).pack(side="left", padx=(0, 5))
        tk.Button(controls_frame, text="Debug Log", command=self.open_debug_log,
                 bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                 width=10, height=2).pack(side="left", padx=(0, 5))
        self.btn_logs = tk.Button(controls_frame, text="Open Logs", command=self.open_logs_folder, state="disabled",
                                 bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                                 width=10, height=2)
        self.btn_logs.pack(side="left", padx=(0, 5))
        self.btn_csv = tk.Button(controls_frame, text="Today's CSV", command=self.open_today_csv, state="disabled",
                                bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                                width=11, height=2)
        self.btn_csv.pack(side="left", padx=(0, 5))
        
        # Fullscreen toggle button (right side) for touch-screen interface
        # Text shows the action it will perform (where you'll go)
        self.fullscreen_button = tk.Button(controls_frame, text="", command=self._toggle_fullscreen_button,
                 bg=self.colors['fg_bad'], fg='white',
                 width=13, height=2)
        self.fullscreen_button.pack(side="right", padx=(5, 0))
        self._update_fullscreen_button_text()  # Set initial text based on state
        
        # Quit button (right side, before fullscreen)
        tk.Button(controls_frame, text="Quit", command=self.quit_app,
                 bg=self.colors['fg_bad'], fg='white',
                 width=9, height=2).pack(side="right", padx=(0, 5))
        
        # Table container with horizontal scrollbar (initially hidden since default is cards)
        self.table_container = tk.Frame(self, bg=self.colors['bg_frame'])
        # Don't pack yet - cards is default view
        
        # Create canvas for scrolling
        self.table_canvas = tk.Canvas(self.table_container, bg=self.colors['bg_frame'], highlightthickness=0)
        self.table_canvas.pack(side="top", fill="both", expand=True)
        
        # Horizontal scrollbar - widened for touch input (24px)
        self.h_scrollbar = tk.Scrollbar(self.table_container, orient="horizontal", command=self.table_canvas.xview, width=24)
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.table_canvas.configure(xscrollcommand=self.h_scrollbar.set)
        
        # Table frame inside canvas
        self.table_frame = tk.Frame(self.table_canvas, bg=self.colors['bg_frame'])
        self.table_canvas.create_window((0, 0), window=self.table_frame, anchor="nw")
        
        # Update scroll region when table frame changes size
        def update_scrollregion(event):
            self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all"))
        self.table_frame.bind("<Configure>", update_scrollregion)
        
        # Card container frame (initially shown since cards is default)
        self.setup_card_container()
        self.card_container.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Setup table columns
        self.setup_table()
        
        # Protocol for window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _generate_message_id(self) -> str:
        """Generate a unique message ID in format <sender_short>_<timestamp_ms>.
        
        Returns:
            Message ID string (e.g., '0de0_1734112345678')
        """
        import time
        local_node_id = self.config_manager.get('meshtastic.local_node_id')
        if local_node_id and local_node_id.startswith('!'):
            short_id = local_node_id[1:]  # Remove '!' prefix
        else:
            short_id = 'unknown'
        
        timestamp_ms = int(time.time() * 1000)
        return f"{short_id}_{timestamp_ms}"
    
    def _get_local_node_id(self) -> str:
        """Get the local node ID from the connected interface.
        
        Returns:
            Local node ID string (e.g., '!a20a0de0') or empty string if not available
        """
        # First try to get it from the active connection
        if self.data_collector and self.data_collector.connection_manager:
            node_id = self.data_collector.connection_manager.get_local_node_id()
            if node_id:
                # Update config if it changed
                cached_id = self.config_manager.get('meshtastic.local_node_id')
                if cached_id != node_id:
                    logger.info(f"Local node changed from {cached_id} to {node_id}")
                    self.config_manager.set('meshtastic.local_node_id', node_id)
                return node_id
        
        # Fall back to cached value if no active connection
        return self.config_manager.get('meshtastic.local_node_id') or ''
    
    def _toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode (F11 key)"""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)
        
        # When exiting fullscreen, restore to normal window (not maximized)
        if not self.is_fullscreen:
            self.attributes('-zoomed', False)  # Unset zoomed state on Linux
            self.state('normal')
            self.wm_geometry('')  # Clear geometry to reset window manager state
            # Restore saved geometry or use default
            geometry = self.config_manager.get('dashboard.window_geometry', '1200x660')
            self.geometry(geometry)
        
        self._update_fullscreen_button_text()  # Update button text to reflect new state
        logger.info(f"Fullscreen mode: {'ON' if self.is_fullscreen else 'OFF'}")
    
    def _toggle_fullscreen_button(self):
        """Toggle fullscreen mode (for button clicks)"""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)
        
        # When exiting fullscreen, restore to normal window (not maximized)
        if not self.is_fullscreen:
            self.attributes('-zoomed', False)  # Unset zoomed state on Linux
            self.state('normal')
            self.wm_geometry('')  # Clear geometry to reset window manager state
            # Restore saved geometry or use default
            geometry = self.config_manager.get('dashboard.window_geometry', '1200x660')
            self.geometry(geometry)
        
        self._update_fullscreen_button_text()  # Update button text to reflect new state
        logger.info(f"Fullscreen mode: {'ON' if self.is_fullscreen else 'OFF'} (via button)")
    
    def _update_fullscreen_button_text(self):
        """Update fullscreen button text based on current state
        Button shows the action it will perform (where you'll go)"""
        if self.is_fullscreen:
            self.fullscreen_button.config(text="Exit Fullscreen")
        else:
            self.fullscreen_button.config(text="Fullscreen")
    
    def _load_unread_messages(self):
        """Load unread messages from storage and populate cache.
        
        Triggers card line 2 update if unread count changes.
        """
        try:
            local_node_id = self._get_local_node_id()
            if not local_node_id:
                logger.warning("Cannot load unread messages: local node ID not available yet")
                return
            
            # Track previous count to detect changes
            prev_count = len(self.unread_messages.get(local_node_id, []))
            
            # Get unread messages for local node
            unread = self.message_manager.get_unread_messages(local_node_id)
            
            logger.info(f"_load_unread_messages: local_node_id={local_node_id}, prev_count={prev_count}, new_count={len(unread) if unread else 0}")
            
            if unread:
                self.unread_messages[local_node_id] = unread
                new_count = len(unread)
                logger.info(f"Loaded {new_count} unread message(s) for local node {local_node_id}")
                
                # If count changed and card exists, update line 2
                if new_count != prev_count and local_node_id in self.card_widgets:
                    logger.info(f"Unread count changed ({prev_count} -> {new_count}), updating card line 2")
                    self._update_card_line2(local_node_id)
            else:
                # No unread messages - clear cache if needed
                if prev_count > 0:
                    self.unread_messages[local_node_id] = []
                    logger.info("No unread messages found, clearing cache")
                    # Update line 2 to remove message display
                    if local_node_id in self.card_widgets:
                        self._update_card_line2(local_node_id)
                else:
                    logger.debug("No unread messages found")
                
        except Exception as e:
            logger.error(f"Error loading unread messages: {e}", exc_info=True)
    
    def convert_temperature(self, temp_c, to_unit=None):
        """Convert temperature from Celsius to the configured unit
        
        Args:
            temp_c: Temperature in Celsius
            to_unit: Override unit ('C' or 'F'), or None to use config setting
            
        Returns:
            tuple: (converted_value, unit_string, thresholds_tuple)
                   thresholds_tuple = (red_threshold, yellow_threshold)
        """
        if to_unit is None:
            to_unit = self.config_manager.get('dashboard.temperature_unit', 'C')
        
        if to_unit == 'F':
            # Convert to Fahrenheit: F = C * 9/5 + 32
            temp_f = temp_c * 9/5 + 32
            # Thresholds: 45°C = 113°F, 35°C = 95°F
            return (temp_f, '°F', (113, 95))
        else:
            # Keep in Celsius
            return (temp_c, '°C', (45, 35))
    
    # =========================================================================
    # Field Registry Helper Methods
    # These methods are called by card_field_registry.py for formatting/coloring
    # =========================================================================
    
    def format_temperature(self, temp_c):
        """Format temperature value (number only, unit is separate label)"""
        temp_value, temp_unit_str, _ = self.convert_temperature(temp_c)
        return f"{temp_value:.0f}"
    
    def get_temperature_color(self, temp_c):
        """Get color based on temperature thresholds"""
        _, _, (red_threshold, yellow_threshold) = self.convert_temperature(temp_c)
        if temp_c > red_threshold or temp_c < 0:
            return self.colors['fg_bad']
        elif temp_c >= yellow_threshold:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_good']
    
    def format_humidity(self, humidity):
        """Format humidity value"""
        return f"{humidity:.0f}%"
    
    def get_humidity_color(self, humidity):
        """Get color based on humidity thresholds"""
        if humidity > 80 or humidity < 20:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_good']
    
    def format_pressure(self, pressure):
        """Format pressure value (number only, unit is separate label)"""
        return f"{pressure:.1f}"
    
    def get_pressure_color(self, pressure):
        """Get color based on pressure (always normal for now)"""
        return self.colors['fg_normal']
    
    def format_channel_util(self, util):
        """Format channel utilization percentage"""
        return f"Ch: {util:.1f}%"
    
    def get_channel_util_color(self, util):
        """Get color based on channel utilization thresholds"""
        if util > 25:
            return self.colors['fg_bad']
        elif util > 10:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_good']
    
    def format_air_util(self, util):
        """Format air utilization percentage"""
        return f"Air: {util:.1f}%"
    
    def get_air_util_color(self, util):
        """Get color based on air utilization thresholds"""
        if util > 10:
            return self.colors['fg_bad']
        elif util > 5:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_good']
    
    def setup_table(self):
        """Setup the data table"""
        # Column definitions: (title, key, width_chars, anchor, is_numeric)
        self.COLUMNS = [
            ("Node ID", "id", 10, "w", False),
            ("Name", "long", 18, "w", False), 
            ("Short", "short", 8, "center", False),
            ("Status", "status", 12, "center", False),
            ("Last Heard", "last_heard", 18, "center", False),
            ("Motion", "motion", 16, "center", False),
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
        
        # Track active menu for dismissal
        self.active_menu = None
        
        # Create scrollable canvas for cards
        self.card_canvas = tk.Canvas(self.card_container, bg=self.colors['bg_main'], highlightthickness=0)
        # Vertical scrollbar - widened for touch input (24px)
        self.card_scrollbar = tk.Scrollbar(self.card_container, orient="vertical", command=self.card_canvas.yview, width=24)
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
        
        # Bind window resize to detect when card layout should change
        self.bind("<Configure>", self.on_window_resize)
    
    def on_window_resize(self, event):
        """Handle window resize - reflow cards if column count changes"""
        # Only handle main window resizes, not child widgets
        if event.widget != self:
            return
        
        # Calculate columns dynamically based on window width
        # Card width is 368px + 8px padding (4px each side) = 376px per card
        window_width = self.winfo_width()
        card_width_with_padding = 376
        new_cards_per_row = max(1, window_width // card_width_with_padding)
        
        # Only rebuild if column count actually changed
        if new_cards_per_row != self.current_cards_per_row and self.view_mode == "cards":
            self.current_cards_per_row = new_cards_per_row
            # Force a full card rebuild by clearing the card_widgets cache
            self.card_widgets.clear()
            self.refresh_display()
    
    def start_data_collection(self):
        """Start the data collection system"""
        try:
            self.data_collector = DataCollector()
            
            # Register callback for data changes (event-driven updates)
            self.data_collector.set_data_change_callback(self.on_data_changed)
            
            # Register callback for message reception
            self.data_collector.on_message_received = self._on_message_received
            
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
    
    def start_periodic_refresh(self):
        """Start periodic refresh timer to catch status changes (online->offline transitions)"""
        # v1.0.8 (2025-11-16): Refresh every 5 minutes to update node status
        # Status is time-based (current_time - last_heard) not data-based,
        # so offline transitions won't trigger updates without periodic refresh.
        # Clear last_node_data cache to force all cards to recalculate status.
        self.last_node_data.clear()
        self.refresh_display()
        self.after(300000, self.start_periodic_refresh)  # 5 minutes
    
    def _start_message_flash_timer(self):
        """Start periodic timer to toggle message flash state (1 second cycle)
        
        Also checks for new messages every 5 seconds to pick up externally injected messages.
        """
        try:
            # Check for new messages periodically (every 5 seconds)
            current_time = time.time()
            if not hasattr(self, '_last_message_check') or current_time - self._last_message_check >= 5.0:
                self._last_message_check = current_time
                # Only log if in debug mode - too chatty otherwise
                logger.debug("Flash timer: Checking for new messages (5-second interval)")
                self._load_unread_messages()
            
            # Check if any local node has unread messages
            local_node_id = self._get_local_node_id()
            has_unread = local_node_id and local_node_id in self.unread_messages and len(self.unread_messages[local_node_id]) > 0
            
            if has_unread:
                # Only log flash toggle at debug level - happens every second
                logger.debug(f"Flash timer: {local_node_id} has {len(self.unread_messages[local_node_id])} unread messages - toggling flash")
                # Toggle flash state
                current_state = self.message_flash_state.get(local_node_id, True)
                self.message_flash_state[local_node_id] = not current_state
                
                # Update card border for flash effect (toggle between blue and green)
                if self.view_mode == "cards" and local_node_id in self.card_widgets:
                    card_info = self.card_widgets[local_node_id]
                    # Flash border between blue (unread) and green (local node)
                    # Only change color, not thickness (to prevent size recalculation)
                    if self.message_flash_state[local_node_id]:
                        card_info['frame'].config(highlightbackground='#4a90e2')  # Light blue
                    else:
                        card_info['frame'].config(highlightbackground='#00AA00')  # Green
            else:
                # No unread messages - restore normal green border for local node
                if local_node_id and local_node_id in self.message_flash_state:
                    del self.message_flash_state[local_node_id]
                    
                    # Restore normal green border (only color, not thickness)
                    if self.view_mode == "cards" and local_node_id in self.card_widgets:
                        card_info = self.card_widgets[local_node_id]
                        card_info['frame'].config(highlightbackground='#00AA00')
        
        except Exception as e:
            logger.error(f"Error in flash timer: {e}", exc_info=True)
        
        finally:
            # Always reschedule next flash toggle (1000ms = 1 second)
            self.after(1000, self._start_message_flash_timer)
    
    def cleanup_old_logs(self):
        """Clean up old application log files based on retention settings"""
        try:
            retention_days = self.config_manager.get('logging.retention_days', 30)
            
            # -1 means keep forever, don't clean up
            if retention_days == -1:
                logger.debug("Log retention set to Forever - skipping cleanup")
                return
            
            log_file = 'logs/meshtastic_monitor.log'
            if not os.path.exists(log_file):
                return
            
            # Check file age
            file_mtime = os.path.getmtime(log_file)
            file_age_days = (time.time() - file_mtime) / 86400  # seconds to days
            
            if file_age_days > retention_days:
                # Archive old log with timestamp before deleting
                archive_name = f'logs/meshtastic_monitor_{datetime.fromtimestamp(file_mtime).strftime("%Y%m%d")}.log.old'
                try:
                    # Rename to archive
                    os.rename(log_file, archive_name)
                    logger.info(f"Archived old log file to {archive_name}")
                    
                    # Delete the archive (we just wanted to preserve it briefly)
                    os.remove(archive_name)
                    logger.info(f"Cleaned up log file older than {retention_days} days")
                except Exception as e:
                    logger.warning(f"Failed to clean up old log: {e}")
            else:
                logger.debug(f"Log file is {file_age_days:.1f} days old, retention is {retention_days} days")
            
            # Also clean up any .old archived logs older than retention period
            if os.path.exists('logs'):
                for filename in os.listdir('logs'):
                    if filename.endswith('.log.old'):
                        filepath = os.path.join('logs', filename)
                        file_age = (time.time() - os.path.getmtime(filepath)) / 86400
                        if file_age > retention_days:
                            try:
                                os.remove(filepath)
                                logger.info(f"Removed old archived log: {filename}")
                            except Exception as e:
                                logger.warning(f"Failed to remove {filename}: {e}")
        
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
        
        # Schedule next cleanup in 24 hours
        self.after(86400000, self.cleanup_old_logs)  # 24 hours in milliseconds
    
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
                elif conn_type == 'serial':
                    port = interface_info.get('port', 'unknown')
                    conn_text = f"Serial {port}"
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
            elif key == "motion":
                motion_detected = node_data.get('Motion Detected')
                if motion_detected:
                    age_seconds = current_time - motion_detected
                    if age_seconds < 60:
                        text = "Just now"
                    elif age_seconds < 3600:
                        text = f"{int(age_seconds / 60)} min ago"
                    elif age_seconds < 86400:
                        text = f"{int(age_seconds / 3600)} hr ago"
                    else:
                        text = f"{int(age_seconds / 86400)} days ago"
                else:
                    text = "—"
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
                            # Prefer Ch3 Voltage (external) over Voltage (battery)
                            display_voltage = node_data.get('Ch3 Voltage', value)
                            
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
                            # Color coding: >15% red (congested), 10-15% yellow (busy), <10% green (good)
                            if value > 15:
                                fg = self.colors['fg_bad']  # Red for high utilization
                            elif value >= 10:
                                fg = self.colors['fg_warning']  # Yellow for moderate utilization
                            else:
                                fg = self.colors['fg_good']  # Green for low utilization
                        elif key == 'Humidity':
                            text = f"{value:.0f}"
                            # Color coding: 20-60% green (ideal), else yellow
                            if 20 <= value <= 60:
                                fg = self.colors['fg_good']  # Green for ideal range
                            else:
                                fg = self.colors['fg_warning']  # Yellow for too dry/humid
                        elif key == 'Battery Level':
                            # Use get_battery_percentage_display to handle external battery (Ch3 Voltage)
                            battery_text, battery_color = self.get_battery_percentage_display(node_data)
                            # Extract just the percentage number from "Bat:XX%" format
                            if battery_text.startswith('Bat:'):
                                text = battery_text.replace('Bat:', '').replace('%', '')
                                fg = battery_color
                            elif battery_text == "no external battery sensor":
                                text = "—"
                                fg = self.colors['fg_secondary']
                            else:
                                text = f"{value:.0f}"
                                # Color coding: 0-25% red, 25-50% yellow, >50% green
                                if value > 50:
                                    fg = self.colors['fg_good']
                                elif value >= 25:
                                    fg = self.colors['fg_warning']
                                else:
                                    fg = self.colors['fg_bad']
                        elif key == 'Current':
                            text = f"{value:.0f}"
                            # Color coding: >100mA red (high draw), 50-100 yellow, <50 green (low draw)
                            if value > 100:
                                fg = self.colors['fg_bad']  # Red for high current draw
                            elif value >= 50:
                                fg = self.colors['fg_warning']  # Yellow for moderate draw
                            else:
                                fg = self.colors['fg_good']  # Green for low draw
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
        """Force an immediate refresh by rebuilding all cards
        
        This is the "hammer" approach - rebuilds the entire card structure.
        Generally prefer targeted container updates (_update_card_line2, etc.)
        for efficiency. Use force_refresh() only when:
        - Changing view modes (table <-> cards)
        - Node list changes (new nodes, nodes removed)
        - Complete UI reset needed
        """
        self.refresh_display()
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.config_manager)
        self.wait_window(dialog.dialog)
        
        if dialog.result:
            # Configuration changed, restart data collector if needed
            messagebox.showinfo("Settings", "Settings saved. Restart the application for all changes to take effect.")
    
    def open_logs_folder(self, node_id: str = None):
        """Open logs folder for selected node or specified node"""
        target_node_id = node_id if node_id else self.selected_node_id
        
        if not target_node_id:
            return
        
        log_dir = self.config_manager.get('data.log_directory', 'logs')
        clean_id = target_node_id[1:] if target_node_id.startswith('!') else target_node_id
        node_log_path = os.path.join(log_dir, clean_id)
        
        if os.path.exists(node_log_path):
            self.open_path(node_log_path)
        else:
            messagebox.showinfo("No Logs", f"No log directory found for {target_node_id}")
    
    def open_today_csv(self, node_id: str = None):
        """Open today's CSV file for selected node or specified node"""
        target_node_id = node_id if node_id else self.selected_node_id
        
        if not target_node_id:
            return
        
        log_dir = self.config_manager.get('data.log_directory', 'logs')
        clean_id = target_node_id[1:] if target_node_id.startswith('!') else target_node_id
        today = datetime.now()
        csv_path = os.path.join(log_dir, clean_id, today.strftime('%Y'), today.strftime('%Y%m%d') + '.csv')
        
        if os.path.exists(csv_path):
            self.open_path(csv_path)
        else:
            messagebox.showinfo("No CSV", f"No CSV file found for today for {target_node_id}")
    
    def open_debug_log(self):
        """Open the main debug log file"""
        log_path = os.path.join('logs', 'meshtastic_monitor.log')
        
        if os.path.exists(log_path):
            self.open_path(log_path)
        else:
            messagebox.showinfo("No Log", "Debug log file not found. It will be created when the application runs.")
    
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
                          for field in ['Voltage', 'Ch3 Voltage', 'Temperature', 'SNR', 'Battery Level'])
            if (last_heard is not None and last_heard > 0) or has_data:
                filtered_nodes[node_id] = node_data
        
        # Sort nodes like in table view, but put local node first
        current_time = time.time()
        local_node_id = self.config_manager.get('meshtastic.local_node_id')
        
        def sort_key(item):
            node_id, node_data = item
            # Local node always first (sort key -1)
            if node_id == local_node_id:
                return (-1, '')
            # Then by online/offline status and name
            return (self.get_node_sort_key(node_data, current_time),
                    node_data.get('Node LongName', 'Unknown'))
        
        sorted_nodes = sorted(filtered_nodes.items(), key=sort_key)
        
        # Check which nodes have changed data
        changed_nodes = set()
        changed_nodes_info = []  # For logging with names
        for node_id, node_data in sorted_nodes:
            if node_id not in self.last_node_data or self.last_node_data[node_id] != node_data:
                changed_nodes.add(node_id)
                self.last_node_data[node_id] = node_data.copy()
                # Collect node info for logging
                long_name = node_data.get('Node LongName', 'Unknown')
                short_name = node_data.get('Node ShortName', node_id[-4:])
                changed_nodes_info.append(f"{node_id} ({short_name}/{long_name})")
        
        # Log when cards are being updated
        if changed_nodes:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            logger.info(f"[{timestamp}] Card display updating for changed nodes: {', '.join(changed_nodes_info)}")
        
        # If layout needs rebuild (new/removed nodes or first time)
        existing_nodes = set(self.card_widgets.keys())
        current_nodes = set(dict(sorted_nodes).keys())
        
        if existing_nodes != current_nodes or not self.card_widgets:
            # Full rebuild needed
            for widget in self.card_scrollable_frame.winfo_children():
                widget.destroy()
            self.card_widgets.clear()
            
            # Calculate grid layout - cards are 345px wide (25% reduction from 460px)
            # Window width calculation: 1400 - 24 (scrollbar) - 20 (padding) = 1356 available
            # 1356 / 353 = 3.8, so 3 cards per row (353 = 345 card + 8px padding)
            window_width = self.winfo_width()
            card_width = 345  # Current card width (25% reduction)
            card_width_with_padding = 353  # Card + padding (4px each side)
            cards_per_row = max(1, window_width // card_width_with_padding)
            
            # Store current column count for resize detection
            self.current_cards_per_row = cards_per_row
            
            # CRITICAL: Configure grid columns to fixed width to prevent resizing
            # Without this, grid auto-sizes columns on ANY widget update (border color, text, etc.)
            # causing all cards to resize/"dance" during updates. Must set minsize and weight=0.
            for col_idx in range(cards_per_row):
                self.card_scrollable_frame.grid_columnconfigure(col_idx, minsize=card_width_with_padding, weight=0)
            
            # Create cards using grid layout with local node in upper left
            # Don't flash cards during full rebuild - only flash on data updates
            row = 0
            col = 0
            for node_id, node_data in sorted_nodes:
                is_local = (node_id == local_node_id)
                
                # Create card with normal background (no flash) during rebuild
                self.create_node_card(self.card_scrollable_frame, node_id, node_data, 
                                    row, col, card_width, is_changed=False, 
                                    is_local=is_local)
                
                # Update column position
                col += 1
                if col >= cards_per_row:
                    col = 0
                    row += 1
        else:
            # Update only changed cards
            for node_id in changed_nodes:
                if node_id in self.card_widgets and node_id in filtered_nodes:
                    self.update_node_card(node_id, filtered_nodes[node_id], current_time, is_changed=True)
    
    def create_node_card(self, parent, node_id: str, node_data: Dict[str, Any], row: int, col: int, card_width: int, is_changed: bool = False, is_local: bool = False):
        """Create a compact card for a single node
        
        Args:
            parent: Parent widget
            node_id: Node ID
            node_data: Node data dictionary
            row: Grid row position
            col: Grid column position
            card_width: Width of card (460px standard)
            is_changed: Whether to show blue flash
            is_local: Whether this is the local node (gets green background and border)
        """
        # Status colors
        status_colors = {
            'Online': self.colors['fg_good'],
            'Offline': self.colors['fg_bad']
        }
        
        # Determine node status based on any packet received
        current_time = time.time()
        last_heard = node_data.get('Last Heard', 0)
        time_diff = current_time - last_heard if last_heard else float('inf')
        # v1.0.8 (2025-11-16): Changed from 5min to 16min threshold
        # Nodes send telemetry every 15 minutes, 5min caused false offline states
        status = "Online" if time_diff <= 960 else "Offline"  # 16 minutes (960s)
        
        # Debug logging for node 30c0
        if '30c0' in node_id.lower():
            logger.info(f"Node {node_id} STATUS DEBUG (CREATE): last_heard={last_heard}, current_time={current_time}, time_diff={time_diff:.1f}s, status={status}")
        
        # Determine if telemetry data is stale (no telemetry in 16 minutes)
        last_telemetry = node_data.get('Last Telemetry Time', 0)
        telemetry_diff = current_time - last_telemetry if last_telemetry else float('inf')
        telemetry_stale = telemetry_diff > 960  # 16 minutes = 960 seconds
        
        # Check if this node has unread messages (only flash local node)
        has_unread_messages = is_local and node_id in self.unread_messages and len(self.unread_messages[node_id]) > 0
        
        # Main card background - local node gets green tint, others get normal grey
        # (Border will flash for unread messages, not background)
        if is_local:
            bg_color = self.colors['bg_local_node']  # Dark green tint for local node
        else:
            bg_color = self.colors['bg_frame']  # Normal dark grey for all other nodes
        
        # All cards get a 3px border (to maintain consistent size)
        # Local node: green border (or blue/green flash for unread messages)
        # Other nodes: dark grey border (invisible against background)
        if is_local:
            # Start with appropriate border color for local node
            if has_unread_messages:
                # Start with light blue if we have unread messages
                flash_blue = self.message_flash_state.get(node_id, True)
                border_color = '#4a90e2' if flash_blue else '#00AA00'  # Light blue or green
            else:
                border_color = '#00AA00'  # Green for local node
        else:
            # Non-local nodes get dark grey border (matches bg_frame)
            border_color = self.colors['bg_frame']
        
        border_config = {
            'highlightbackground': border_color,
            'highlightthickness': 3
        }
        
        card_frame = tk.Frame(parent, bg=bg_color, relief='raised', bd=2, **border_config)
        card_frame.grid(row=row, column=col, padx=4, pady=3, sticky="nsew")
        card_frame.grid_propagate(False)  # Lock size to prevent resize during updates
        card_frame.config(width=card_width, height=1)  # Fixed width, minimal height (will expand to content)
        
        # Header row - Name and Status only (short name moved to line 2)
        header_frame = tk.Frame(card_frame, bg=bg_color)
        header_frame.pack(fill="x", padx=6, pady=(3, 1))
        
        # Left side - Node name only
        left_header = tk.Frame(header_frame, bg=bg_color)
        left_header.pack(side="left")
        
        # Node name (bold, larger - 14pt)
        # If name is unknown in node_data, look it up from data_collector's cache
        long_name = node_data.get('Node LongName', 'Unknown')
        short_name = node_data.get('Node ShortName', node_id[-4:])
        
        # If we have "Unknown" or "Unknown Node", try to get real name from cache
        if long_name in ('Unknown', 'Unknown Node') and self.data_collector:
            cached_info = self.data_collector.node_info_cache.get(node_id)
            if cached_info:
                cached_long, cached_short = cached_info
                if cached_long and cached_long not in ('Unknown', 'Unknown Node'):
                    logger.info(f"CREATE {node_id}: Found '{cached_long}' in cache")
                    long_name = cached_long
                if cached_short and cached_short != 'Unknown':
                    short_name = cached_short
            else:
                logger.warning(f"CREATE {node_id}: Unknown but no cache entry")
        
        display_name = long_name.replace("AG6WR-", "") if long_name.startswith("AG6WR-") else long_name
        name_label = tk.Label(left_header, text=display_name, 
                             bg=bg_color, fg=self.colors['fg_normal'], 
                             font=self.font_card_header)
        name_label.pack(side="left")
        
        # Local node badge
        if is_local:
            local_badge = tk.Label(left_header, text=" 📍",
                                  bg=bg_color, fg='#00AA00',
                                  font=self.font_card_header)
            local_badge.pack(side="left")
        
        # Right side - Menu button, message indicator, and status
        right_header = tk.Frame(header_frame, bg=bg_color)
        right_header.pack(side="right")
        
        # Menu button (⋮ vertical ellipsis) - 48x48px touch target
        def show_card_menu(event=None):
            # Dismiss any active menu first
            if self.active_menu:
                try:
                    self.active_menu.unpost()
                except:
                    pass
            
            menu = tk.Menu(self, tearoff=0,
                          bg=self.colors['bg_frame'],
                          fg=self.colors['fg_normal'],
                          activebackground=self.colors['bg_selected'],
                          activeforeground=self.colors['fg_normal'])
            menu.add_command(label="View Details", command=lambda: self.show_node_detail(node_id))
            menu.add_command(label="Show Logs", command=lambda: self.open_logs_folder(node_id))
            menu.add_command(label="Open CSV", command=lambda: self.open_today_csv(node_id))
            menu.add_command(label="Plot Telemetry", command=lambda: self.show_plot_for_node(node_id))
            menu.add_command(label=f"Send Message To '{display_name}'...", command=lambda: self._send_message_to_node(node_id))
            # Only add Forget Node option if this is NOT the local node
            if not is_local:
                menu.add_command(label=f"Forget Node '{display_name}'", command=lambda: self._forget_node_from_card(node_id))
            
            # Track this as active menu
            self.active_menu = menu
            
            # Post menu at event coordinates (card was clicked)
            # Use tk_popup instead of post - tk_popup auto-handles grab/release
            if event:
                try:
                    menu.tk_popup(event.x_root, event.y_root)
                finally:
                    menu.grab_release()
            
            # Stop event propagation to prevent card click
            if event:
                return "break"
        
        # Menu button removed - entire card is now clickable to show context menu
        menu_button = None  # Keep variable for compatibility
        
        # Bind card click to show menu (show_card_menu handles dismissing old menu)
        card_frame.bind('<Button-1>', show_card_menu)
        
        # Message indicator (always create it, show/hide based on message time)
        msg_indicator = tk.Label(right_header, text="📧 ",
                                bg=bg_color, fg=self.colors['fg_normal'],
                                font=self.font_card_header)
        
        # Add click handler to message indicator to open message viewer
        def on_message_click(event):
            try:
                logger.info(f"Message indicator clicked for node {node_id}")
                # Get most recent unread message for this node
                if node_id in self.unread_messages and len(self.unread_messages[node_id]) > 0:
                    # Open most recent unread message
                    message_data = self.unread_messages[node_id][0]  # Already sorted newest first
                    message_id = message_data.get('message_id')
                    logger.info(f"Opening message {message_id} from indicator click")
                    if message_id:
                        self._view_message_by_id(message_id)
                else:
                    logger.warning(f"No unread messages for {node_id} when clicking indicator")
            except Exception as e:
                logger.error(f"Error opening message from indicator: {e}", exc_info=True)
            return "break"  # Stop event propagation
        
        msg_indicator.bind('<Button-1>', on_message_click)
        
        last_message_time = node_data.get('Last Message Time')
        if last_message_time:
            time_since_message = current_time - last_message_time
            if time_since_message <= 900:  # 15 minutes = 900 seconds
                msg_indicator.pack(side="left", anchor="e")
        
        # Status (colored, bold - 14pt)
        status_label = tk.Label(right_header, text=status,
                               bg=bg_color, fg=status_colors.get(status, self.colors['fg_normal']),
                               font=self.font_card_header)
        status_label.pack(anchor="e")
        
        # Last Heard / Motion Detected row - fixed height area for all cards (uniform height)
        # Increased to 18px to accommodate both left text and right short name
        # Show "Last heard:" for offline nodes OR "Motion detected" for online nodes with recent motion
        # Short name appears on right side of this line
        lastheard_frame = tk.Frame(card_frame, bg=bg_color, height=18)
        lastheard_frame.pack(fill="x", padx=6, pady=1)
        lastheard_frame.pack_propagate(False)
        
        # short_name was already looked up above with long_name from cache
        shortname_label = None  # Short name display removed but variable needed for widget dict
        
        heard_label = None
        motion_label = None
        message_label = None
        last_motion = node_data.get('Last Motion')
        
        # Check for unread messages (highest priority for line 2)
        unread_msgs = self.unread_messages.get(node_id, [])
        has_unread = len(unread_msgs) > 0
        
        if has_unread:
            # Show most recent unread message
            newest_msg = unread_msgs[0]  # Already sorted newest first
            msg_text = newest_msg.get('text', '')
            msg_from = newest_msg.get('from_name', 'Unknown')
            
            # Shorten sender name if too long (use first word or first 15 chars)
            if len(msg_from) > 15:
                msg_from = msg_from.split()[0] if ' ' in msg_from else msg_from[:15]
            
            # Calculate available space: 368px card width - 12px padding - icon space
            # ~50 chars fits comfortably
            max_preview = 50
            preview = msg_text[:max_preview] + '...' if len(msg_text) > max_preview else msg_text
            
            # Show count if multiple unread
            count_badge = f" [{len(unread_msgs)}]" if len(unread_msgs) > 1 else ""
            
            # Format: [MSG] From: preview text... [count]
            display_text = f"[MSG] {msg_from}: {preview}{count_badge}"
            
            message_label = tk.Label(lastheard_frame, text=display_text,
                                   bg=bg_color, fg=self.colors['fg_normal'],
                                   font=self.font_card_line2, cursor="hand2", anchor="w")
            message_label.pack(anchor="w", side="left", fill="x")
            
            # Make clickable to open message viewer
            # Note: This label will be excluded from bind_click_recursive below
            def open_viewer(event):
                self._open_message_viewer(node_id)
                return "break"  # Stop event propagation to prevent card menu
            
            message_label.bind('<Button-1>', open_viewer)
            message_label._is_message_label = True  # Mark for exclusion from card click binding
            
        # Line 2 reserved for temporary status messages only (motion, last heard, messages)
        # Short name removed from here (was on right side)
        # Messages take highest priority, then motion, then last heard
        elif status == "Offline" and last_heard:
            # For offline nodes, show static last heard timestamp
            heard_dt = datetime.fromtimestamp(last_heard)
            heard_text = f"Last: {heard_dt.strftime('%m-%d %H:%M')}"
            # 12pt font for line 2
            heard_label = tk.Label(lastheard_frame, text=heard_text,
                                  bg=bg_color, fg=self.colors['fg_bad'],
                                  font=self.font_card_line2)
            heard_label.pack(anchor="w", side="left")
        elif status == "Online" and last_motion:
            # For online nodes with recent motion, show motion detected
            motion_display_duration = self.config_manager.get('dashboard.motion_display_seconds', 900)  # Default 15 minutes
            time_since_motion = current_time - last_motion
            
            if time_since_motion <= motion_display_duration:
                # Motion indicator - using text instead of emoji for Linux compatibility
                logger.info(f"Node {node_id}: SHOWING 'Motion detected' - time_since={time_since_motion:.1f}s <= threshold={motion_display_duration}s")
                motion_text = "Motion detected"
                # 12pt font for line 2
                motion_label = tk.Label(lastheard_frame, text=motion_text,
                                       bg=bg_color, fg=self.colors['fg_good'],
                                       font=self.font_card_line2)
                motion_label.pack(anchor="w", side="left")
            else:
                # Motion too old - don't show indicator
                logger.info(f"Node {node_id}: HIDING motion (too old) - time_since={time_since_motion:.1f}s > threshold={motion_display_duration}s")
        
        # Determine if data is stale (use grey color for stale telemetry)
        # Data is stale if we haven't received telemetry recently, even if node is online
        is_stale = telemetry_stale
        stale_color = self.colors['fg_secondary']  # Grey for stale data
        
        # =============================================================================
        # ROW 1: BATTERY INFORMATION (3-column layout)
        # Format: "ICP:12.9V (80%)   +2.5mA ↑   Node:4.2V (100%)"
        # Column 1 (left): ICP voltage + %
        # Column 2 (center): Current with charge indicator
        # Column 3 (right): Node battery voltage + %
        # =============================================================================
        metrics1_frame = tk.Frame(card_frame, bg=bg_color)
        metrics1_frame.pack(fill="x", padx=6, pady=1)
        
        # Create three columns for row 1 - matching row 2/3 widths
        row1_col1_frame = tk.Frame(metrics1_frame, bg=bg_color, width=100, height=18)
        row1_col1_frame.pack(side="left")
        row1_col1_frame.pack_propagate(False)
        
        row1_col2_frame = tk.Frame(metrics1_frame, bg=bg_color, width=105, height=18)
        row1_col2_frame.pack(side="left", padx=(6, 0))
        row1_col2_frame.pack_propagate(False)
        
        row1_col3_frame = tk.Frame(metrics1_frame, bg=bg_color, width=100, height=18)
        row1_col3_frame.pack(side="left", padx=(6, 0))
        row1_col3_frame.pack_propagate(False)
        
        # Column 1: ICP battery percentage only (left-aligned)
        ch3_voltage = node_data.get('Ch3 Voltage')
        ext_batt_label = None
        if ch3_voltage is not None:
            battery_pct = self.data_collector.voltage_to_percentage(ch3_voltage) if self.data_collector else None
            if battery_pct is not None:
                # Color coding for percentage
                if battery_pct > 50:
                    pct_color = self.colors['fg_good']
                elif battery_pct >= 25:
                    pct_color = self.colors['fg_warning']
                else:
                    pct_color = self.colors['fg_bad']
                display_pct_color = stale_color if is_stale else pct_color
                
                # Create container for ICP battery display
                ext_container = tk.Frame(row1_col1_frame, bg=bg_color)
                ext_container.pack(anchor="w")
                
                # "ICP Batt:" label (8pt small)
                tk.Label(ext_container, text="ICP Batt:", bg=bg_color,
                        fg=self.colors['fg_secondary'], font=self.font_card_label).pack(side="left")
                
                # Percentage value (11pt bold)
                tk.Label(ext_container, text=f"{battery_pct}%", bg=bg_color,
                        fg=display_pct_color, font=self.font_card_value).pack(side="left")
                
                ext_batt_label = ext_container
        
        # Column 2: Ch3 Current with charge/discharge indicator (centered)
        ch3_current = node_data.get('Ch3 Current')
        current_label = None
        if ch3_current is not None:
            # Convert mA and determine charge state
            if ch3_current > 0:
                current_text = f"+{ch3_current:.0f}mA"
                arrow = "↑"  # Charging
                current_color = self.colors['fg_good']
            elif ch3_current < 0:
                current_text = f"{ch3_current:.0f}mA"
                arrow = "↓"  # Discharging
                current_color = self.colors['fg_warning']
            else:
                current_text = f"{ch3_current:.0f}mA"
                arrow = ""
                current_color = self.colors['fg_normal']
            
            display_current_color = stale_color if is_stale else current_color
            
            # Create container for current display (centered)
            current_container = tk.Frame(row1_col2_frame, bg=bg_color)
            current_container.pack(fill="x", expand=True)
            
            # Inner container for centering
            current_inner = tk.Frame(current_container, bg=bg_color)
            current_inner.pack(anchor="center")
            
            # Current value (11pt bold)
            tk.Label(current_inner, text=current_text, bg=bg_color,
                    fg=display_current_color, font=self.font_card_value).pack(side="left")
            
            # Arrow indicator (11pt bold)
            if arrow:
                tk.Label(current_inner, text=f" {arrow}", bg=bg_color,
                        fg=display_current_color, font=self.font_card_value).pack(side="left")
            
            current_label = current_container
        
        # Column 3: Node battery percentage only (right-aligned)
        int_voltage = node_data.get('Internal Battery Voltage')
        battery_level = node_data.get('Battery Level')
        int_batt_label = None
        if int_voltage is not None and battery_level is not None:
            # Color coding for percentage
            if battery_level > 50:
                pct_color = self.colors['fg_good']
            elif battery_level >= 25:
                pct_color = self.colors['fg_warning']
            else:
                pct_color = self.colors['fg_bad']
            display_pct_color = stale_color if is_stale else pct_color
            
            # Create container for Node battery display
            int_container = tk.Frame(row1_col3_frame, bg=bg_color)
            int_container.pack(fill="x", expand=True)
            
            # Pack right-to-left for right alignment
            # Percentage value (11pt bold)
            tk.Label(int_container, text=f"{battery_level:.0f}%", bg=bg_color,
                    fg=display_pct_color, font=self.font_card_value).pack(side="right")
            
            # "Node Batt:" label (8pt small)
            tk.Label(int_container, text="Node Batt:", bg=bg_color,
                    fg=self.colors['fg_secondary'], font=self.font_card_label).pack(side="right")
            
            int_batt_label = int_container
        
        # Store labels for row 1
        battery_label = ext_batt_label  # For backward compat with flash code
        temp_label = None  # Temperature moved to row 3
        int_battery_label = int_batt_label  # New widget for internal battery
        
        # Metrics row 2 - SNR, Channel Utilization, Humidity
        metrics2_frame = tk.Frame(card_frame, bg=bg_color)
        metrics2_frame.pack(fill="x", padx=6, pady=1)
        
        # Create three columns for row 2 - uniform 3-column layout
        # Column widths: col1=100px, col2=105px, col3=100px (total ~305px + padding = ~323px)
        # Height 18px to match 8pt/11pt font sizes
        row2_col1_frame = tk.Frame(metrics2_frame, bg=bg_color, width=100, height=18)
        row2_col1_frame.pack(side="left")
        row2_col1_frame.pack_propagate(False)
        
        row2_col2_frame = tk.Frame(metrics2_frame, bg=bg_color, width=105, height=18)
        row2_col2_frame.pack(side="left", padx=(6, 0))
        row2_col2_frame.pack_propagate(False)
        
        row2_col3_frame = tk.Frame(metrics2_frame, bg=bg_color, width=100, height=18)
        row2_col3_frame.pack(side="left", padx=(6, 0))
        row2_col3_frame.pack_propagate(False)
        
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
                                 fg=self.colors['fg_secondary'], font=self.font_card_label)
            icon_label.pack(side="left", padx=0)  # No padding
            
            # Get bar colors based on SNR level
            # Use pipe characters with different colors - all same width and baseline
            bar_chars = "||||"  # Four identical pipes/bars
            bar_colors = self.get_signal_bar_colors(snr)
            
            # Debug: print what we're doing
            logger.debug(f"SNR {snr}: bar_colors = {bar_colors}")
            
            # Change SNR bars to 10pt to match other row 2 text
            bar_font = tkfont.Font(family="Consolas" if sys.platform.startswith("win") else "Courier New", 
                                  size=10)  # Match other row 2 text
            
            # Create each bar with its own color - NO spacing between bars
            # Labels packed side-by-side naturally share baseline
            for i, (char, color) in enumerate(zip(bar_chars, bar_colors)):
                bar_label = tk.Label(snr_container, text=char, bg=bg_color,
                                   fg=color, font=bar_font, padx=0, pady=0)
                bar_label.pack(side="left", padx=0, pady=0)
            
            snr_label = snr_container  # Store container reference
        
        # Channel Utilization in second column
        channel_util = node_data.get('Channel Utilization')
        util_label = None
        if channel_util is not None:
            util_color = self.colors['fg_bad'] if channel_util > 80 else self.colors['fg_warning'] if channel_util > 50 else self.colors['fg_good']
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else util_color
            
            # Create container for mixed font display (centered)
            util_container = tk.Frame(row2_col2_frame, bg=bg_color)
            util_container.pack(fill="x", expand=True)
            
            # Create inner container for actual centering of content
            util_inner = tk.Frame(util_container, bg=bg_color)
            util_inner.pack(anchor="center")
            
            # "Ch:" label (8pt small, light grey)
            ch_label = tk.Label(util_inner, text="Ch:",
                               bg=bg_color, fg=self.colors['fg_secondary'],
                               font=self.font_card_label, padx=0, pady=0)
            ch_label.pack(side="left", padx=0)
            
            # Value (11pt bold)
            ch_value = tk.Label(util_inner, text=f"{channel_util:.1f}",
                               bg=bg_color, fg=display_color,
                               font=self.font_card_value, padx=0, pady=0)
            ch_value.pack(side="left", padx=0)
            
            # "%" unit (8pt small, light grey)
            ch_unit = tk.Label(util_inner, text="%",
                              bg=bg_color, fg=self.colors['fg_secondary'],
                              font=self.font_card_label, padx=0, pady=0)
            ch_unit.pack(side="left", padx=0)
            
            util_label = util_container
        else:
            logger.debug(f"Card creation for {node_id}: No channel util data (Channel Utilization={node_data.get('Channel Utilization')})")
        
        # Air Utilization (TX) in third column
        air_util = node_data.get('Air Utilization (TX)')
        air_util_label = None
        if air_util is not None:
            # Color coding: Green for low, Yellow for moderate, Red for high
            if air_util > 80:
                air_color = self.colors['fg_bad']
            elif air_util > 50:
                air_color = self.colors['fg_warning']
            else:
                air_color = self.colors['fg_good']
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else air_color
            
            # Create container for mixed font display (right-aligned)
            air_container = tk.Frame(row2_col3_frame, bg=bg_color)
            air_container.pack(fill="x", expand=True)
            
            # Pack labels right-to-left for right alignment
            # "%" unit (8pt small, light grey)
            air_unit = tk.Label(air_container, text="%",
                               bg=bg_color, fg=self.colors['fg_secondary'],
                               font=self.font_card_label, padx=0, pady=0)
            air_unit.pack(side="right", padx=0)
            
            # Value (11pt bold)
            air_value = tk.Label(air_container, text=f"{air_util:.1f}",
                                bg=bg_color, fg=display_color,
                                font=self.font_card_value, padx=0, pady=0)
            air_value.pack(side="right", padx=0)
            
            # "Air:" label (8pt small, light grey)
            air_label = tk.Label(air_container, text="Air:",
                                bg=bg_color, fg=self.colors['fg_secondary'],
                                font=self.font_card_label, padx=0, pady=0)
            air_label.pack(side="right", padx=0)
            
            air_util_label = air_container
        
        # =============================================================================
        # ROW 3: ENVIRONMENTAL CONDITIONS (Temperature, Humidity, Pressure)
        # Format: "72°F, 54% hum, 1013.2 hPa"
        # =============================================================================
        metrics3_frame = tk.Frame(card_frame, bg=bg_color)
        metrics3_frame.pack(fill="x", padx=6, pady=1)
        
        # Create three columns for row 3 - uniform 3-column layout
        # Column widths: col1=100px, col2=105px, col3=100px (total ~305px + padding = ~323px)
        row3_col1_frame = tk.Frame(metrics3_frame, bg=bg_color, width=100, height=18)
        row3_col1_frame.pack(side="left")
        row3_col1_frame.pack_propagate(False)
        
        row3_col2_frame = tk.Frame(metrics3_frame, bg=bg_color, width=105, height=18)
        row3_col2_frame.pack(side="left", padx=(6, 0))
        row3_col2_frame.pack_propagate(False)
        
        row3_col3_frame = tk.Frame(metrics3_frame, bg=bg_color, width=100, height=18)
        row3_col3_frame.pack(side="left", padx=(6, 0))
        row3_col3_frame.pack_propagate(False)
        
        # Temperature in column 1
        temp = node_data.get('Temperature')
        temp_label = None
        if temp is not None:
            # Convert temperature to configured unit
            temp_value, temp_unit_str, (red_threshold, yellow_threshold) = self.convert_temperature(temp)
            
            # Match table view: Red if >red_threshold or <0°C, Yellow if yellow_threshold-red_threshold, Green if 0-yellow_threshold
            if temp > red_threshold or temp < 0:
                temp_color = self.colors['fg_bad']  # Red for extreme temps
            elif temp >= yellow_threshold:
                temp_color = self.colors['fg_warning']  # Orange for warm temps
            else:
                temp_color = self.colors['fg_good']  # Green for normal temps
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else temp_color
            
            # Create container for temperature display
            temp_container = tk.Frame(row3_col1_frame, bg=bg_color)
            temp_container.pack(anchor="w")
            
            # Temperature value (11pt bold)
            temp_value_label = tk.Label(temp_container, text=f"{temp_value:.0f}",
                                       bg=bg_color, fg=display_color,
                                       font=self.font_card_value, padx=0, pady=0)
            temp_value_label.pack(side="left", padx=0)
            
            # Unit (8pt small, light grey)
            temp_unit_label = tk.Label(temp_container, text=temp_unit_str,
                                      bg=bg_color, fg=self.colors['fg_secondary'],
                                      font=self.font_card_label, padx=0, pady=0)
            temp_unit_label.pack(side="left", padx=0)
            
            temp_label = temp_container  # Store container reference
        
        # Humidity in column 2
        humidity = node_data.get('Humidity')
        humidity_label = None
        if humidity is not None:
            # Color coding: Green for normal (20-60%), Yellow for dry/humid (<20% or >60%)
            if humidity < 20 or humidity > 60:
                humidity_color = self.colors['fg_warning']  # Yellow for dry or humid
            else:
                humidity_color = self.colors['fg_good']  # Green for normal (20-60%)
            # Use grey if stale, otherwise use color-coded value
            display_color = stale_color if is_stale else humidity_color
            
            # Create container for humidity display
            humidity_container = tk.Frame(row3_col2_frame, bg=bg_color)
            humidity_container.pack(anchor="center")
            
            # "Humidity:" label (8pt small, grey)
            hum_label = tk.Label(humidity_container, text="Humidity:",
                                bg=bg_color, fg=self.colors['fg_secondary'],
                                font=self.font_card_label, padx=0, pady=0)
            hum_label.pack(side="left", padx=0)
            
            # Humidity value (11pt bold for number)
            hum_num = tk.Label(humidity_container, text=f"{humidity:.0f}%",
                              bg=bg_color, fg=display_color,
                              font=self.font_card_value, padx=0, pady=0)
            hum_num.pack(side="left", padx=0)
            
            humidity_label = humidity_container
        
        # Pressure in column 3
        pressure = node_data.get('Pressure')
        pressure_label = None
        if pressure is not None:
            # Create container for pressure display (right-aligned)
            pressure_container = tk.Frame(row3_col3_frame, bg=bg_color)
            pressure_container.pack(fill="x", expand=True)
            
            # Pack right-to-left for right alignment
            # "hPa" unit (8pt small, grey)
            press_unit = tk.Label(pressure_container, text=" hPa",
                                 bg=bg_color, fg=self.colors['fg_secondary'],
                                 font=self.font_card_label, padx=0, pady=0)
            press_unit.pack(side="right", padx=0)
            
            # Pressure value (11pt bold, grey - no color thresholds)
            press_value = tk.Label(pressure_container, text=f"{pressure:.1f}",
                                  bg=bg_color, fg=stale_color if is_stale else self.colors['fg_secondary'],
                                  font=self.font_card_value, padx=0, pady=0)
            press_value.pack(side="right", padx=0)
            
            pressure_label = pressure_container
        
        # Humidity moved from row 2 to row 3
        humidity_label = None
        
        # Click handler for showing context menu (left-click only)
        def on_card_click(event):
            show_card_menu(event)
        
        # Bind left-click to card frame and all children recursively
        # Skip message labels (they have their own click handler)
        def bind_click_recursive(widget):
            # Skip widgets marked as message labels
            if not hasattr(widget, '_is_message_label'):
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
            'row2_col1_frame': row2_col1_frame,
            'row2_col2_frame': row2_col2_frame,
            'row2_col3_frame': row2_col3_frame,
            'row3_col1_frame': row3_col1_frame,
            'row3_col2_frame': row3_col2_frame,
            'row3_col3_frame': row3_col3_frame,
            'name_label': name_label,
            'shortname_label': shortname_label,
            'status_label': status_label,
            'menu_button': menu_button,
            'msg_indicator': msg_indicator,
            'message_label': message_label if unread_msgs else None,
            'heard_label': heard_label,
            'motion_label': motion_label,
            'battery_label': battery_label,
            'int_battery_label': int_batt_label,
            'current_label': current_label,
            'temp_label': temp_label,
            'snr_label': snr_label,
            'util_label': util_label,
            'air_util_label': air_util_label,
            'humidity_label': humidity_label,
            'pressure_label': pressure_label,
        }
        
        # Fix for initial card creation: explicitly set backgrounds on all labels
        # This prevents tkinter's default blue/system background from showing
        # through before the first update. Without this, labels briefly show
        # the system default background (light blue on Windows) even though
        # bg= was set in the constructor.
        if not is_changed:
            # Explicitly configure backgrounds on all labels and their children
            for key in ['name_label', 'shortname_label', 'status_label', 'menu_button',
                       'heard_label', 'motion_label']:
                widget = self.card_widgets[node_id].get(key)
                if widget:
                    widget.config(bg=bg_color)
            
            # Handle container labels (battery, current, temp, snr, util, humidity)
            # which have child labels that also need backgrounds set
            for key in ['battery_label', 'current_label', 'temp_label', 'snr_label',
                       'util_label', 'humidity_label']:
                widget = self.card_widgets[node_id].get(key)
                if widget:
                    widget.config(bg=bg_color)
                    # Update all child labels within the container
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label):
                            child.config(bg=bg_color)
        
        # If this card was created with blue background (is_changed), schedule restoration
        if is_changed:
            # Cancel any existing timer for this node
            if node_id in self.flash_timers:
                self.after_cancel(self.flash_timers[node_id])
            
            # Schedule restoration to normal background after 2 seconds
            def restore_normal():
                # Update the card's background directly instead of full redisplay
                if node_id in self.card_widgets:
                    card_info = self.card_widgets[node_id]
                    # Use local node color if this is the local node, otherwise normal bg
                    local_node_id = self.config_manager.get('meshtastic.local_node_id')
                    normal_bg = self.colors['bg_local_node'] if (node_id == local_node_id) else self.colors['bg_frame']
                    
                    # Update card frame background
                    card_info['frame'].config(bg=normal_bg)
                    
                    # Update all child frames
                    for key in ['header_frame', 'left_header', 'right_header', 
                               'lastheard_frame',
                               'metrics1_frame', 'metrics2_frame', 'metrics3_frame',
                               'row2_col1_frame', 'row2_col2_frame', 'row2_col3_frame',
                               'row3_col1_frame', 'row3_col2_frame', 'row3_col3_frame']:
                        if key in card_info and card_info[key]:
                            card_info[key].config(bg=normal_bg)
                    
                    # Update all labels
                    for key in ['name_label', 'shortname_label', 'status_label', 'heard_label',
                               'battery_label', 'int_battery_label', 'temp_label', 'util_label',
                               'motion_label', 'current_label', 'humidity_label', 'pressure_label',
                               'air_util_label']:
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
            
            # Schedule flash restoration after 2 seconds (2000ms)
            self.flash_timers[node_id] = self.after(2000, restore_normal)
    
    # =========================================================================
    # Registry-based Field Update Methods
    # =========================================================================
    
    def _update_simple_field(self, node_id: str, field_name: str, value: Any, is_stale: bool):
        """Update a simple field using registry metadata
        
        Args:
            node_id: Node ID for widget lookup
            field_name: Field name in registry (e.g., 'Temperature')
            value: New value to display
            is_stale: Whether data is stale (>16 min old)
        """
        if node_id not in self.card_widgets:
            return
        
        field_def = self.field_registry.get_field_definition(field_name)
        if not field_def or field_def['widget_type'] != 'simple':
            return
        
        widget_key = field_def['widget_key']
        container = self.card_widgets[node_id].get(widget_key)
        
        if not container or not container.winfo_exists():
            return
        
        # Format value
        formatted_text = self.field_registry.format_field(self, field_name, value)
        
        # Get color
        color = self.field_registry.get_field_color(self, field_name, value, is_stale)
        
        # Container is a Frame with child labels
        # For most fields, update the value label (which might be first or second child)
        # Temperature: children[0] is value, children[1] is unit
        # Humidity: children[0] is "Humidity:" label, children[1] is value
        # Pressure: children[0] is unit, children[1] is value
        children = container.winfo_children()
        if not children:
            return
        
        # Find the value label (the one that should be updated)
        # For pressure and humidity, it's the second child; for temperature it's the first
        if field_name in ['Pressure', 'Humidity']:
            # Value is second child (index 1)
            if len(children) > 1 and isinstance(children[1], tk.Label):
                children[1].config(text=formatted_text, fg=color)
        else:
            # Value is first child (index 0) - temperature and others
            if isinstance(children[0], tk.Label):
                children[0].config(text=formatted_text, fg=color)
    
    def update_snr_composite(self, node_id: str, node_data: Dict[str, Any], is_stale: bool):
        """Update SNR bar colors without recreating widget
        
        Args:
            node_id: Node ID for widget lookup
            node_data: Node data dict
            is_stale: Whether data is stale
        """
        if node_id not in self.card_widgets:
            return
        
        snr = node_data.get('SNR')
        if snr is None:
            return
        
        widget = self.card_widgets[node_id].get('snr_label')
        if not widget or not widget.winfo_exists():
            return
        
        # Get bar colors based on SNR value
        bar_colors = self.get_signal_bar_colors(snr)
        
        # Override with stale color if needed
        if is_stale:
            bar_colors = [self.colors['fg_secondary']] * 4
        
        # Update child label colors (skip first child which is "SNR: " label)
        children = widget.winfo_children()
        if len(children) >= 5:  # icon + 4 bars
            for i, color in enumerate(bar_colors):
                children[i + 1].config(fg=color)  # +1 to skip "SNR: " label
    
    def update_external_battery_composite(self, node_id: str, node_data: Dict[str, Any], is_stale: bool):
        """Update external battery display (composite widget)
        
        Args:
            node_id: Node ID for widget lookup
            node_data: Node data dict
            is_stale: Whether data is stale
        """
        if node_id not in self.card_widgets:
            return
        
        container = self.card_widgets[node_id].get('battery_label')
        if not container or not container.winfo_exists():
            return
        
        ch3_voltage = node_data.get('Ch3 Voltage')
        battery_level = node_data.get('Battery Level')
        ch3_current = node_data.get('Ch3 Current')
        
        if ch3_voltage is None:
            return
        
        # External battery has complex nested structure with 8 child labels
        # For now, skip updating to avoid complexity - battery updates less frequently
        # TODO: Implement proper external battery update if needed
        pass
    
    def update_internal_battery_composite(self, node_id: str, node_data: Dict[str, Any], is_stale: bool):
        """Update internal battery display (composite widget)
        
        Args:
            node_id: Node ID for widget lookup
            node_data: Node data dict
            is_stale: Whether data is stale
        """
        if node_id not in self.card_widgets:
            return
        
        container = self.card_widgets[node_id].get('int_battery_label')
        if not container or not container.winfo_exists():
            return
        
        int_voltage = node_data.get('Internal Battery Voltage')
        battery_level = node_data.get('Battery Level')
        
        if int_voltage is None or battery_level is None:
            return
        
        # Color coding for percentage
        if battery_level > 50:
            pct_color = self.colors['fg_good']
        elif battery_level >= 25:
            pct_color = self.colors['fg_warning']
        else:
            pct_color = self.colors['fg_bad']
        display_pct_color = self.colors['fg_secondary'] if is_stale else pct_color
        
        # Update children labels (label + voltage + percentage)
        children = container.winfo_children()
        if len(children) >= 3:
            # Children[0] = "Node: " (stays grey)
            # Children[1] = voltage value
            # Children[2] = percentage (color-coded)
            children[1].config(text=f"{int_voltage:.1f}V")
            children[2].config(text=f" ({battery_level:.0f}%)", fg=display_pct_color)
    
    def update_channel_util_composite(self, node_id: str, node_data: Dict[str, Any], is_stale: bool):
        """Update channel utilization display (3-part composite: Ch: value %)
        
        Args:
            node_id: Node ID for widget lookup
            node_data: Node data dict
            is_stale: Whether data is stale
        """
        if node_id not in self.card_widgets:
            return
        
        widget = self.card_widgets[node_id].get('util_label')
        if not widget or not widget.winfo_exists():
            return
        
        channel_util = node_data.get('Channel Utilization')
        if channel_util is None:
            return
        
        # Color based on utilization thresholds
        if channel_util > 25:
            util_color = self.colors['fg_bad']
        elif channel_util > 10:
            util_color = self.colors['fg_warning']
        else:
            util_color = self.colors['fg_good']
        
        display_color = self.colors['fg_secondary'] if is_stale else util_color
        
        # Update children (label "Ch:" + value + unit "%")
        children = widget.winfo_children()
        if len(children) >= 3:
            # Children[0] = "Ch:", Children[1] = value, Children[2] = "%"
            children[0].config(fg=self.colors['fg_secondary'])  # Label always grey
            children[1].config(text=f"{channel_util:.1f}", fg=display_color)  # Value colored
            children[2].config(fg=self.colors['fg_secondary'])  # Unit always grey
    
    def update_air_util_composite(self, node_id: str, node_data: Dict[str, Any], is_stale: bool):
        """Update air utilization display (3-part composite: Air: value %)
        
        Args:
            node_id: Node ID for widget lookup
            node_data: Node data dict
            is_stale: Whether data is stale
        """
        if node_id not in self.card_widgets:
            return
        
        widget = self.card_widgets[node_id].get('air_util_label')
        if not widget or not widget.winfo_exists():
            return
        
        air_util = node_data.get('Air Utilization (TX)')
        if air_util is None:
            return
        
        # Color based on utilization thresholds
        if air_util > 10:
            util_color = self.colors['fg_bad']
        elif air_util > 5:
            util_color = self.colors['fg_warning']
        else:
            util_color = self.colors['fg_good']
        
        display_color = self.colors['fg_secondary'] if is_stale else util_color
        
        # Update children (label "Air:" + value + unit "%")
        children = widget.winfo_children()
        if len(children) >= 3:
            # Children[0] = "Air:", Children[1] = value, Children[2] = "%"
            children[0].config(fg=self.colors['fg_secondary'])  # Label always grey
            children[1].config(text=f"{air_util:.1f}", fg=display_color)  # Value colored
            children[2].config(fg=self.colors['fg_secondary'])  # Unit always grey
    
    # =========================================================================
    # Targeted Container Update Methods
    # These methods surgically update individual containers without rebuilding
    # the entire card. Each method clears the container's children and recreates
    # the content based on current state. This is more efficient than force_refresh().
    # =========================================================================
    
    def _update_messages_button(self):
        """Update Messages button text to show unread count"""
        if not hasattr(self, 'messages_btn'):
            return
        
        # Count total unread messages across all nodes
        total_unread = sum(len(msgs) for msgs in self.unread_messages.values())
        
        # Update button text and color
        if total_unread > 0:
            self.messages_btn.config(text=f"Messages ({total_unread})", 
                                    bg=self.colors['fg_warning'])  # Orange when unread
        else:
            self.messages_btn.config(text="Messages", 
                                    bg=self.colors['button_bg'])  # Normal grey
    
    def _update_card_line2(self, node_id: str):
        """Surgically update line 2 (lastheard_frame) content
        
        Shows unread message, motion detected, or last heard based on priority.
        Destroys existing children and recreates appropriate label(s).
        
        Args:
            node_id: Node ID to update
        """
        logger.info(f"_update_card_line2 called for {node_id}")
        
        if node_id not in self.card_widgets:
            logger.warning(f"_update_card_line2: {node_id} not in card_widgets")
            return
        
        card_info = self.card_widgets[node_id]
        lastheard_frame = card_info.get('lastheard_frame')
        
        if not lastheard_frame or not lastheard_frame.winfo_exists():
            logger.warning(f"_update_card_line2: lastheard_frame missing or destroyed for {node_id}")
            return
        
        # Calculate background color based on whether this is local node
        local_node_id = self._get_local_node_id()
        normal_bg = self.colors['bg_local_node'] if (node_id == local_node_id) else self.colors['bg_frame']
        
        # Get current background color (preserves flash state)
        bg_color = lastheard_frame.cget('bg')
        
        # Clear existing children
        for child in lastheard_frame.winfo_children():
            child.destroy()
        
        # Get current node data
        nodes_data = self.data_collector.get_nodes_data()
        node_data = nodes_data.get(node_id, {})
        
        # Determine what to show (priority order)
        unread_msgs = self.unread_messages.get(node_id, [])
        has_unread = len(unread_msgs) > 0
        
        logger.info(f"_update_card_line2: {node_id} has {len(unread_msgs)} unread messages")
        
        if has_unread:
            # Show most recent unread message
            newest_msg = unread_msgs[0]  # Already sorted newest first
            msg_text = newest_msg.get('text', '')
            msg_from = newest_msg.get('from_name', 'Unknown')
            
            # Shorten sender name if too long
            if len(msg_from) > 15:
                msg_from = msg_from.split()[0] if ' ' in msg_from else msg_from[:15]
            
            # Preview text (50 chars)
            max_preview = 50
            preview = msg_text[:max_preview] + '...' if len(msg_text) > max_preview else msg_text
            
            # Show count if multiple unread
            count_badge = f" [{len(unread_msgs)}]" if len(unread_msgs) > 1 else ""
            
            # Format: [MSG] From: preview text... [count]
            display_text = f"[MSG] {msg_from}: {preview}{count_badge}"
            
            message_label = tk.Label(lastheard_frame, text=display_text,
                                   bg=bg_color, fg=self.colors['fg_normal'],
                                   font=self.font_card_line2, cursor="hand2", anchor="w")
            message_label.pack(anchor="w", side="left", fill="x")
            
            # Make clickable to open message viewer
            def open_viewer(event):
                self._open_message_viewer(node_id)
                return "break"  # Stop event propagation
            
            message_label.bind('<Button-1>', open_viewer)
            message_label._is_message_label = True  # Exclude from card click binding
            
            # Update widget reference
            card_info['message_label'] = message_label
            
        else:
            # No unread messages - check motion or last heard
            status = node_data.get('Status', 'Unknown')
            last_heard = node_data.get('Last Heard')
            last_motion = node_data.get('Last Motion')
            current_time = time.time()
            
            if status == "Offline" and last_heard:
                # Show static last heard timestamp
                heard_dt = datetime.fromtimestamp(last_heard)
                heard_text = f"Last: {heard_dt.strftime('%m-%d %H:%M')}"
                heard_label = tk.Label(lastheard_frame, text=heard_text,
                                      bg=bg_color, fg=self.colors['fg_bad'],
                                      font=self.font_card_line2)
                heard_label.pack(anchor="w", side="left")
                card_info['heard_label'] = heard_label
                
            elif status == "Online" and last_motion:
                # Show motion if recent enough
                motion_display_duration = self.config_manager.get('dashboard.motion_display_seconds', 900)
                time_since_motion = current_time - last_motion
                
                if time_since_motion <= motion_display_duration:
                    motion_text = "Motion detected"
                    motion_label = tk.Label(lastheard_frame, text=motion_text,
                                          bg=bg_color, fg=self.colors['fg_warning'],
                                          font=self.font_card_line2)
                    motion_label.pack(anchor="w", side="left")
                    card_info['motion_label'] = motion_label
    
    def update_node_card(self, node_id: str, node_data: Dict[str, Any], current_time: float, is_changed: bool = False):
        """Update existing card without recreating it (prevents flickering)
        
        Updates card content for new 3-row layout:
        - Row 1: External battery (Ch3 Voltage, %, Current) + Internal battery (Voltage, %)
        - Row 2: SNR, Air Util, Ch Util
        - Row 3: Temperature, Humidity, Pressure
        
        TODO: REFACTOR THIS FUNCTION - See CARD_REGISTRY_DESIGN.md
        This function is tightly coupled to card layout. After 3-row card redesign,
        it needs complete rewrite using field registry pattern for maintainability.
        Design doc: CARD_REGISTRY_DESIGN.md (WIP - don't merge to main docs yet)
        Tracking: AI_CONTEXT.md "WORK IN PROGRESS" section
        """
        if node_id not in self.card_widgets:
            return
            
        card_info = self.card_widgets[node_id]
        card_frame = card_info['frame']
        
        # Note: Data change flash has been removed - using border flash for messages only
        
        # Update node name if it changed (e.g., from "Unknown Node" to actual name)
        long_name = node_data.get('Node LongName', 'Unknown')
        short_name = node_data.get('Node ShortName', node_id[-4:])
        
        # If we have "Unknown" or "Unknown Node", try to get real name from cache
        if long_name in ('Unknown', 'Unknown Node') and self.data_collector:
            cached_info = self.data_collector.node_info_cache.get(node_id)
            if cached_info:
                cached_long, cached_short = cached_info
                if cached_long and cached_long not in ('Unknown', 'Unknown Node'):
                    logger.info(f"UPDATE {node_id}: Found '{cached_long}' in cache")
                    long_name = cached_long
                if cached_short and cached_short != 'Unknown':
                    short_name = cached_short
        
        display_name = long_name.replace("AG6WR-", "") if long_name.startswith("AG6WR-") else long_name
        card_info['name_label'].config(text=display_name)
        # Short name removed from card (reserved for status messages only)
        # if card_info.get('shortname_label'):
        #     card_info['shortname_label'].config(text=f"({short_name})")
        
        # Update status based on any packet received
        last_heard = node_data.get('Last Heard', 0)
        time_diff = current_time - last_heard if last_heard else float('inf')
        status = "Online" if time_diff <= 960 else "Offline"  # 16 minutes threshold
        
        # Determine if telemetry data is stale (no telemetry in 16 minutes)
        last_telemetry = node_data.get('Last Telemetry Time', 0)
        telemetry_diff = current_time - last_telemetry if last_telemetry else float('inf')
        telemetry_stale = telemetry_diff > 960
        is_stale = telemetry_stale
        stale_color = self.colors['fg_secondary']  # Grey for stale data
        
        status_colors = {
            'Online': self.colors['fg_good'],
            'Offline': self.colors['fg_bad']
        }
        
        card_info['status_label'].config(text=status, fg=status_colors.get(status, self.colors['fg_normal']))
        
        # Update message indicator
        last_message_time = node_data.get('Last Message Time')
        if last_message_time and 'msg_indicator' in card_info and card_info['msg_indicator']:
            time_since_message = current_time - last_message_time
            if time_since_message <= 900:  # 15 minutes
                card_info['msg_indicator'].pack(side="left", anchor="e")
            else:
                card_info['msg_indicator'].pack_forget()
        
        # Update Last Heard / Motion Detected
        last_motion = node_data.get('Last Motion')
        motion_display_duration = self.config_manager.get('dashboard.motion_display_seconds', 900)
        
        if status == "Offline" and last_heard:
            heard_dt = datetime.fromtimestamp(last_heard)
            heard_text = f"Last: {heard_dt.strftime('%m-%d %H:%M')}"
            
            if card_info['motion_label']:
                card_info['motion_label'].pack_forget()
            
            if card_info['heard_label']:
                card_info['heard_label'].config(text=heard_text, fg=self.colors['fg_bad'], bg=normal_bg)
                card_info['heard_label'].pack(anchor="w", side="left")
            else:
                heard_label = tk.Label(card_info['lastheard_frame'], text=heard_text,
                                      bg=normal_bg, fg=self.colors['fg_bad'],
                                      font=self.font_card_line2)
                heard_label.pack(anchor="w", side="left")
                card_info['heard_label'] = heard_label
        elif status == "Online" and last_motion and (current_time - last_motion) <= motion_display_duration:
            motion_text = "Motion detected"
            
            if card_info['heard_label']:
                card_info['heard_label'].pack_forget()
            
            if card_info['motion_label']:
                card_info['motion_label'].config(text=motion_text, fg=self.colors['fg_good'], bg=normal_bg)
                card_info['motion_label'].pack(anchor="w", side="left")
            else:
                motion_label = tk.Label(card_info['lastheard_frame'], text=motion_text,
                                       bg=normal_bg, fg=self.colors['fg_good'],
                                       font=self.font_card_line2)
                motion_label.pack(anchor="w", side="left")
                card_info['motion_label'] = motion_label
        else:
            if card_info['heard_label']:
                card_info['heard_label'].pack_forget()
            if card_info['motion_label']:
                card_info['motion_label'].pack_forget()
        
        # =============================================================================
        # FIELD UPDATES - Registry-driven approach
        # =============================================================================
        
        # Update simple fields using registry
        simple_fields = self.field_registry.get_all_simple_fields()
        for field_name in simple_fields:
            value = node_data.get(field_name)
            if value is not None:
                self._update_simple_field(node_id, field_name, value, is_stale)
        
        # Update composite fields using custom handlers
        self.update_snr_composite(node_id, node_data, is_stale)
        self.update_external_battery_composite(node_id, node_data, is_stale)
        self.update_internal_battery_composite(node_id, node_data, is_stale)
        self.update_channel_util_composite(node_id, node_data, is_stale)
        self.update_air_util_composite(node_id, node_data, is_stale)
    
    def show_node_detail(self, node_id: str):
        """Show detailed information window for a node"""
        # Get fresh data from data_collector instead of self.nodes
        nodes_data = self.data_collector.get_nodes_data()
        
        if node_id not in nodes_data:
            logger.warning(f"Cannot show detail for unknown node: {node_id}")
            return
        
        node_data = nodes_data[node_id]
        
        # Define callbacks that capture node_id properly (avoiding lambda closure issues on Linux)
        def open_logs():
            logger.info(f"open_logs callback triggered for {node_id}")
            self.open_logs_folder(node_id)
        
        def open_csv():
            logger.info(f"open_csv callback triggered for {node_id}")
            self.open_today_csv(node_id)
        
        def show_plot():
            logger.info(f"show_plot callback triggered for {node_id}")
            self.show_plot_for_node(node_id, detail_window.window)
        
        # Create detail window with callback functions
        detail_window = NodeDetailWindow(
            self, 
            node_id, 
            node_data,
            on_logs=open_logs,
            on_csv=open_csv,
            on_plot=show_plot,
            data_collector=self.data_collector
        )
    
    def _show_card_context_menu(self, event, node_id):
        """Show context menu for card right-click"""
        nodes_data = self.data_collector.get_nodes_data() if self.data_collector else {}
        node_data = nodes_data.get(node_id, {})
        node_name = node_data.get('Node LongName', node_id)
        
        # Create context menu
        menu = tk.Menu(self, tearoff=0,
                      bg=self.colors['bg_frame'],
                      fg=self.colors['fg_normal'],
                      activebackground=self.colors['bg_selected'],
                      activeforeground=self.colors['fg_normal'])
        
        # Add menu items
        menu.add_command(label=f"View Details", 
                        command=lambda: self.show_node_detail(node_id))
        menu.add_command(label=f"Show Logs", 
                        command=lambda: self.open_node_logs(node_id))
        menu.add_command(label=f"Open CSV", 
                        command=lambda: self.open_node_csv(node_id))
        menu.add_command(label=f"Plot Telemetry", 
                        command=lambda: self.show_plot_for_node(node_id))
        menu.add_separator()
        menu.add_command(label=f"Send Message To '{node_name}'...", 
                        command=lambda: self._send_message_to_node(node_id))
        menu.add_separator()
        menu.add_command(label=f"Forget Node '{node_name}'", 
                        command=lambda: self._forget_node_from_card(node_id),
                        foreground=self.colors['fg_bad'])  # Red text for destructive action
        
        # Show menu at mouse position
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def _forget_node_from_card(self, node_id):
        """Forget a node from card context menu"""
        import tkinter.messagebox as messagebox
        
        nodes_data = self.data_collector.get_nodes_data() if self.data_collector else {}
        node_data = nodes_data.get(node_id, {})
        node_name = node_data.get('Node LongName', node_id)
        
        # Confirmation dialog (same as detail window)
        response = messagebox.askyesno(
            "Forget Node",
            f"Forget node '{node_name}' ({node_id})?\n\n"
            "This will:\n"
            "• Remove all node data from the dashboard\n"
            "• Clear alerts for this node\n"
            "• Keep CSV logs (unless deleted manually)\n\n"
            "This cannot be undone. Continue?",
            icon='warning'
        )
        
        if response:
            # Ask about deleting logs
            delete_logs = messagebox.askyesno(
                "Delete Logs?",
                f"Also delete CSV log files for '{node_name}'?\n\n"
                "If you select No, logs will be preserved\n"
                "and can be accessed manually.",
                icon='question'
            )
            
            # Call data_collector to forget the node
            if self.data_collector:
                success = self.data_collector.forget_node(node_id, delete_logs)
                
                if success:
                    messagebox.showinfo("Node Forgotten", f"Node '{node_name}' has been removed.")
                    # Trigger a refresh to remove the card
                    self.refresh_display()
                else:
                    messagebox.showerror("Error", f"Failed to forget node '{node_name}'.")
            else:
                messagebox.showerror("Error", "Data collector not available.")
    
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
            return f"{voltage:.1f}V", color
        else:
            return "No voltage", self.colors['fg_secondary']
    
    def get_battery_percentage_display(self, node_data: dict):
        """Get battery percentage display with appropriate color coding
        
        Determines battery % from either:
        - Ch3 Voltage (external LiFePO4) converted via interpolation
        - Battery Level (internal Li+ cell) from deviceMetrics
        
        Returns: (text, color) tuple
        """
        # Try external battery first (Ch3 Voltage)
        ch3_voltage = node_data.get('Ch3 Voltage')
        if ch3_voltage is not None and self.data_collector:
            battery_pct = self.data_collector.voltage_to_percentage(ch3_voltage)
            if battery_pct is not None:
                # Color coding: 0-25% red, 25-50% yellow, >50% green
                if battery_pct > 50:
                    color = self.colors['fg_good']     # Green
                elif battery_pct >= 25:
                    color = self.colors['fg_warning']  # Yellow
                else:
                    color = self.colors['fg_bad']      # Red
                return f"Bat:{battery_pct}%", color
        
        # Fall back to internal battery percentage
        internal_battery = node_data.get('Battery Level')
        if internal_battery is not None:
            # Color coding: 0-25% red, 25-50% yellow, >50% green
            if internal_battery > 50:
                color = self.colors['fg_good']     # Green
            elif internal_battery >= 25:
                color = self.colors['fg_warning']  # Yellow
            else:
                color = self.colors['fg_bad']      # Red
            return f"Bat:{internal_battery}%", color
        
        # No battery data available
        return "no external battery sensor", self.colors['fg_secondary']
    
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
            # Switch TO cards
            self.view_mode = "cards"
            self.view_btn.config(text="Table")  # Button shows where you can go
            self.table_container.pack_forget()
            self.card_container.pack(fill="both", expand=True, padx=8, pady=8)
        else:
            # Switch TO table
            self.view_mode = "table"
            self.view_btn.config(text="Cards")  # Button shows where you can go
            self.card_container.pack_forget()
            self.table_container.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Force a refresh to update the display
        self.force_refresh()
    
    def open_messages(self):
        """Open the message list window"""
        from message_list_window import MessageListWindow
        MessageListWindow(self, self.message_manager, 
                         on_view_message=self._view_message_by_id,
                         on_send_message=self._send_message_to_node)
    
    def _view_message_by_id(self, message_id: str):
        """Open message viewer for a specific message ID
        
        Args:
            message_id: Message ID to view
        """
        message_data = self.message_manager.get_message_by_id(message_id)
        if not message_data:
            logger.warning(f"Message {message_id} not found")
            return
        
        # Determine node_id for updating UI after actions
        if message_data.get('direction') == 'received':
            node_id = message_data.get('from_node_id')
        else:
            # For sent messages, use first recipient or None
            to_ids = message_data.get('to_node_ids', [])
            node_id = to_ids[0] if to_ids else None
        
        def on_reply(reply_to_id: str, reply_to_name: str):
            """Callback when user clicks Reply in viewer"""
            self._send_message_to_node(reply_to_id)
        
        def on_delete(msg_id: str):
            """Callback when user clicks Delete in viewer"""
            try:
                self.message_manager.delete_message(msg_id)
                logger.info(f"Deleted message {msg_id}")
                
                # Remove from unread cache if present
                for nid in list(self.unread_messages.keys()):
                    self.unread_messages[nid] = [
                        msg for msg in self.unread_messages[nid]
                        if msg.get('message_id') != msg_id
                    ]
                
                # Update all cards that might show this message
                self._update_all_message_indicators()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        def on_close(msg_id: str, direction: str):
            """Callback when viewer closes - mark as read and send receipt"""
            if direction == 'received':
                try:
                    self.message_manager.mark_as_read(msg_id)
                    logger.info(f"Marked message {msg_id} as read")
                    
                    # Send read receipt if structured
                    if message_data.get('structured', True):
                        receipt_text = f"[RECEIPT:{msg_id}]"
                        sender_id = message_data.get('from_node_id')
                        if sender_id:
                            self.data_collector.connection_manager.send_message(sender_id, receipt_text)
                    
                    # Remove from unread cache
                    if node_id and node_id in self.unread_messages:
                        self.unread_messages[node_id] = [
                            msg for msg in self.unread_messages[node_id]
                            if msg.get('message_id') != msg_id
                        ]
                    
                    # Update card display
                    if node_id:
                        self._update_card_line2(node_id)
                    self._update_messages_button()  # Update button badge
                    
                except Exception as e:
                    logger.error(f"Error marking message as read: {e}")
        
        def on_mark_read(msg_id: str):
            """Callback when user clicks Mark as Read in viewer"""
            try:
                self.message_manager.mark_as_read(msg_id)
                logger.info(f"Marked message {msg_id} as read")
                
                # Send read receipt if structured
                if message_data.get('structured', True):
                    receipt_text = f"[RECEIPT:{msg_id}]"
                    sender_id = message_data.get('from_node_id')
                    if sender_id:
                        self.data_collector.connection_manager.send_message(sender_id, receipt_text)
                
                # Remove from unread cache
                if node_id and node_id in self.unread_messages:
                    self.unread_messages[node_id] = [
                        msg for msg in self.unread_messages[node_id]
                        if msg.get('message_id') != msg_id
                    ]
                
                # Update card display
                if node_id:
                    self._update_card_line2(node_id)
            except Exception as e:
                logger.error(f"Error marking message as read: {e}")
        
        def on_archive(msg_id: str):
            """Callback when user clicks Archive in viewer"""
            try:
                message = self.message_manager.get_message(msg_id)
                if message:
                    message['archived'] = True
                    self.message_manager.save_message(message)
                    logger.info(f"Archived message {msg_id}")
                    
                    # Remove from unread cache
                    if node_id and node_id in self.unread_messages:
                        self.unread_messages[node_id] = [
                            msg for msg in self.unread_messages[node_id]
                            if msg.get('message_id') != msg_id
                        ]
                    
                    # Update card display
                    if node_id:
                        self._update_card_line2(node_id)
            except Exception as e:
                logger.error(f"Error archiving message: {e}")
        
        # Open the viewer
        from message_viewer import MessageViewer
        MessageViewer(self, message_data, 
                     on_reply=on_reply,
                     on_delete=on_delete,
                     on_close=on_close,
                     on_mark_read=on_mark_read,
                     on_archive=on_archive)
    
    def _update_all_message_indicators(self):
        """Update message indicators on all cards"""
        for node_id in list(self.card_widgets.keys()):
            self._update_card_line2(node_id)
        self._update_messages_button()  # Update button badge
    
    def _open_message_viewer(self, node_id: str):
        """Open message viewer for the oldest unread message for a node
        
        Args:
            node_id: Node ID to view messages for
        """
        # Get unread messages for this node
        unread_msgs = self.unread_messages.get(node_id, [])
        if not unread_msgs:
            logger.warning(f"No unread messages for {node_id}")
            return
        
        # Show the oldest unread message (last in list since sorted newest first)
        message_data = unread_msgs[-1]
        
        def on_reply(reply_to_id: str, reply_to_name: str):
            """Callback when user clicks Reply in viewer"""
            self._send_message_to_node(reply_to_id)
        
        def on_delete(message_id: str):
            """Callback when user clicks Delete in viewer"""
            try:
                self.message_manager.delete_message(message_id)
                logger.info(f"Deleted message {message_id}")
                
                # Remove from unread cache
                if node_id in self.unread_messages:
                    self.unread_messages[node_id] = [
                        msg for msg in self.unread_messages[node_id]
                        if msg.get('message_id') != message_id
                    ]
                
                # Surgically update line 2 to remove message label
                self._update_card_line2(node_id)
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        def on_close(message_id: str, direction: str):
            """Callback when viewer closes - mark as read and send receipt"""
            if direction == 'received':
                try:
                    # Mark message as read
                    self.message_manager.mark_as_read(message_id)
                    logger.info(f"Marked message {message_id} as read")
                    
                    # Send read receipt back to sender
                    receipt_text = f"[RECEIPT:{message_id}]"
                    sender_id = message_data.get('from_node_id')
                    if sender_id:
                        success = self.data_collector.connection_manager.send_message(sender_id, receipt_text)
                        if success:
                            logger.info(f"Sent read receipt for {message_id} to {sender_id}")
                        else:
                            logger.warning(f"Failed to send read receipt for {message_id}")
                    
                    # Remove from unread cache
                    if node_id in self.unread_messages:
                        self.unread_messages[node_id] = [
                            msg for msg in self.unread_messages[node_id]
                            if msg.get('message_id') != message_id
                        ]
                    
                    # Surgically update line 2 to remove message label and stop flash
                    self._update_card_line2(node_id)
                    
                except Exception as e:
                    logger.error(f"Error marking message as read: {e}")
        
        def on_mark_read(message_id: str):
            """Callback when user clicks Mark as Read in viewer"""
            try:
                # Mark message as read
                self.message_manager.mark_as_read(message_id)
                logger.info(f"Marked message {message_id} as read")
                
                # Send read receipt if structured message
                if message_data.get('structured', True):
                    receipt_text = f"[RECEIPT:{message_id}]"
                    sender_id = message_data.get('from_node_id')
                    if sender_id:
                        success = self.data_collector.connection_manager.send_message(sender_id, receipt_text)
                        if success:
                            logger.info(f"Sent read receipt for {message_id} to {sender_id}")
                        else:
                            logger.warning(f"Failed to send read receipt for {message_id}")
                
                # Remove from unread cache
                if node_id in self.unread_messages:
                    self.unread_messages[node_id] = [
                        msg for msg in self.unread_messages[node_id]
                        if msg.get('message_id') != message_id
                    ]
                
                # Update card to remove message indicator and stop flash
                self._update_card_line2(node_id)
            except Exception as e:
                logger.error(f"Error marking message as read: {e}")
        
        def on_archive(message_id: str):
            """Callback when user clicks Archive in viewer"""
            try:
                # Set archived flag in message
                message = self.message_manager.get_message(message_id)
                if message:
                    message['archived'] = True
                    self.message_manager.save_message(message)
                    logger.info(f"Archived message {message_id}")
                    
                    # Remove from unread cache
                    if node_id in self.unread_messages:
                        self.unread_messages[node_id] = [
                            msg for msg in self.unread_messages[node_id]
                            if msg.get('message_id') != message_id
                        ]
                    
                    # Update card to remove message indicator
                    self._update_card_line2(node_id)
            except Exception as e:
                logger.error(f"Error archiving message: {e}")
        
        # Open the viewer
        MessageViewer(self, message_data, 
                     on_reply=on_reply,
                     on_delete=on_delete,
                     on_close=on_close,
                     on_mark_read=on_mark_read,
                     on_archive=on_archive)
    
    def _send_message_to_node(self, node_id: str):
        """Open dialog to send a message to a node"""
        nodes_data = self.data_collector.get_nodes_data() if self.data_collector else {}
        node_data = nodes_data.get(node_id, {})
        node_name = node_data.get('Node LongName', node_id)
        
        def send_callback(dest_id: str, message: str, send_bell: bool):
            """Callback when user confirms message send"""
            import time
            
            # Add bell character if requested
            if send_bell:
                message = '\a' + message
            
            # Generate message ID
            message_id = self._generate_message_id()
            
            # Format message with protocol: [MSG:id]text
            formatted_text = f"[MSG:{message_id}]{message}"
            
            # Send the message
            success = self.data_collector.connection_manager.send_message(dest_id, formatted_text)
            
            if success:
                logger.info(f"Message sent to {node_name} ({dest_id}): {repr(message)} [ID: {message_id}]")
                
                # Save to message_manager
                local_node_id = self._get_local_node_id()
                local_node_data = nodes_data.get(local_node_id, {})
                local_node_name = local_node_data.get('Node LongName', 'Local')
                
                message_obj = {
                    'message_id': message_id,
                    'structured': True,  # All sent messages use our protocol
                    'from_node_id': local_node_id,
                    'from_name': local_node_name,
                    'to_node_ids': [dest_id],
                    'is_bulletin': False,
                    'text': message,  # Store original text without protocol prefix
                    'timestamp': time.time(),
                    'direction': 'sent',
                    'delivery_status': 'pending',  # Will be updated by ACK handler
                    'archived': False
                }
                
                self.message_manager.save_message(message_obj)
                logger.info(f"Saved sent message to storage: {message_id}")
            else:
                logger.error(f"Failed to send message to {node_name} ({dest_id})")
                messagebox.showerror("Send Failed", f"Failed to send message to {node_name}")
        
        # Open the message dialog
        dialog = MessageDialog(self, node_id, node_name, send_callback)
        dialog.show()
    
    def _on_message_received(self, message_data: Dict[str, Any]):
        """Handle received message notification"""
        import time
        import re
        
        from_id = message_data.get('from')
        to_id = message_data.get('to')
        text = message_data.get('text', '')
        
        # Get node names
        nodes_data = self.data_collector.get_nodes_data() if self.data_collector else {}
        from_data = nodes_data.get(from_id, {})
        to_data = nodes_data.get(to_id, {})
        
        from_name = from_data.get('Node LongName', from_id)
        to_name = to_data.get('Node LongName', to_id)
        local_node_id = self._get_local_node_id()
        
        # Check if this is a read receipt: [RECEIPT:msg_id]
        receipt_match = re.match(r'^\[RECEIPT:([^\]]+)\]', text)
        if receipt_match:
            message_id = receipt_match.group(1)
            logger.info(f"Received read receipt for message {message_id} from {from_name}")
            
            # Update read receipt in message_manager
            self.message_manager.add_read_receipt(message_id, from_id)
            return  # Don't show notification for receipts
        
        # Check if this is a protocol-formatted message: [MSG:id]text
        msg_match = re.match(r'^\[MSG:([^\]]+)\](.*)$', text, re.DOTALL)
        if msg_match:
            message_id = msg_match.group(1)
            message_text = msg_match.group(2)
            logger.info(f"Received protocol message {message_id} from {from_name}: {repr(message_text)}")
            
            # Save to message_manager
            message_obj = {
                'message_id': message_id,
                'structured': True,  # Flag to indicate this uses our protocol
                'from_node_id': from_id,
                'from_name': from_name,
                'to_node_ids': [to_id] if to_id else [],
                'is_bulletin': not to_id or to_id == '^all',  # Bulletin if no specific recipient
                'text': message_text,  # Store without protocol prefix
                'timestamp': time.time(),
                'direction': 'received',
                'read': False,
                'archived': False
            }
            
            self.message_manager.save_message(message_obj)
            
            # Update unread messages cache for local node if this message is for us
            if to_id == local_node_id or not to_id:
                if local_node_id not in self.unread_messages:
                    self.unread_messages[local_node_id] = []
                self.unread_messages[local_node_id].append(message_obj)
                logger.info(f"Added to unread messages for local node (total: {len(self.unread_messages[local_node_id])})")
                self._update_messages_button()  # Update button badge
            
            # Show notification
            self._show_message_notification(from_id, from_name, to_name, message_text)
        else:
            # Non-protocol message (from other client like mobile app)
            logger.info(f"Received unstructured message from {from_name} to {to_name}: {repr(text)}")
            
            # Generate message_id for local tracking
            message_id = f"{from_id.strip('!')}_{int(time.time() * 1000)}"
            
            # Save as unstructured message
            message_obj = {
                'message_id': message_id,
                'structured': False,  # Flag to indicate this is from external client
                'from_node_id': from_id,
                'from_name': from_name,
                'to_node_ids': [to_id] if to_id else [],
                'is_bulletin': not to_id or to_id == '^all',
                'text': text,
                'timestamp': time.time(),
                'direction': 'received',
                'read': False,
                'archived': False
            }
            
            self.message_manager.save_message(message_obj)
            
            # Update unread messages cache for local node if this message is for us
            if to_id == local_node_id or not to_id:
                if local_node_id not in self.unread_messages:
                    self.unread_messages[local_node_id] = []
                self.unread_messages[local_node_id].append(message_obj)
                logger.info(f"Added unstructured message to unread (total: {len(self.unread_messages[local_node_id])})")
                self._update_messages_button()  # Update button badge
            
            # Show notification
            self._show_message_notification(from_id, from_name, to_name, text)
    
    def _show_message_notification(self, from_id: str, from_name: str, to_name: str, text: str):
        """Add message to scrolling notification banner at bottom"""
        # Add to recent messages (keep last 3)
        message_tuple = (from_name, to_name, text)
        self.recent_messages.append(message_tuple)
        if len(self.recent_messages) > 3:
            self.recent_messages.pop(0)  # Remove oldest
        
        # Create banner if it doesn't exist
        if self.notification_banner is None:
            self.notification_banner = tk.Frame(self, bg='#FFA500', relief="raised", borderwidth=2, height=35)
            self.notification_banner.pack(side="bottom", fill="x", padx=0, pady=0)
            self.notification_banner.pack_propagate(False)  # Keep fixed height
            
            self.notification_label = tk.Label(
                self.notification_banner,
                text="",
                font=self.font_bold,
                bg='#FFA500',
                fg='#000000',
                padx=10,
                pady=5,
                anchor="w"
            )
            self.notification_label.pack(fill="both", expand=True)
        
        # Reset to first message and start scrolling
        self.notification_index = 0
        self._update_notification_display()
    
    def _update_notification_display(self):
        """Update notification banner to show current message and schedule next"""
        # Cancel any existing timer
        if self.notification_timer is not None:
            self.after_cancel(self.notification_timer)
            self.notification_timer = None
        
        if not self.recent_messages or self.notification_label is None:
            return
        
        # Show current message
        from_name, to_name, text = self.recent_messages[self.notification_index]
        display_text = f"📨 From {from_name} To {to_name}: {text}"
        self.notification_label.config(text=display_text)
        
        # If we have multiple messages, schedule rotation
        if len(self.recent_messages) > 1:
            # Advance to next message (wrap around)
            self.notification_index = (self.notification_index + 1) % len(self.recent_messages)
            # Rotate every 5 seconds
            self.notification_timer = self.after(5000, self._update_notification_display)
    
    def _remove_message_notification(self, from_id: str):
        """Remove message notification for a node (legacy method - now using scrolling banner)"""
        # This method is kept for compatibility but doesn't remove individual notifications
        # The banner will scroll through recent messages automatically
        pass
    
    def quit_app(self):
        """Quit the application"""
        self.on_closing()
    
    def on_closing(self):
        """Handle application closing"""
        try:
            # Cancel all pending timer callbacks
            if hasattr(self, 'notification_timer') and self.notification_timer is not None:
                try:
                    self.after_cancel(self.notification_timer)
                    self.notification_timer = None
                except:
                    pass
            
            # Cancel all flash timers
            if hasattr(self, 'flash_timers'):
                for timer_id in list(self.flash_timers.values()):
                    try:
                        self.after_cancel(timer_id)
                    except:
                        pass
                self.flash_timers.clear()
            
            # Unsubscribe from events
            try:
                pub.unsubscribe(self._on_critical_error, "meshtastic.connection.critical_error")
            except:
                pass
            
            # Save any pending messages
            if hasattr(self, 'message_manager') and self.message_manager:
                try:
                    # Message manager auto-saves, but call save explicitly to be sure
                    self.message_manager.save_messages()
                except Exception as e:
                    logger.error(f"Error saving messages during shutdown: {e}")
            
            # Save window geometry (must be done before destroy)
            if hasattr(self, 'config_manager'):
                try:
                    # geometry() can fail if window is already being destroyed
                    geom = self.geometry()
                    self.config_manager.set('dashboard.window_geometry', geom)
                    self.config_manager.save_config()
                except Exception as e:
                    logger.error(f"Error saving config during shutdown: {e}")
            
            # Stop data collection (closes Meshtastic connection)
            if hasattr(self, 'data_collector') and self.data_collector:
                try:
                    self.data_collector.stop()
                except Exception as e:
                    logger.error(f"Error stopping data collector: {e}")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            # Always destroy, even if cleanup fails
            try:
                self.destroy()
            except:
                pass
    
    def _on_critical_error(self, error):
        """Handle critical connection errors - exit dashboard"""
        logger.error(f"Critical error received: {error}")
        messagebox.showerror(
            "Connection Error",
            f"Cannot start dashboard:\n\n{error}\n\n"
            f"Please check your Meshtastic interface connection and restart the application."
        )
        # Exit application
        self.after(100, self.on_closing)

def main():
    """Main entry point"""
    # Load config to get logging preferences
    config_mgr = ConfigManager()
    
    # Setup logging to file and console
    os.makedirs('logs', exist_ok=True)
    
    # Get log level from config
    log_level_str = config_mgr.get('logging.level', 'INFO').upper()
    if log_level_str == 'NOTSET':
        # Disable logging by setting to a level that shows nothing
        log_level = logging.CRITICAL + 1
    else:
        log_level = getattr(logging, log_level_str, logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/meshtastic_monitor.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    try:
        app = EnhancedDashboard()
        app.mainloop()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Application Error", f"Fatal error: {e}")

if __name__ == "__main__":
    main()
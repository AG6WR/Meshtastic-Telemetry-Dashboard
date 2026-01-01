"""
settings_dialog_qt.py - Qt/PySide6 Settings Dialog for Meshtastic Dashboard

This is the PySide6 port of settings_dialog.py, providing the same functionality
with a Qt-based UI for better touchscreen support on Raspberry Pi.

Usage:
    from settings_dialog_qt import SettingsDialogQt
    
    dialog = SettingsDialogQt(parent_window, config_manager)
    if dialog.exec() == QDialog.Accepted:
        # Settings were saved
        pass
"""

import sys
import logging

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QRadioButton, QButtonGroup, QGridLayout,
    QFrame, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from config_manager import ConfigManager
from qt_styles import (create_button, create_ok_button, create_apply_button, 
                       create_cancel_button, COLORS, CHECKBOX_STYLE, 
                       RADIOBUTTON_STYLE, TAB_STYLE, GROUPBOX_STYLE)

logger = logging.getLogger(__name__)


class SettingsDialogQt(QDialog):
    """Qt-based configuration dialog for dashboard settings"""
    
    # Signal emitted when settings are applied (for immediate refresh)
    settings_changed = Signal()
    
    def __init__(self, parent, config_manager: ConfigManager, data_collector=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.data_collector = data_collector  # Optional, for per-node hardware settings
        self.result = None
        self._current_hardware_node = "default"  # Track selected node for hardware settings
        
        self.setWindowTitle("Dashboard Settings")
        self.setMinimumSize(650, 550)
        self.setModal(True)
        
        # Initialize widget references
        self._init_widget_refs()
        
        self.create_widgets()
        self.load_current_values()
    
    def _init_widget_refs(self):
        """Initialize widget reference attributes"""
        # Connection widgets
        self.conn_type_group = None
        self.tcp_radio = None
        self.serial_radio = None
        self.tcp_group = None
        self.serial_group = None
        self.tcp_host = None
        self.tcp_port = None
        self.serial_port = None
        self.serial_baud = None
        self.conn_timeout = None
        self.retry_interval = None
        
        # Dashboard widgets
        self.time_format = None
        self.stale_row_seconds = None
        self.motion_display_seconds = None
        self.temp_unit = None
        
        # Telemetry widgets
        self.telemetry_vars = {}
        
        # Alert widgets
        self.offline_enabled = None
        self.offline_threshold = None
        self.voltage_enabled = None
        self.voltage_threshold = None
        self.temp_enabled = None
        self.temp_threshold = None
        
        # Email widgets
        self.email_enabled = None
        self.smtp_server = None
        self.smtp_port = None
        self.smtp_username = None
        self.smtp_password = None
        self.from_address = None
        self.to_addresses = None
        self.use_tls = None
        
        # Logging widgets
        self.log_level = None
        self.log_retention_days = None
        
        # Hardware widgets
        self.hardware_node_selector = None
        self.current_sensor_enabled = None
        self.full_scale_voltage_mv = None
        self.full_scale_current_a = None
        self.shunt_resistance_display = None
        self.scale_factor_display = None
        self.example_display = None
    
    def create_widgets(self):
        """Create dialog widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Apply dark theme styles to this dialog
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_main']};
            }}
            QLabel {{
                color: {COLORS['fg_normal']};
            }}
            QLineEdit, QComboBox {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['fg_normal']};
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11pt;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['fg_normal']};
                selection-background-color: #555555;
                selection-color: white;
            }}
            {CHECKBOX_STYLE}
            {RADIOBUTTON_STYLE}
            {TAB_STYLE}
            {GROUPBOX_STYLE}
        """)
        
        # Tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Connection tab
        conn_tab = QWidget()
        tab_widget.addTab(conn_tab, "Connection")
        self.create_connection_tab(conn_tab)
        
        # Dashboard tab
        dash_tab = QWidget()
        tab_widget.addTab(dash_tab, "Dashboard")
        self.create_dashboard_tab(dash_tab)
        
        # Telemetry tab - DISABLED for now, needs more work
        # telemetry_tab = QWidget()
        # tab_widget.addTab(telemetry_tab, "Telemetry")
        # self.create_telemetry_tab(telemetry_tab)
        
        # Alerts tab
        alerts_tab = QWidget()
        tab_widget.addTab(alerts_tab, "Alerts")
        self.create_alerts_tab(alerts_tab)
        
        # Email tab
        email_tab = QWidget()
        tab_widget.addTab(email_tab, "Email")
        self.create_email_tab(email_tab)
        
        # Hardware tab
        hardware_tab = QWidget()
        tab_widget.addTab(hardware_tab, "Hardware")
        self.create_hardware_tab(hardware_tab)
        
        # Logging tab
        logging_tab = QWidget()
        tab_widget.addTab(logging_tab, "Logging")
        self.create_logging_tab(logging_tab)
        
        # Button frame
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 10, 0, 0)
        
        button_layout.addStretch()
        
        # OK button (primary action - blue)
        ok_btn = create_button("✓ OK", "primary", self.ok)
        
        # Apply button (green)
        apply_btn = create_apply_button(self.apply)
        
        # Cancel button (gray)
        cancel_btn = create_cancel_button(self.cancel)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(apply_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def create_connection_tab(self, parent):
        """Create connection settings tab"""
        layout = QVBoxLayout(parent)
        
        # Connection Type Selection
        type_group = QGroupBox("Connection Type")
        type_layout = QHBoxLayout(type_group)
        
        self.conn_type_group = QButtonGroup(self)
        self.tcp_radio = QRadioButton("TCP/IP Network")
        self.serial_radio = QRadioButton("USB/Serial Port")
        
        self.conn_type_group.addButton(self.tcp_radio, 0)
        self.conn_type_group.addButton(self.serial_radio, 1)
        
        self.tcp_radio.toggled.connect(self._toggle_connection_fields)
        
        type_layout.addWidget(self.tcp_radio)
        type_layout.addWidget(self.serial_radio)
        type_layout.addStretch()
        
        layout.addWidget(type_group)
        
        # TCP/IP Settings
        self.tcp_group = QGroupBox("Meshtastic TCP/IP Interface")
        tcp_layout = QGridLayout(self.tcp_group)
        
        tcp_layout.addWidget(QLabel("Host/IP Address:"), 0, 0)
        self.tcp_host = QLineEdit()
        self.tcp_host.setMinimumWidth(150)
        tcp_layout.addWidget(self.tcp_host, 0, 1)
        
        tcp_layout.addWidget(QLabel("Port:"), 0, 2)
        self.tcp_port = QLineEdit()
        self.tcp_port.setMaximumWidth(80)
        tcp_layout.addWidget(self.tcp_port, 0, 3)
        
        tcp_layout.setColumnStretch(1, 1)
        layout.addWidget(self.tcp_group)
        
        # USB/Serial Settings
        self.serial_group = QGroupBox("USB/Serial Interface")
        serial_layout = QGridLayout(self.serial_group)
        
        serial_layout.addWidget(QLabel("Serial Port:"), 0, 0)
        
        # Port combo and refresh button
        port_widget = QWidget()
        port_layout = QHBoxLayout(port_widget)
        port_layout.setContentsMargins(0, 0, 0, 0)
        
        self.serial_port = QComboBox()
        self.serial_port.setEditable(True)
        self.serial_port.setMinimumWidth(150)
        port_layout.addWidget(self.serial_port)
        
        refresh_btn = QPushButton("↻")
        refresh_btn.setMaximumWidth(30)
        refresh_btn.clicked.connect(self._refresh_serial_ports)
        port_layout.addWidget(refresh_btn)
        
        serial_layout.addWidget(port_widget, 0, 1)
        serial_layout.addWidget(QLabel("(e.g., COM3 on Windows, /dev/ttyUSB0 on Linux)"), 0, 2)
        
        serial_layout.addWidget(QLabel("Baud Rate:"), 1, 0)
        self.serial_baud = QComboBox()
        self.serial_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.serial_baud.setCurrentText("115200")
        serial_layout.addWidget(self.serial_baud, 1, 1)
        
        serial_layout.setColumnStretch(2, 1)
        layout.addWidget(self.serial_group)
        
        # Connection Options
        conn_group = QGroupBox("Connection Options")
        conn_layout = QGridLayout(conn_group)
        
        conn_layout.addWidget(QLabel("Connection Timeout:"), 0, 0)
        self.conn_timeout = QLineEdit()
        self.conn_timeout.setMaximumWidth(80)
        conn_layout.addWidget(self.conn_timeout, 0, 1)
        conn_layout.addWidget(QLabel("seconds"), 0, 2)
        
        conn_layout.addWidget(QLabel("Retry Interval:"), 1, 0)
        self.retry_interval = QLineEdit()
        self.retry_interval.setMaximumWidth(80)
        conn_layout.addWidget(self.retry_interval, 1, 1)
        conn_layout.addWidget(QLabel("seconds"), 1, 2)
        
        conn_layout.setColumnStretch(3, 1)
        layout.addWidget(conn_group)
        
        layout.addStretch()
    
    def create_dashboard_tab(self, parent):
        """Create dashboard settings tab"""
        layout = QVBoxLayout(parent)
        
        # Display Options
        display_group = QGroupBox("Display Options")
        display_layout = QGridLayout(display_group)
        
        display_layout.addWidget(QLabel("Time Format:"), 0, 0)
        self.time_format = QComboBox()
        self.time_format.addItems(["DDd:HHh:MMm:SSs", "Seconds", "Minutes"])
        display_layout.addWidget(self.time_format, 0, 1)
        
        display_layout.addWidget(QLabel("Stale Row Threshold:"), 1, 0)
        self.stale_row_seconds = QLineEdit()
        self.stale_row_seconds.setMaximumWidth(80)
        display_layout.addWidget(self.stale_row_seconds, 1, 1)
        display_layout.addWidget(QLabel("seconds"), 1, 2)
        
        display_layout.addWidget(QLabel("Motion Display Duration:"), 2, 0)
        self.motion_display_seconds = QLineEdit()
        self.motion_display_seconds.setMaximumWidth(80)
        display_layout.addWidget(self.motion_display_seconds, 2, 1)
        display_layout.addWidget(QLabel("seconds (show motion indicator)"), 2, 2)
        
        display_layout.addWidget(QLabel("Temperature Unit:"), 3, 0)
        self.temp_unit = QComboBox()
        self.temp_unit.addItems(["Celsius (°C)", "Fahrenheit (°F)"])
        display_layout.addWidget(self.temp_unit, 3, 1)
        
        display_layout.setColumnStretch(3, 1)
        layout.addWidget(display_group)
        
        layout.addStretch()
    
    def create_telemetry_tab(self, parent):
        """Create telemetry field settings tab"""
        layout = QVBoxLayout(parent)
        
        info_label = QLabel("Select which telemetry fields to display in card view:")
        info_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Telemetry field checkboxes
        telemetry_fields = [
            ("voltage", "Voltage", "Show battery/power voltage readings"),
            ("temperature", "Temperature", "Show temperature sensor readings"),
            ("humidity", "Humidity", "Show humidity sensor readings"),
            ("pressure", "Pressure", "Show atmospheric pressure readings"),
            ("battery", "Battery", "Show battery percentage levels"),
            ("snr", "SNR", "Show signal-to-noise ratio"),
            ("channel_utilization", "Channel Usage", "Show mesh channel utilization"),
            ("current", "Current", "Show current consumption readings"),
            ("uptime", "Uptime", "Show device uptime information")
        ]
        
        for field_key, display_name, description in telemetry_fields:
            field_widget = QWidget()
            field_layout = QHBoxLayout(field_widget)
            field_layout.setContentsMargins(10, 2, 10, 2)
            
            checkbox = QCheckBox(display_name)
            checkbox.setMinimumWidth(180)
            field_layout.addWidget(checkbox)
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: gray; font-size: 10pt;")
            field_layout.addWidget(desc_label)
            field_layout.addStretch()
            
            self.telemetry_vars[field_key] = checkbox
            layout.addWidget(field_widget)
        
        layout.addStretch()
    
    def create_alerts_tab(self, parent):
        """Create alerts settings tab"""
        layout = QVBoxLayout(parent)
        
        # Alert Rules
        rules_group = QGroupBox("Alert Thresholds")
        rules_layout = QVBoxLayout(rules_group)
        
        # Node Offline
        offline_widget = QWidget()
        offline_layout = QHBoxLayout(offline_widget)
        offline_layout.setContentsMargins(0, 0, 0, 0)
        
        self.offline_enabled = QCheckBox("Node Offline Alert")
        offline_layout.addWidget(self.offline_enabled)
        
        offline_layout.addWidget(QLabel("After:"))
        self.offline_threshold = QLineEdit()
        self.offline_threshold.setMaximumWidth(60)
        offline_layout.addWidget(self.offline_threshold)
        offline_layout.addWidget(QLabel("minutes"))
        
        info_label = QLabel("(Offline status threshold: 16 min)")
        info_label.setStyleSheet("color: gray; font-size: 8pt;")
        offline_layout.addWidget(info_label)
        offline_layout.addStretch()
        
        rules_layout.addWidget(offline_widget)
        
        # Low Voltage
        voltage_widget = QWidget()
        voltage_layout = QHBoxLayout(voltage_widget)
        voltage_layout.setContentsMargins(0, 0, 0, 0)
        
        self.voltage_enabled = QCheckBox("Low Voltage Alert")
        voltage_layout.addWidget(self.voltage_enabled)
        
        voltage_layout.addWidget(QLabel("Below:"))
        self.voltage_threshold = QLineEdit()
        self.voltage_threshold.setMaximumWidth(60)
        voltage_layout.addWidget(self.voltage_threshold)
        voltage_layout.addWidget(QLabel("volts"))
        voltage_layout.addStretch()
        
        rules_layout.addWidget(voltage_widget)
        
        # High Temperature
        temp_widget = QWidget()
        temp_layout = QHBoxLayout(temp_widget)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        
        self.temp_enabled = QCheckBox("High Temperature Alert")
        temp_layout.addWidget(self.temp_enabled)
        
        temp_layout.addWidget(QLabel("Above:"))
        self.temp_threshold = QLineEdit()
        self.temp_threshold.setMaximumWidth(60)
        temp_layout.addWidget(self.temp_threshold)
        temp_layout.addWidget(QLabel("°C"))
        temp_layout.addStretch()
        
        rules_layout.addWidget(temp_widget)
        
        layout.addWidget(rules_group)
        layout.addStretch()
    
    def create_email_tab(self, parent):
        """Create email settings tab"""
        layout = QVBoxLayout(parent)
        
        # Enable Email
        self.email_enabled = QCheckBox("Enable Email Alerts")
        layout.addWidget(self.email_enabled)
        
        # SMTP Settings
        smtp_group = QGroupBox("SMTP Configuration")
        smtp_layout = QGridLayout(smtp_group)
        
        smtp_layout.addWidget(QLabel("SMTP Server:"), 0, 0)
        self.smtp_server = QLineEdit()
        smtp_layout.addWidget(self.smtp_server, 0, 1)
        
        smtp_layout.addWidget(QLabel("Port:"), 0, 2)
        self.smtp_port = QLineEdit()
        self.smtp_port.setMaximumWidth(60)
        smtp_layout.addWidget(self.smtp_port, 0, 3)
        
        smtp_layout.addWidget(QLabel("Username:"), 1, 0)
        self.smtp_username = QLineEdit()
        smtp_layout.addWidget(self.smtp_username, 1, 1, 1, 3)
        
        smtp_layout.addWidget(QLabel("Password:"), 2, 0)
        self.smtp_password = QLineEdit()
        self.smtp_password.setEchoMode(QLineEdit.Password)
        smtp_layout.addWidget(self.smtp_password, 2, 1, 1, 3)
        
        smtp_layout.addWidget(QLabel("From Address:"), 3, 0)
        self.from_address = QLineEdit()
        smtp_layout.addWidget(self.from_address, 3, 1, 1, 3)
        
        smtp_layout.addWidget(QLabel("To Addresses:"), 4, 0)
        self.to_addresses = QLineEdit()
        smtp_layout.addWidget(self.to_addresses, 4, 1, 1, 3)
        
        hint_label = QLabel("(comma-separated)")
        hint_label.setStyleSheet("color: gray;")
        smtp_layout.addWidget(hint_label, 5, 1)
        
        self.use_tls = QCheckBox("Use TLS encryption")
        smtp_layout.addWidget(self.use_tls, 6, 1)
        
        # Test Email button - right side, aligned with TLS checkbox row
        test_email_btn = create_button("Test Email", "warning", self.test_email)
        test_email_btn.setMaximumWidth(120)
        smtp_layout.addWidget(test_email_btn, 6, 3, Qt.AlignRight)
        
        smtp_layout.setColumnStretch(1, 1)
        layout.addWidget(smtp_group)
        
        layout.addStretch()
    
    def create_hardware_tab(self, parent):
        """Create hardware settings tab"""
        layout = QVBoxLayout(parent)
        
        # Node Selector (for per-node settings)
        node_select_layout = QHBoxLayout()
        node_select_layout.addWidget(QLabel("Configure for:"))
        self.hardware_node_selector = QComboBox()
        self.hardware_node_selector.addItem("Default (all nodes)", "default")
        
        # Add known nodes if data_collector is available
        if self.data_collector:
            for node_id, node_data in self.data_collector.nodes_data.items():
                long_name = node_data.get('Node LongName', node_id)
                short_name = node_data.get('Node ShortName', '')
                display = f"{long_name} ({short_name})" if short_name else long_name
                self.hardware_node_selector.addItem(display, node_id)
        
        self.hardware_node_selector.setMinimumWidth(200)
        self.hardware_node_selector.currentIndexChanged.connect(self._on_hardware_node_changed)
        node_select_layout.addWidget(self.hardware_node_selector)
        node_select_layout.addStretch()
        layout.addLayout(node_select_layout)
        
        # Enable checkbox - outside the group box like Email tab
        self.current_sensor_enabled = QCheckBox("Enable current scaling")
        layout.addWidget(self.current_sensor_enabled)
        
        # External Current Sensor Group
        sensor_group = QGroupBox("Current Sensor Configuration")
        sensor_layout = QGridLayout(sensor_group)
        
        # Full Scale Voltage
        sensor_layout.addWidget(QLabel("Full Scale Voltage:"), 0, 0)
        self.full_scale_voltage_mv = QLineEdit()
        self.full_scale_voltage_mv.setMaximumWidth(80)
        sensor_layout.addWidget(self.full_scale_voltage_mv, 0, 1)
        sensor_layout.addWidget(QLabel("mV"), 0, 2)
        
        # Full Scale Current
        sensor_layout.addWidget(QLabel("Full Scale Current:"), 1, 0)
        self.full_scale_current_a = QLineEdit()
        self.full_scale_current_a.setMaximumWidth(80)
        sensor_layout.addWidget(self.full_scale_current_a, 1, 1)
        sensor_layout.addWidget(QLabel("A"), 1, 2)
        
        # Hint text
        hint_label = QLabel("(voltage across shunt at full scale current)")
        hint_label.setStyleSheet("color: gray;")
        sensor_layout.addWidget(hint_label, 2, 1, 1, 2)
        
        # Calculated values section
        sensor_layout.addWidget(QLabel("Shunt Resistance:"), 3, 0)
        self.shunt_resistance_display = QLabel("100.00 mΩ")
        self.shunt_resistance_display.setStyleSheet("font-weight: bold; color: #4a90d9;")
        sensor_layout.addWidget(self.shunt_resistance_display, 3, 1, 1, 2)
        
        sensor_layout.addWidget(QLabel("Scaling Factor:"), 4, 0)
        self.scale_factor_display = QLabel("1.00x")
        self.scale_factor_display.setStyleSheet("font-weight: bold; color: #4a90d9;")
        sensor_layout.addWidget(self.scale_factor_display, 4, 1, 1, 2)
        
        # Example calculation
        self.example_display = QLabel("Example: 100mA raw → 100mA scaled")
        self.example_display.setStyleSheet("color: gray;")
        sensor_layout.addWidget(self.example_display, 5, 1, 1, 2)
        
        sensor_layout.setColumnStretch(2, 1)
        layout.addWidget(sensor_group)
        
        # Help text
        help_group = QGroupBox("About Current Scaling")
        help_layout = QVBoxLayout(help_group)
        
        help_text = (
            "The INA current sensor measures voltage across a shunt resistor.\n"
            "The default shunt is 100mΩ (350mV at 3.5A full scale).\n\n"
            "If you've installed a different shunt resistor for higher current\n"
            "measurement, enter your shunt's specifications above.\n\n"
            "The scaling factor adjusts the reported current to match your hardware."
        )
        help_label = QLabel(help_text)
        help_label.setStyleSheet("font-size: 9pt; color: #aaaaaa;")
        help_layout.addWidget(help_label)
        
        layout.addWidget(help_group)
        
        # Connect signals for live calculation update
        self.full_scale_voltage_mv.textChanged.connect(self._update_current_calculations)
        self.full_scale_current_a.textChanged.connect(self._update_current_calculations)
        self.current_sensor_enabled.toggled.connect(self._update_current_calculations)
        
        layout.addStretch()
    
    def _update_current_calculations(self):
        """Update the calculated shunt resistance and scaling factor display"""
        try:
            voltage_mv = float(self.full_scale_voltage_mv.text() or 0)
            current_a = float(self.full_scale_current_a.text() or 0)
            enabled = self.current_sensor_enabled.isChecked()
            
            if current_a > 0 and voltage_mv > 0:
                # Calculate shunt resistance: R = V / I, R(mΩ) = V(mV) / I(A)
                shunt_mohm = voltage_mv / current_a
                self.shunt_resistance_display.setText(f"{shunt_mohm:.2f} mΩ")
                
                # Calculate scaling factor: default_shunt / user_shunt
                # Default shunt is 100mΩ (350mV / 3.5A)
                default_shunt = 100.0
                scale_factor = default_shunt / shunt_mohm if shunt_mohm > 0 else 1.0
                
                if enabled:
                    self.scale_factor_display.setText(f"{scale_factor:.2f}x")
                    # Example: show what 100mA raw becomes
                    scaled_example = 100 * scale_factor
                    if scaled_example >= 1000:
                        self.example_display.setText(f"Example: 100mA raw → {scaled_example/1000:.2f}A scaled")
                    else:
                        self.example_display.setText(f"Example: 100mA raw → {scaled_example:.0f}mA scaled")
                else:
                    self.scale_factor_display.setText("1.00x (disabled)")
                    self.example_display.setText("Example: 100mA raw → 100mA scaled (no scaling)")
            else:
                self.shunt_resistance_display.setText("-- mΩ")
                self.scale_factor_display.setText("--")
                self.example_display.setText("Enter valid values above")
        except ValueError:
            self.shunt_resistance_display.setText("-- mΩ")
            self.scale_factor_display.setText("--")
            self.example_display.setText("Enter valid numeric values")
    
    def _on_hardware_node_changed(self, index):
        """Handle hardware node selector change - save current and load new"""
        # Save current node's settings before switching
        self._save_hardware_settings_for_node(self._current_hardware_node)
        
        # Switch to new node
        self._current_hardware_node = self.hardware_node_selector.currentData()
        
        # Load new node's settings
        self._load_hardware_settings_for_node(self._current_hardware_node)
    
    def _get_hardware_config_path(self, node_id: str) -> str:
        """Get the config path prefix for a node's hardware settings"""
        if node_id == "default":
            return "hardware.current_sensor.default"
        else:
            return f"hardware.current_sensor.nodes.{node_id}"
    
    def _load_hardware_settings_for_node(self, node_id: str):
        """Load hardware settings for a specific node"""
        path = self._get_hardware_config_path(node_id)
        
        # If this is a specific node, check if it has settings, otherwise use default
        if node_id != "default":
            node_settings = self.config_manager.get(path)
            if not node_settings:
                # No specific settings, show defaults but don't enable
                path = "hardware.current_sensor.default"
        
        self.current_sensor_enabled.setChecked(
            self.config_manager.get(f'{path}.enabled', False))
        self.full_scale_voltage_mv.setText(
            str(self.config_manager.get(f'{path}.full_scale_voltage_mv', 350)))
        self.full_scale_current_a.setText(
            str(self.config_manager.get(f'{path}.full_scale_current_a', 3.5)))
        
        self._update_current_calculations()
    
    def _save_hardware_settings_for_node(self, node_id: str):
        """Save hardware settings for a specific node"""
        path = self._get_hardware_config_path(node_id)
        
        try:
            enabled = self.current_sensor_enabled.isChecked()
            voltage = float(self.full_scale_voltage_mv.text() or 350)
            current = float(self.full_scale_current_a.text() or 3.5)
            
            # For specific nodes, only save if settings differ from default
            if node_id != "default":
                default_enabled = self.config_manager.get('hardware.current_sensor.default.enabled', False)
                default_voltage = self.config_manager.get('hardware.current_sensor.default.full_scale_voltage_mv', 350)
                default_current = self.config_manager.get('hardware.current_sensor.default.full_scale_current_a', 3.5)
                
                # If same as default, remove node-specific settings
                if enabled == default_enabled and voltage == default_voltage and current == default_current:
                    nodes = self.config_manager.get('hardware.current_sensor.nodes', {})
                    if node_id in nodes:
                        del nodes[node_id]
                        self.config_manager.set('hardware.current_sensor.nodes', nodes)
                    return
            
            self.config_manager.set(f'{path}.enabled', enabled)
            self.config_manager.set(f'{path}.full_scale_voltage_mv', voltage)
            self.config_manager.set(f'{path}.full_scale_current_a', current)
        except ValueError:
            pass  # Invalid values, don't save

    def create_logging_tab(self, parent):
        """Create logging settings tab"""
        layout = QVBoxLayout(parent)
        
        # Log Level Group
        level_group = QGroupBox("Log Level")
        level_layout = QVBoxLayout(level_group)
        
        level_layout.addWidget(QLabel("Select logging verbosity:"))
        
        self.log_level = QComboBox()
        self.log_level.addItems([
            "Disable Logging",
            "CRITICAL",
            "ERROR",
            "WARNING",
            "INFO",
            "DEBUG"
        ])
        self.log_level.setMaximumWidth(200)
        level_layout.addWidget(self.log_level)
        
        # Help text
        help_text = (
            "DEBUG: Most verbose - shows all diagnostic details\n"
            "INFO: Normal operation messages and updates\n"
            "WARNING: Unexpected events that don't stop operation\n"
            "ERROR: Serious problems that prevent features from working\n"
            "CRITICAL: Severe errors that may crash the application\n"
            "Disable Logging: Turn off all logging output"
        )
        help_label = QLabel(help_text)
        help_label.setStyleSheet("font-size: 8pt; color: gray;")
        level_layout.addWidget(help_label)
        
        layout.addWidget(level_group)
        
        # Log Retention Group
        retention_group = QGroupBox("Log File Retention")
        retention_layout = QVBoxLayout(retention_group)
        
        retention_layout.addWidget(QLabel("Delete log files older than:"))
        
        self.log_retention_days = QComboBox()
        self.log_retention_days.addItems([
            "5 days",
            "30 days",
            "60 days",
            "90 days",
            "360 days",
            "Forever"
        ])
        self.log_retention_days.setMaximumWidth(200)
        retention_layout.addWidget(self.log_retention_days)
        
        retention_help = QLabel(
            "Application logs (meshtastic_monitor.log) will be cleaned up automatically.\n"
            "Node CSV logs are managed separately by the Data settings."
        )
        retention_help.setStyleSheet("font-size: 8pt; color: gray;")
        retention_layout.addWidget(retention_help)
        
        layout.addWidget(retention_group)
        layout.addStretch()
    
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
            current_text = self.serial_port.currentText()
            self.serial_port.clear()
            self.serial_port.addItems(port_list)
            
            # Restore previous selection if it exists
            if current_text:
                index = self.serial_port.findText(current_text)
                if index >= 0:
                    self.serial_port.setCurrentIndex(index)
                else:
                    self.serial_port.setCurrentText(current_text)
            elif port_list:
                self.serial_port.setCurrentIndex(0)
                
        except Exception as e:
            logger.warning(f"Failed to enumerate serial ports: {e}")
            # Provide defaults on error
            if sys.platform.startswith('win'):
                self.serial_port.clear()
                self.serial_port.addItems(['COM3', 'COM4', 'COM5'])
            else:
                self.serial_port.clear()
                self.serial_port.addItems(['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0'])
    
    def _toggle_connection_fields(self):
        """Show/hide connection fields based on selected type"""
        is_tcp = self.tcp_radio.isChecked()
        self.tcp_group.setVisible(is_tcp)
        self.serial_group.setVisible(not is_tcp)
    
    def load_current_values(self):
        """Load current configuration values into dialog"""
        # Connection settings
        interface_type = self.config_manager.get('meshtastic.interface.type', 'tcp')
        if interface_type == 'tcp':
            self.tcp_radio.setChecked(True)
        else:
            self.serial_radio.setChecked(True)
        
        self.tcp_host.setText(self.config_manager.get('meshtastic.interface.host', '192.168.1.91'))
        self.tcp_port.setText(str(self.config_manager.get('meshtastic.interface.port', 4403)))
        
        # Load serial port and refresh available ports
        self._refresh_serial_ports()
        saved_serial_port = self.config_manager.get('meshtastic.interface.serial_port', '')
        if saved_serial_port:
            self.serial_port.setCurrentText(saved_serial_port)
        self.serial_baud.setCurrentText(str(self.config_manager.get('meshtastic.interface.baud', 115200)))
        
        self.conn_timeout.setText(str(self.config_manager.get('meshtastic.connection_timeout', 30)))
        self.retry_interval.setText(str(self.config_manager.get('meshtastic.retry_interval', 60)))
        
        # Toggle connection fields based on type
        self._toggle_connection_fields()
        
        # Dashboard settings
        self.time_format.setCurrentText(self.config_manager.get('dashboard.time_format', 'DDd:HHh:MMm:SSs'))
        self.stale_row_seconds.setText(str(self.config_manager.get('dashboard.stale_row_seconds', 300)))
        self.motion_display_seconds.setText(str(self.config_manager.get('dashboard.motion_display_seconds', 900)))
        
        # Temperature unit setting
        temp_unit_value = self.config_manager.get('dashboard.temperature_unit', 'C')
        self.temp_unit.setCurrentText('Celsius (°C)' if temp_unit_value == 'C' else 'Fahrenheit (°F)')
        
        # Telemetry field settings
        telemetry_config = self.config_manager.get('dashboard.telemetry_fields', {})
        for field_key, checkbox in self.telemetry_vars.items():
            checkbox.setChecked(telemetry_config.get(field_key, True))
        
        # Alert settings
        self.offline_enabled.setChecked(self.config_manager.get('alerts.rules.node_offline.enabled', True))
        offline_seconds = self.config_manager.get('alerts.rules.node_offline.threshold_seconds', 960)
        self.offline_threshold.setText(str(offline_seconds // 60))
        
        self.voltage_enabled.setChecked(self.config_manager.get('alerts.rules.low_voltage.enabled', True))
        self.voltage_threshold.setText(str(self.config_manager.get('alerts.rules.low_voltage.threshold_volts', 11.0)))
        
        self.temp_enabled.setChecked(self.config_manager.get('alerts.rules.high_temperature.enabled', True))
        self.temp_threshold.setText(str(self.config_manager.get('alerts.rules.high_temperature.threshold_celsius', 35)))
        
        # Email settings
        self.email_enabled.setChecked(self.config_manager.get('alerts.email_enabled', False))
        self.smtp_server.setText(self.config_manager.get('alerts.email_config.smtp_server', 'smtp.mail.me.com'))
        self.smtp_port.setText(str(self.config_manager.get('alerts.email_config.smtp_port', 587)))
        self.smtp_username.setText(self.config_manager.get('alerts.email_config.username', ''))
        self.smtp_password.setText(self.config_manager.get('alerts.email_config.password', ''))
        self.from_address.setText(self.config_manager.get('alerts.email_config.from_address', ''))
        to_addrs = self.config_manager.get('alerts.email_config.to_addresses', [])
        self.to_addresses.setText(', '.join(to_addrs))
        self.use_tls.setChecked(self.config_manager.get('alerts.email_config.use_tls', True))
        
        # Logging settings
        log_level = self.config_manager.get('logging.level', 'INFO')
        if log_level == 'NOTSET':
            self.log_level.setCurrentText('Disable Logging')
        else:
            self.log_level.setCurrentText(log_level)
        
        retention_days = self.config_manager.get('logging.retention_days', -1)
        if retention_days == -1:
            self.log_retention_days.setCurrentText('Forever')
        else:
            self.log_retention_days.setCurrentText(f'{retention_days} days')
        
        # Hardware settings - load for the currently selected node (default)
        self._current_hardware_node = "default"
        if self.hardware_node_selector:
            self.hardware_node_selector.setCurrentIndex(0)  # Select "Default (all nodes)"
        self._load_hardware_settings_for_node(self._current_hardware_node)
    
    def test_email(self):
        """Test email configuration"""
        try:
            # Save current values temporarily
            self.save_values()
            
            # Import and test
            from alert_system import AlertManager
            alert_config = self.config_manager.get_section('alerts')
            alert_manager = AlertManager(alert_config)
            
            success, error_msg = alert_manager.test_email_with_error()
            if success:
                QMessageBox.information(self, "Email Test", "Test email sent successfully! Check your inbox.")
            else:
                QMessageBox.critical(self, "Email Test", f"Failed to send test email:\n\n{error_msg}")
                
        except Exception as e:
            QMessageBox.critical(self, "Email Test", f"Email test failed: {e}")
    
    def save_values(self):
        """Save dialog values to configuration"""
        try:
            # Connection settings
            conn_type = 'tcp' if self.tcp_radio.isChecked() else 'serial'
            self.config_manager.set('meshtastic.interface.type', conn_type)
            
            if conn_type == 'tcp':
                self.config_manager.set('meshtastic.interface.host', self.tcp_host.text())
                self.config_manager.set('meshtastic.interface.port', int(self.tcp_port.text()))
            else:  # serial
                self.config_manager.set('meshtastic.interface.serial_port', self.serial_port.currentText())
                self.config_manager.set('meshtastic.interface.baud', int(self.serial_baud.currentText()))
            
            self.config_manager.set('meshtastic.connection_timeout', int(self.conn_timeout.text()))
            self.config_manager.set('meshtastic.retry_interval', int(self.retry_interval.text()))
            
            # Dashboard settings
            self.config_manager.set('dashboard.time_format', self.time_format.currentText())
            self.config_manager.set('dashboard.stale_row_seconds', int(self.stale_row_seconds.text()))
            self.config_manager.set('dashboard.motion_display_seconds', int(self.motion_display_seconds.text()))
            
            # Temperature unit setting
            temp_unit_value = 'C' if 'Celsius' in self.temp_unit.currentText() else 'F'
            self.config_manager.set('dashboard.temperature_unit', temp_unit_value)
            
            # Telemetry field settings
            telemetry_fields = {}
            for field_key, checkbox in self.telemetry_vars.items():
                telemetry_fields[field_key] = checkbox.isChecked()
            self.config_manager.set('dashboard.telemetry_fields', telemetry_fields)
            
            # Alert settings
            self.config_manager.set('alerts.rules.node_offline.enabled', self.offline_enabled.isChecked())
            offline_minutes = int(self.offline_threshold.text())
            self.config_manager.set('alerts.rules.node_offline.threshold_seconds', offline_minutes * 60)
            
            self.config_manager.set('alerts.rules.low_voltage.enabled', self.voltage_enabled.isChecked())
            self.config_manager.set('alerts.rules.low_voltage.threshold_volts', float(self.voltage_threshold.text()))
            
            self.config_manager.set('alerts.rules.high_temperature.enabled', self.temp_enabled.isChecked())
            self.config_manager.set('alerts.rules.high_temperature.threshold_celsius', float(self.temp_threshold.text()))
            
            # Email settings
            self.config_manager.set('alerts.email_enabled', self.email_enabled.isChecked())
            self.config_manager.set('alerts.email_config.smtp_server', self.smtp_server.text())
            self.config_manager.set('alerts.email_config.smtp_port', int(self.smtp_port.text()))
            self.config_manager.set('alerts.email_config.username', self.smtp_username.text())
            self.config_manager.set('alerts.email_config.password', self.smtp_password.text())
            self.config_manager.set('alerts.email_config.from_address', self.from_address.text())
            
            to_addrs = [addr.strip() for addr in self.to_addresses.text().split(',') if addr.strip()]
            self.config_manager.set('alerts.email_config.to_addresses', to_addrs)
            self.config_manager.set('alerts.email_config.use_tls', self.use_tls.isChecked())
            
            # Logging settings
            log_level_value = self.log_level.currentText()
            if log_level_value == 'Disable Logging':
                self.config_manager.set('logging.level', 'NOTSET')
            else:
                self.config_manager.set('logging.level', log_level_value)
            
            retention_value = self.log_retention_days.currentText()
            if retention_value == 'Forever':
                self.config_manager.set('logging.retention_days', -1)
            else:
                days = int(retention_value.split()[0])
                self.config_manager.set('logging.retention_days', days)
            
            # Hardware settings - save currently displayed node's settings
            self._save_hardware_settings_for_node(self._current_hardware_node)
            
            # Save to file
            self.config_manager.save_config()
            
        except ValueError as e:
            QMessageBox.critical(self, "Configuration Error", f"Invalid value: {e}")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Configuration Error", f"Failed to save configuration: {e}")
            return False
        
        return True
    
    def ok(self):
        """OK button handler"""
        if self.save_values():
            self.result = True
            self.accept()
    
    def apply(self):
        """Apply button handler"""
        if self.save_values():
            # Emit signal to trigger dashboard refresh
            self.settings_changed.emit()
    
    def cancel(self):
        """Cancel button handler"""
        self.result = False
        self.reject()


# Test harness for standalone testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Load config manager
    config_manager = ConfigManager()
    
    dialog = SettingsDialogQt(None, config_manager)
    result = dialog.exec()
    
    if result == QDialog.Accepted:
        print("Settings saved!")
    else:
        print("Settings cancelled.")
    
    sys.exit(0)

"""
Node Detail Window (Qt/PySide6) for displaying detailed information about a single node

This is the PySide6 port of node_detail_window.py.

Usage:
    from node_detail_window_qt import NodeDetailWindowQt
    
    window = NodeDetailWindowQt(parent, node_id, node_data, on_logs, on_csv, on_plot, data_collector)
    window.show()
"""

import logging
from datetime import datetime
from typing import Callable, Optional
import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QGridLayout, QMessageBox,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from qt_styles import create_button, create_close_button, COLORS, BUTTON_STYLES, get_font

logger = logging.getLogger(__name__)


class NodeDetailWindowQt(QDialog):
    """Qt window displaying detailed information for a single Meshtastic node"""
    
    def __init__(self, parent, node_id: str, node_data: dict,
                 on_logs: Optional[Callable] = None,
                 on_csv: Optional[Callable] = None,
                 on_plot: Optional[Callable] = None,
                 data_collector=None):
        """
        Create a node detail window
        
        Args:
            parent: Parent dashboard instance
            node_id: Node ID (with ! prefix)
            node_data: Dictionary containing node information
            on_logs: Callback for logs button
            on_csv: Callback for CSV button
            on_plot: Callback for plot button
            data_collector: DataCollector instance for forget_node functionality
        """
        super().__init__(parent)
        
        self.parent_window = parent
        self.node_id = node_id
        self.node_data = node_data
        self.on_logs = on_logs
        self.on_csv = on_csv
        self.on_plot = on_plot
        self.data_collector = data_collector
        
        # Get color scheme from parent or use defaults
        self.colors = getattr(parent, 'colors', {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'fg_secondary': '#b0b0b0',
            'fg_good': '#228B22',
            'fg_warning': '#FFA500',
            'fg_yellow': '#FFD700',
            'fg_bad': '#FF6B9D',
            'button_bg': '#0d47a1',
            'button_fg': '#ffffff'
        })
        
        self.setWindowTitle(f"Node Details: {node_id}")
        self.setMinimumSize(420, 650)
        self.setModal(True)
        
        self._apply_dark_theme()
        self._create_ui()
        
        # Position relative to parent
        if parent:
            parent_geo = parent.geometry()
            self.move(parent_geo.x() + 50, parent_geo.y() + 50)
    
    def _apply_dark_theme(self):
        """Apply dark theme colors"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['bg_main']};
            }}
            QLabel {{
                color: {self.colors['fg_normal']};
            }}
            QFrame {{
                background-color: {self.colors['bg_frame']};
                border-radius: 4px;
            }}
            QScrollArea {{
                background-color: {self.colors['bg_main']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['bg_frame']};
                width: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #555555;
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #777777;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QPushButton {{
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12pt;
                border: none;
            }}
        """)
    
    def _create_ui(self):
        """Create the main UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Button bar at top
        self._create_button_bar(layout)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(6)
        
        # Add sections
        self._create_header(content_layout)
        self._create_general_info(content_layout)
        self._create_environmental_section(content_layout)
        self._create_device_telemetry(content_layout)
        self._create_motion_section(content_layout)
        self._create_messages_section(content_layout)
        
        # Add stretch to push content to top
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # Bottom bar with Forget Node (destructive action on left)
        self._create_bottom_bar(layout)
    
    def _create_bottom_bar(self, parent_layout):
        """Create bottom bar with Forget Node button"""
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(f"background-color: {self.colors['bg_frame']}; padding: 6px;")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(6, 6, 6, 6)
        
        # Forget Node button (left side - destructive action)
        forget_btn = create_button("Forget Node", "danger", self._forget_node)
        bottom_layout.addWidget(forget_btn)
        
        bottom_layout.addStretch()
        
        parent_layout.addWidget(bottom_frame)
    
    def _create_button_bar(self, parent_layout):
        """Create button bar at top - single row: Plot, CSV, Logs, Close"""
        button_frame = QFrame()
        button_frame.setStyleSheet(f"background-color: {self.colors['bg_frame']}; padding: 6px;")
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(6, 6, 6, 6)
        button_layout.setSpacing(6)
        
        # Plot button (blue - primary, matches main window)
        if self.on_plot:
            plot_btn = create_button("Plot", "primary", self.on_plot)
            button_layout.addWidget(plot_btn)
        
        # CSV button (blue - primary)
        if self.on_csv:
            csv_btn = create_button("CSV", "primary", self.on_csv)
            button_layout.addWidget(csv_btn)
        
        # Logs button (blue - primary)
        if self.on_logs:
            logs_btn = create_button("Logs", "primary", self.on_logs)
            button_layout.addWidget(logs_btn)
        
        button_layout.addStretch()
        
        # Close button (gray - dismissive, right side)
        close_btn = create_close_button(self.close)
        button_layout.addWidget(close_btn)
        
        parent_layout.addWidget(button_frame)
    
    def _create_header(self, parent_layout):
        """Create header with node name and ID"""
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {self.colors['bg_frame']}; padding: 4px;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 4, 10, 4)
        header_layout.setSpacing(2)
        
        # Node name
        name = self.node_data.get('Node LongName', 'Unknown')
        name_label = QLabel(name)
        name_label.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(name_label)
        
        # Node ID and short name
        short_name = self.node_data.get('Node ShortName', 'N/A')
        id_label = QLabel(f"{self.node_id} ({short_name})")
        id_label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt;")
        header_layout.addWidget(id_label)
        
        parent_layout.addWidget(header_frame)
    
    def _create_section(self, parent_layout, title: str) -> QVBoxLayout:
        """Create a section with title and return content layout"""
        # Section title (outside frame)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 12pt; font-weight: bold; background: transparent;")
        parent_layout.addWidget(title_label)
        
        # Content frame
        content_frame = QFrame()
        content_frame.setStyleSheet(f"background-color: {self.colors['bg_frame']}; padding: 4px;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(8, 4, 8, 4)
        content_layout.setSpacing(2)
        
        parent_layout.addWidget(content_frame)
        
        return content_layout
    
    def _add_info_row(self, layout, label_text: str, value_text: str, value_color: str = None):
        """Add an info row with label and value"""
        if value_color is None:
            value_color = self.colors['fg_normal']
        
        row = QHBoxLayout()
        row.setSpacing(8)
        
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt; background: transparent;")
        label.setMinimumWidth(120)
        row.addWidget(label)
        
        value = QLabel(value_text)
        value.setStyleSheet(f"color: {value_color}; font-size: 12pt; background: transparent;")
        row.addWidget(value)
        row.addStretch()
        
        layout.addLayout(row)
    
    def _add_subsection_header(self, layout, text: str):
        """Add a subsection header"""
        label = QLabel(text)
        label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt; font-style: italic; background: transparent;")
        layout.addWidget(label)
    
    def _create_general_info(self, parent_layout):
        """Create general info section"""
        content_layout = self._create_section(parent_layout, "General Information")
        
        # Status
        last_heard = self.node_data.get('Last Heard', 0)
        time_since_heard = time.time() - last_heard if last_heard else float('inf')
        stale_threshold = 960  # 16 minutes
        
        if time_since_heard < stale_threshold:
            status = "Online"
            status_color = self.colors['fg_good']
        else:
            status = "Offline"
            status_color = self.colors['fg_bad']
        
        self._add_info_row(content_layout, "Status:", status, status_color)
        
        # Last heard
        if last_heard:
            heard_dt = datetime.fromtimestamp(last_heard)
            heard_str = heard_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            heard_str = "Never"
        self._add_info_row(content_layout, "Last Heard:", heard_str)
        
        # Hardware model
        hw_model = self.node_data.get('Hardware Model', 'Unknown')
        self._add_info_row(content_layout, "Hardware:", hw_model)
        
        # Uptime
        uptime_seconds = self.node_data.get('Uptime')
        if uptime_seconds:
            uptime_str = self._format_uptime(uptime_seconds)
            self._add_info_row(content_layout, "Uptime:", uptime_str)
    
    def _create_environmental_section(self, parent_layout):
        """Create environmental telemetry section"""
        has_env = any([
            self.node_data.get('Temperature') is not None,
            self.node_data.get('Humidity') is not None,
            self.node_data.get('Pressure') is not None
        ])
        
        if not has_env:
            return
        
        content_layout = self._create_section(parent_layout, "Environmental Telemetry")
        
        # Temperature
        temp = self.node_data.get('Temperature')
        if temp is not None:
            temp_text = f"{temp:.1f}°C"
            temp_color = self._get_temp_color(temp)
            self._add_info_row(content_layout, "Temperature:", temp_text, temp_color)
        
        # Humidity
        humidity = self.node_data.get('Humidity')
        if humidity is not None:
            humidity_text = f"{humidity:.1f}%"
            humidity_color = self._get_humidity_color(humidity)
            self._add_info_row(content_layout, "Humidity:", humidity_text, humidity_color)
        
        # Pressure
        pressure = self.node_data.get('Pressure')
        if pressure is not None:
            pressure_text = f"{pressure:.1f} hPa"
            self._add_info_row(content_layout, "Pressure:", pressure_text)
    
    def _create_device_telemetry(self, parent_layout):
        """Create device telemetry section"""
        content_layout = self._create_section(parent_layout, "Device Telemetry")
        
        # === Meshtastic Internal Battery ===
        internal_battery = self.node_data.get('Battery Level')
        internal_voltage = self.node_data.get('Internal Battery Voltage')
        
        if internal_battery is not None or internal_voltage is not None:
            self._add_subsection_header(content_layout, "Meshtastic Internal Battery:")
            
            if internal_battery is not None:
                battery_text = f"{internal_battery}%"
                battery_color = self._get_battery_color(internal_battery)
                self._add_info_row(content_layout, "  Charge:", battery_text, battery_color)
            
            if internal_voltage is not None:
                voltage_text = f"{internal_voltage:.2f}V"
                self._add_info_row(content_layout, "  Voltage:", voltage_text)
        
        # === ICP Main Battery (External via Ch3) ===
        ch3_voltage = self.node_data.get('Ch3 Voltage')
        ch3_current = self.node_data.get('Ch3 Current')
        
        if ch3_voltage is not None or ch3_current is not None:
            self._add_subsection_header(content_layout, "Main System Battery:")
            
            # Calculate percentage from voltage
            if ch3_voltage is not None and self.data_collector:
                battery_pct = self.data_collector.voltage_to_percentage(ch3_voltage)
                if battery_pct is not None:
                    pct_text = f"{battery_pct}%"
                    pct_color = self._get_battery_color(battery_pct)
                    self._add_info_row(content_layout, "  Charge:", pct_text, pct_color)
            
            if ch3_voltage is not None:
                ch3_text = f"{ch3_voltage:.2f}V"
                voltage_color = self._get_voltage_color(ch3_voltage)
                self._add_info_row(content_layout, "  Voltage:", ch3_text, voltage_color)
            
            if ch3_current is not None:
                current_text = f"{ch3_current:.0f}mA"
                self._add_info_row(content_layout, "  Current:", current_text)
        
        # Channel Utilization
        channel_util = self.node_data.get('Channel Utilization')
        if channel_util is not None:
            util_text = f"{channel_util:.1f}%"
            self._add_info_row(content_layout, "Ch. Utilization:", util_text)
        
        # SNR
        snr = self.node_data.get('SNR')
        if snr is not None:
            snr_text = f"{snr:.1f} dB"
            snr_color = self._get_snr_color(snr)
        else:
            snr_text = "N/A"
            snr_color = self.colors['fg_secondary']
        self._add_info_row(content_layout, "SNR:", snr_text, snr_color)
        
        # Legacy voltage field
        voltage = self.node_data.get('Voltage')
        if voltage is not None and internal_voltage is None:
            voltage_text = f"{voltage:.2f}V"
            voltage_color = self._get_voltage_color(voltage)
            self._add_info_row(content_layout, "Voltage:", voltage_text, voltage_color)
    
    def _create_motion_section(self, parent_layout):
        """Create motion detection section"""
        last_motion = self.node_data.get('Last Motion')
        if last_motion is None:
            return
        
        content_layout = self._create_section(parent_layout, "Motion Detection")
        
        motion_dt = datetime.fromtimestamp(last_motion)
        motion_str = motion_dt.strftime('%Y-%m-%d %H:%M:%S')
        self._add_info_row(content_layout, "Last Motion:", motion_str)
    
    def _create_messages_section(self, parent_layout):
        """Create messages section showing last 5 messages"""
        if not self.data_collector:
            return
        
        messages = self.data_collector.get_node_messages(self.node_id, limit=5)
        if not messages:
            return
        
        content_layout = self._create_section(parent_layout, "Recent Messages")
        
        # Get nodes data for name lookup
        nodes_data = self.data_collector.get_nodes_data()
        
        for msg in reversed(messages):
            # Message container
            msg_frame = QFrame()
            msg_frame.setStyleSheet(f"background-color: {self.colors['bg_frame']}; padding: 4px;")
            msg_layout = QVBoxLayout(msg_frame)
            msg_layout.setContentsMargins(0, 4, 0, 4)
            msg_layout.setSpacing(2)
            
            # Header: From and timestamp
            from_id = msg.get('from')
            from_node = nodes_data.get(from_id, {})
            from_name = from_node.get('Node LongName', from_id)
            
            timestamp = msg.get('timestamp', 0)
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime('%m-%d %H:%M')
            
            header_label = QLabel(f"From {from_name} at {time_str}")
            header_label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 11pt; background: transparent;")
            msg_layout.addWidget(header_label)
            
            # Message text
            text = msg.get('text', '')
            text_label = QLabel(text)
            text_label.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 12pt; background: transparent; padding-left: 10px;")
            text_label.setWordWrap(True)
            msg_layout.addWidget(text_label)
            
            content_layout.addWidget(msg_frame)
    
    def _forget_node(self):
        """Forget (remove) this node from the system"""
        node_name = self.node_data.get('Node LongName', self.node_id)
        
        # Confirmation dialog
        response = QMessageBox.question(
            self,
            "Forget Node",
            f"Forget node '{node_name}' ({self.node_id})?\n\n"
            "This will:\n"
            "• Remove all node data from the dashboard\n"
            "• Clear alerts for this node\n"
            "• Keep CSV logs (unless deleted manually)\n\n"
            "This cannot be undone. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if response == QMessageBox.Yes:
            # Ask about deleting logs
            delete_logs = QMessageBox.question(
                self,
                "Delete Logs?",
                f"Also delete CSV log files for '{node_name}'?\n\n"
                "If you select No, logs will be preserved\n"
                "and can be accessed manually.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            ) == QMessageBox.Yes
            
            # Call data_collector to forget the node
            if self.data_collector:
                success = self.data_collector.forget_node(self.node_id, delete_logs)
                
                if success:
                    QMessageBox.information(self, "Node Forgotten", f"Node '{node_name}' has been removed.")
                    self.close()
                else:
                    QMessageBox.critical(self, "Error", f"Failed to forget node '{node_name}'.")
            else:
                QMessageBox.critical(self, "Error", "Data collector not available.")
    
    # === Color helper methods ===
    
    def _get_battery_color(self, battery):
        """Get color for battery level"""
        if battery > 50:
            return self.colors['fg_good']
        elif battery >= 25:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_bad']
    
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
        if temp > 45 or temp < 0:
            return self.colors['fg_bad']
        elif temp > 35:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_good']
    
    def _get_humidity_color(self, humidity):
        """Get color for humidity"""
        if humidity < 20 or humidity > 60:
            return self.colors['fg_warning']
        else:
            return self.colors['fg_good']
    
    def _get_snr_color(self, snr):
        """Get color for SNR"""
        if snr > 5:
            return self.colors['fg_good']
        elif snr >= -10:
            return self.colors.get('fg_yellow', '#FFD700')
        else:
            return self.colors['fg_bad']
    
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


# Test harness for standalone testing
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Mock data for testing
    mock_node_data = {
        'Node LongName': 'Test Node',
        'Node ShortName': 'TST',
        'Hardware Model': 'TLORA_V2_1_1P6',
        'Last Heard': time.time() - 300,  # 5 minutes ago
        'Uptime': 86400 + 3600 + 120,  # 1d 1h 2m
        'Temperature': 28.5,
        'Humidity': 45.2,
        'Pressure': 1013.25,
        'Battery Level': 75,
        'Internal Battery Voltage': 4.12,
        'Ch3 Voltage': 12.8,
        'Ch3 Current': 150,
        'Channel Utilization': 12.5,
        'SNR': 8.5,
    }
    
    def mock_logs():
        print("Logs button clicked")
    
    def mock_csv():
        print("CSV button clicked")
    
    def mock_plot():
        print("Plot button clicked")
    
    window = NodeDetailWindowQt(
        None, 
        "!a20a0de0", 
        mock_node_data,
        on_logs=mock_logs,
        on_csv=mock_csv,
        on_plot=mock_plot,
        data_collector=None
    )
    window.show()
    
    sys.exit(app.exec())

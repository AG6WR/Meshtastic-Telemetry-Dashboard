#!/usr/bin/env python3
"""
Node Alert Configuration Dialog (Qt/PySide6)
Per-node telemetry alert enable/disable settings

This dialog allows users to configure which alerts are enabled for each node.
Useful for disabling alerts on nodes that don't report certain telemetry.

Usage:
    from node_alert_config_qt import NodeAlertConfigDialogQt
    
    dialog = NodeAlertConfigDialogQt(
        nodes_data=nodes_dict,
        config_manager=config_mgr,
        parent=main_window
    )
    if dialog.exec() == QDialog.Accepted:
        settings = dialog.get_settings()
"""

import sys
import os
import json
import logging
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox,
    QScrollArea, QWidget, QFrame, QGridLayout, QPushButton,
    QApplication, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from qt_styles import (COLORS, FONTS, get_font, create_button, 
                       create_ok_button, create_cancel_button,
                       CHECKBOX_STYLE, GROUPBOX_STYLE)

logger = logging.getLogger(__name__)


class NodeAlertConfigDialogQt(QDialog):
    """Dialog for configuring per-node alert settings"""
    
    # Alert types that can be configured per node
    # Format: (key, label, threshold_key, unit, low_high)
    ALERT_TYPES = [
        ("low_voltage", "Low Voltage", "alerts.voltage_threshold", "V", "low"),
        ("high_voltage", "High Voltage", "alerts.voltage_high_threshold", "V", "high"),
        ("low_temp", "Low Temperature", "alerts.temp_low_threshold", "°", "low"),
        ("high_temp", "High Temperature", "alerts.temp_threshold", "°", "high"),
        ("motion", "Motion Detected", None, None, None),
        ("offline", "Node Offline", "alerts.offline_threshold", "min", None),
    ]
    
    def __init__(self, nodes_data: Dict[str, Dict], 
                 config_manager=None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.nodes_data = nodes_data
        self.config_manager = config_manager
        self.checkbox_vars: Dict[str, Dict[str, QCheckBox]] = {}
        self._result: Optional[Dict] = None
        
        self._setup_dialog()
        self._setup_ui()
        self._load_settings()
    
    def _setup_dialog(self):
        """Configure dialog properties"""
        self.setWindowTitle("Node Alert Configuration")
        self.setMinimumSize(650, 500)
        self.resize(700, 550)
        
        # Dark theme using standard styles
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_main']};
            }}
            QLabel {{
                color: {COLORS['fg_normal']};
            }}
            {GROUPBOX_STYLE}
            {CHECKBOX_STYLE}
            QScrollArea {{
                background-color: {COLORS['bg_main']};
                border: none;
            }}
            QScrollBar:vertical {{
                width: 20px;
                background: {COLORS['bg_frame']};
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['fg_secondary']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def _setup_ui(self):
        """Build the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Configure Node Alert Settings")
        title.setFont(get_font('card_title'))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Enable or disable specific alert types for each node."
        )
        instructions.setFont(get_font('ui_body'))
        instructions.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        
        # Scrollable node list
        self._create_node_list(layout)
        
        # Buttons
        self._create_buttons(layout)
    
    def _get_threshold_display(self, alert_key: str) -> str:
        """Get threshold display string for an alert type"""
        for key, label, threshold_key, unit, low_high in self.ALERT_TYPES:
            if key == alert_key and threshold_key and self.config_manager:
                try:
                    value = self.config_manager.get(threshold_key)
                    if value is not None:
                        if low_high == "low":
                            return f"< {value}{unit}"
                        elif low_high == "high":
                            return f"> {value}{unit}"
                        else:
                            return f"{value}{unit}"
                except:
                    pass
        return ""
    
    def _has_telemetry_data(self, node_data: Dict, alert_key: str) -> bool:
        """Check if a node has telemetry data for a specific alert type"""
        if alert_key in ("low_voltage", "high_voltage"):
            ch3_v = node_data.get('Ch3 Voltage')
            main_v = node_data.get('Voltage')
            return (ch3_v is not None and ch3_v != 0) or (main_v is not None and main_v != 0)
        
        elif alert_key in ("low_temp", "high_temp"):
            temp = node_data.get('Temperature')
            return temp is not None
        
        elif alert_key == "motion":
            # Motion is detected via accelerometer or position changes
            last_motion = node_data.get('Last Motion')
            return last_motion is not None
        
        elif alert_key == "offline":
            # Offline alerts always available if we've seen the node
            return True
        
        return True
    
    def _create_node_list(self, parent_layout: QVBoxLayout):
        """Create scrollable list of nodes with checkboxes"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        container.setObjectName("nodeAlertContainer")
        container.setStyleSheet(f"QWidget#nodeAlertContainer {{ background-color: {COLORS['bg_main']}; }}")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        container_layout.setSpacing(10)
        
        # Create a row for each node
        for node_id, node_data in self.nodes_data.items():
            self._create_node_row(container_layout, node_id, node_data)
        
        container_layout.addStretch()
        scroll_area.setWidget(container)
        parent_layout.addWidget(scroll_area, stretch=1)
    
    def _create_node_row(self, parent_layout: QVBoxLayout, node_id: str, node_data: Dict):
        """Create a row for one node's settings"""
        node_name = node_data.get('Node LongName', 'Unknown')
        short_name = node_data.get('Node ShortName', 'Unk')
        
        # Group box for node
        group = QGroupBox(f"{node_name} ({short_name})")
        group.setFont(get_font('ui_body'))
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 15, 10, 10)
        group_layout.setSpacing(6)
        
        # Checkboxes in a grid (3 columns x 2 rows)
        checkbox_widget = QWidget()
        checkbox_widget.setStyleSheet(f"background-color: transparent;")
        checkbox_layout = QGridLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setHorizontalSpacing(15)
        checkbox_layout.setVerticalSpacing(4)
        
        self.checkbox_vars[node_id] = {}
        
        for i, (alert_key, label, threshold_key, unit, low_high) in enumerate(self.ALERT_TYPES):
            row = i // 3
            col = i % 3
            
            # Container for checkbox + threshold note
            cell_widget = QWidget()
            cell_layout = QVBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(1)
            
            # Check if node has data for this alert type
            has_data = self._has_telemetry_data(node_data, alert_key)
            
            # Checkbox
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)  # Default enabled
            checkbox.setEnabled(has_data)
            
            # For disabled checkboxes, install event filter to show dialog on click
            if not has_data:
                checkbox.installEventFilter(self)
                checkbox.setProperty("alert_key", alert_key)
                checkbox.setProperty("node_name", node_name)
            
            cell_layout.addWidget(checkbox)
            
            self.checkbox_vars[node_id][alert_key] = checkbox
            
            # Threshold note (only if data available)
            if has_data:
                threshold_text = self._get_threshold_display(alert_key)
                if threshold_text:
                    note = QLabel(threshold_text)
                    note.setFont(get_font('ui_notes'))
                    note.setStyleSheet(f"color: {COLORS['fg_secondary']}; margin-left: 28px;")
                    cell_layout.addWidget(note)
            
            checkbox_layout.addWidget(cell_widget, row, col)
        
        group_layout.addWidget(checkbox_widget)
        parent_layout.addWidget(group)
    
    def _create_buttons(self, parent_layout: QVBoxLayout):
        """Create action buttons"""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(10)
        
        # Left side - Enable All and Disable All buttons
        btn_enable_all = create_button("Enable All", "success")
        btn_enable_all.clicked.connect(self._enable_all_alerts)
        button_layout.addWidget(btn_enable_all)
        
        btn_disable_all = create_button("Disable All", "warning")
        btn_disable_all.clicked.connect(self._disable_all_alerts)
        button_layout.addWidget(btn_disable_all)
        
        button_layout.addStretch()
        
        # Right side - Save then Cancel (Cancel on far right per UI standard)
        btn_save = create_ok_button(self._save_settings)
        btn_save.setText("Save")
        button_layout.addWidget(btn_save)
        
        btn_cancel = create_cancel_button(self.reject)
        button_layout.addWidget(btn_cancel)
        
        parent_layout.addWidget(button_widget)
    
    def _load_settings(self):
        """Load existing settings from file"""
        try:
            settings_path = 'config/node_alert_settings.json'
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Apply loaded settings
                for node_id, node_settings in settings.items():
                    if node_id in self.checkbox_vars:
                        for alert_type, enabled in node_settings.items():
                            if alert_type in self.checkbox_vars[node_id]:
                                checkbox = self.checkbox_vars[node_id][alert_type]
                                if checkbox.isEnabled():  # Only set if not disabled
                                    checkbox.setChecked(enabled)
        except Exception as e:
            logger.error(f"Error loading alert settings: {e}")
    
    def _enable_all_alerts(self):
        """Enable all alerts for all nodes (where data is available)"""
        for node_vars in self.checkbox_vars.values():
            for checkbox in node_vars.values():
                if checkbox.isEnabled():
                    checkbox.setChecked(True)
    
    def _disable_all_alerts(self):
        """Disable all alerts for all nodes"""
        for node_vars in self.checkbox_vars.values():
            for checkbox in node_vars.values():
                if checkbox.isEnabled():
                    checkbox.setChecked(False)
    
    def eventFilter(self, obj, event):
        """Handle clicks on disabled checkboxes to show info dialog"""
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.MouseButtonPress:
            if isinstance(obj, QCheckBox) and not obj.isEnabled():
                alert_key = obj.property("alert_key")
                node_name = obj.property("node_name")
                
                # Get friendly alert name
                alert_name = alert_key.replace("_", " ").title()
                
                QMessageBox.information(
                    self,
                    "No Data Available",
                    f"'{alert_name}' alerts are not available for {node_name} "
                    f"because this node has not reported the required telemetry data."
                )
                return True
        return super().eventFilter(obj, event)
    
    def _save_settings(self):
        """Save settings and close dialog"""
        # Collect settings from checkboxes
        settings = {}
        for node_id, node_checkboxes in self.checkbox_vars.items():
            settings[node_id] = {}
            for alert_type, checkbox in node_checkboxes.items():
                # Save enabled state (False for disabled checkboxes)
                settings[node_id][alert_type] = checkbox.isChecked() if checkbox.isEnabled() else False
        
        # Save to file
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/node_alert_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            logger.info("Alert settings saved")
        except Exception as e:
            logger.error(f"Error saving alert settings: {e}")
            QMessageBox.warning(
                self,
                "Save Error",
                f"Failed to save settings: {e}"
            )
            return
        
        self._result = settings
        self.accept()
    
    def get_settings(self) -> Optional[Dict]:
        """Get the saved settings (after dialog closes)"""
        return self._result


# =============================================================================
# Standalone Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    # Sample node data for testing
    sample_nodes = {
        '!a20a0de0': {
            'node_id': '!a20a0de0',
            'Node LongName': 'AG6WR-Home',
            'Node ShortName': 'HOME',
            'Last Heard': 1702800000,
            'Ch3 Voltage': 12.8,
            'Temperature': 28.5,
            'Last Motion': 1702799000,
        },
        '!a20a0fb0': {
            'node_id': '!a20a0fb0',
            'Node LongName': 'AG6WR-Mobile',
            'Node ShortName': 'MOBL',
            'Last Heard': 1702800000,
            'Ch3 Voltage': 11.2,
            'Temperature': 35.2,
        },
        '!2f1b9773': {
            'node_id': '!2f1b9773',
            'Node LongName': 'Remote Station',
            'Node ShortName': 'REMT',
            'Last Heard': 1702800000,
            # No voltage, no motion
            'Temperature': 22.0,
        },
    }
    
    dialog = NodeAlertConfigDialogQt(nodes_data=sample_nodes)
    result = dialog.exec()
    
    if result == QDialog.Accepted:
        print("Settings saved:", dialog.get_settings())
    else:
        print("Cancelled")
    
    sys.exit(0)

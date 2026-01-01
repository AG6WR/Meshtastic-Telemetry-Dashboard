"""
Card Renderer (Qt/PySide6) - Node card widget for dashboard display

This module provides the NodeCardQt class, a self-contained QFrame widget
that displays telemetry data for a single Meshtastic node in a compact card format.

Card Layout:
┌─────────────────────────────────────────────────────────────────┐
│ [Node Name]                                    [Online/Offline] │  Header
├─────────────────────────────────────────────────────────────────┤
│ [✉ MSG] From: message preview... OR Last: 12-17 14:30 OR Motion │  Line 2 (status)
├─────────────────────────────────────────────────────────────────┤
│ ⚡ ICP Batt:80%   +2.5mA ⬆          ⚡ Node Batt:100%           │  Row 1 (batteries)
├─────────────────────────────────────────────────────────────────┤
│ SNR:||||          Ch:45.2%                     Air:12.3%        │  Row 2 (radio)
├─────────────────────────────────────────────────────────────────┤
│ 72°F              Humidity:54%                 1013.2 hPa       │  Row 3 (environment)
└─────────────────────────────────────────────────────────────────┘

Usage:
    from card_renderer_qt import NodeCardQt
    
    card = NodeCardQt(node_id="!a20a0de0", node_data=data_dict, parent=container)
    card.clicked.connect(on_card_clicked)
    card.context_menu_requested.connect(on_context_menu)
    
    # Update card with new data
    card.update_data(new_data_dict)
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QMouseEvent

from qt_styles import (
    COLORS, get_font, get_font_style,
    create_battery_bar, create_snr_bar, create_utilization_bar
)
from formatters import (
    convert_temperature, format_temperature, get_temperature_color,
    scale_current, format_current, get_current_color
)

logger = logging.getLogger(__name__)


class StatusIndicator(QLabel):
    """
    A status indicator widget that can display ICP status with optional blinking.
    
    States:
        - Online (green): Normal operation, no blink
        - Warning (yellow): Degraded status, slow blink
        - Critical (red): Problem detected, fast blink
        - Help (red): SEND HELP active, fast blink
        - Offline (grey): Node offline, no blink
    
    The indicator is clickable and emits a signal when clicked to show status details.
    """
    
    clicked = Signal()  # Emitted when indicator is clicked
    
    # Status colors
    STATUS_COLORS = {
        'green': '#00ff00',     # Good/Online
        'yellow': '#ffff00',    # Warning/Degraded  
        'red': '#ff4444',       # Critical/Help
        'grey': '#808080',      # Offline/Unknown
    }
    
    # Blink intervals (ms)
    BLINK_FAST = 300    # Critical/Help status
    BLINK_SLOW = 800    # Warning status
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._status = "Offline"
        self._color = self.STATUS_COLORS['grey']
        self._reasons: List[str] = []
        self._help_active = False
        self._blink_enabled = False
        self._blink_visible = True
        self._blink_timer: Optional[QTimer] = None
        
        # Configure appearance
        self.setFont(get_font('card_header'))
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
        
    def set_status(self, status: str, color: str = 'grey', 
                   reasons: Optional[List[str]] = None,
                   help_active: bool = False,
                   blink: bool = False,
                   blink_fast: bool = False):
        """
        Update the status indicator.
        
        Args:
            status: Status text to display (e.g., "Online", "Warning", "HELP")
            color: Color key ('green', 'yellow', 'red', 'grey')
            reasons: List of reasons for current status
            help_active: Whether SEND HELP is active
            blink: Whether to enable blinking
            blink_fast: Use fast blink (True) or slow blink (False)
        """
        self._status = status
        self._color = self.STATUS_COLORS.get(color, self.STATUS_COLORS['grey'])
        self._reasons = reasons or []
        self._help_active = help_active
        
        # Update text
        self.setText(status)
        
        # Handle blinking
        if blink and not self._blink_enabled:
            self._start_blink(fast=blink_fast)
        elif not blink and self._blink_enabled:
            self._stop_blink()
        elif blink and self._blink_enabled:
            # Update blink speed if needed
            interval = self.BLINK_FAST if blink_fast else self.BLINK_SLOW
            if self._blink_timer and self._blink_timer.interval() != interval:
                self._blink_timer.setInterval(interval)
        
        self._update_style()
        
    def set_online_offline(self, is_online: bool):
        """Simple online/offline status (legacy compatibility)"""
        if is_online:
            self.set_status("Online", color='green', blink=False)
        else:
            self.set_status("Offline", color='grey', blink=False)
            
    def _start_blink(self, fast: bool = False):
        """Start blinking animation"""
        self._blink_enabled = True
        self._blink_visible = True
        
        if self._blink_timer is None:
            self._blink_timer = QTimer(self)
            self._blink_timer.timeout.connect(self._on_blink)
        
        interval = self.BLINK_FAST if fast else self.BLINK_SLOW
        self._blink_timer.start(interval)
        
    def _stop_blink(self):
        """Stop blinking animation"""
        self._blink_enabled = False
        self._blink_visible = True
        
        if self._blink_timer:
            self._blink_timer.stop()
            
        self._update_style()
        
    def _on_blink(self):
        """Toggle blink visibility"""
        self._blink_visible = not self._blink_visible
        self._update_style()
        
    def _update_style(self):
        """Update the label styling"""
        if self._blink_enabled and not self._blink_visible:
            # Blink "off" state - dim the color
            color = '#404040'  # Dark grey when "off"
        else:
            color = self._color
            
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: transparent;
                padding: 0px 4px;
            }}
        """)
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle click to show status details"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
        
    def get_tooltip_text(self) -> str:
        """Get tooltip text with status details"""
        lines = [f"Status: {self._status}"]
        if self._reasons:
            lines.append("Reasons:")
            for reason in self._reasons:
                lines.append(f"  • {reason}")
        if self._help_active:
            lines.append("")
            lines.append("⚠ SEND HELP is active!")
        return "\n".join(lines)


class NodeCardQt(QFrame):
    """
    Qt widget representing a single node's telemetry card.
    
    Signals:
        clicked(str): Emitted when card is clicked, with node_id
        context_menu_requested(str, QPoint): Emitted for right-click, with node_id and position
    """
    
    clicked = Signal(str)  # node_id
    context_menu_requested = Signal(str, object)  # node_id, QPoint
    
    # Card dimensions (narrowed ~20% for better fit)
    CARD_WIDTH = 368
    CARD_HEIGHT = 140
    
    # Thresholds
    ONLINE_THRESHOLD_SECONDS = 960  # 16 minutes
    MOTION_DISPLAY_SECONDS = 900    # 15 minutes default
    
    def __init__(self, node_id: str, node_data: Dict[str, Any], 
                 is_local: bool = False,
                 unread_messages: Optional[List[Dict]] = None,
                 config_manager=None,
                 data_collector=None,
                 parent: Optional[QWidget] = None):
        """
        Create a node card widget.
        
        Args:
            node_id: Node ID (e.g., "!a20a0de0")
            node_data: Dictionary containing node telemetry data
            is_local: Whether this is the local node (gets green background)
            unread_messages: List of unread message dicts for this node
            config_manager: ConfigManager instance for settings
            data_collector: DataCollector instance for voltage conversion
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.node_id = node_id
        self.node_data = node_data
        self.is_local = is_local
        self.unread_messages = unread_messages or []
        self.config_manager = config_manager
        self.data_collector = data_collector
        
        # Flash state for data change indication
        self._flash_active = False
        self._flash_timer: Optional[QTimer] = None
        self._message_flash_state = True  # For message indicator alternation
        
        # Widget references for updates
        self._widgets: Dict[str, QWidget] = {}
        
        # Cache telemetry field visibility settings - DISABLED for now
        # self._telemetry_fields = self._get_telemetry_field_settings()
        
        # Colors
        self.colors = COLORS.copy()
        self.colors['bg_local_node'] = '#1e3d1e'    # Dark green tint for home node
        self.colors['bg_message'] = '#1e2d3d'      # Dark blue tint for pending messages
        self.colors['bg_message_alt'] = '#1e3d2d'  # Blue-green tint for flash alternate
        self.colors['bg_stale'] = '#3d2d2d'        # Reddish tint for stale
        self.colors['border_normal'] = '#404040'   # Subtle border for all cards
        
        # Setup UI
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the card UI"""
        # Card frame styling - use background colors for status indication
        bg_color = self._get_background_color()
        
        self.setStyleSheet(f"""
            NodeCardQt {{
                background-color: {bg_color};
                border: 1px solid {self.colors['border_normal']};
                border-radius: 4px;
            }}
        """)
        self.setFixedWidth(self.CARD_WIDTH)
        self.setMinimumHeight(self.CARD_HEIGHT)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(1)
        
        # Create card sections
        self._create_header(layout)
        self._create_status_line(layout)
        self._create_battery_row(layout)
        self._create_radio_row(layout)
        self._create_environment_row(layout)
        
    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header with node name and status"""
        header = QWidget()
        header.setFixedHeight(22)  # Compact header height
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        bg_color = self.colors['bg_local_node'] if self.is_local else self.colors['bg_frame']
        
        # Node name (left)
        long_name = self.node_data.get('Node LongName', 'Unknown')
        display_name = long_name.replace("AG6WR-", "") if long_name.startswith("AG6WR-") else long_name
        
        self._widgets['name_label'] = QLabel(display_name)
        self._widgets['name_label'].setFont(get_font('card_header'))
        self._widgets['name_label'].setStyleSheet(f"color: {self.colors['fg_normal']}; background: transparent;")
        header_layout.addWidget(self._widgets['name_label'])
        
        header_layout.addStretch()
        
        # Status indicator (right) - uses StatusIndicator for ICP status support
        self._widgets['status_indicator'] = StatusIndicator()
        is_online = self._is_node_online()
        self._widgets['status_indicator'].set_online_offline(is_online)
        header_layout.addWidget(self._widgets['status_indicator'])
        
        parent_layout.addWidget(header)
        
    def _create_status_line(self, parent_layout: QVBoxLayout):
        """Create line 2: messages, motion detected, or last heard"""
        status_widget = QWidget()
        status_widget.setFixedHeight(18)
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(0)
        
        # Determine what to show (priority: messages > motion > last heard)
        self._widgets['status_line'] = QLabel()
        self._widgets['status_line'].setFont(get_font('card_line2'))
        self._widgets['status_line'].setStyleSheet(f"color: {self.colors['fg_normal']}; background: transparent;")
        
        self._update_status_line()
        
        status_layout.addWidget(self._widgets['status_line'])
        status_layout.addStretch()
        
        parent_layout.addWidget(status_widget)
        
    def _create_battery_row(self, parent_layout: QVBoxLayout):
        """Create Row 1: ICP Batt bar, Current, Node Batt bar (left/center/right)"""
        # Narrowed dimensions for compact card layout
        LABEL_WIDTH = 40
        BAR_WIDTH = 45
        
        row = QWidget()
        row.setFixedHeight(20)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        
        # Column 1: ICP Battery bar (left-aligned, no % value shown)
        self._widgets['icp_batt_bar'] = create_battery_bar(
            value=0, label="⚡ ICP", width=BAR_WIDTH, 
            show_value=False, label_width=LABEL_WIDTH
        )
        row_layout.addWidget(self._widgets['icp_batt_bar'])
        
        row_layout.addStretch()  # Push current to center
        
        # Column 2: Current (centered text)
        self._widgets['current_label'] = QLabel()
        self._widgets['current_label'].setFont(get_font('card_value'))
        self._widgets['current_label'].setStyleSheet(f"color: {self.colors['fg_normal']}; background: transparent;")
        self._widgets['current_label'].setAlignment(Qt.AlignCenter)
        row_layout.addWidget(self._widgets['current_label'])
        
        row_layout.addStretch()  # Push node batt to right
        
        # Column 3: Node Battery bar (right-aligned, no % value shown)
        self._widgets['node_batt_bar'] = create_battery_bar(
            value=0, label="⚡ Node", width=BAR_WIDTH,
            show_value=False, label_width=LABEL_WIDTH
        )
        row_layout.addWidget(self._widgets['node_batt_bar'])
        
        # Right margin spacer
        spacer = QWidget()
        spacer.setFixedWidth(10)
        row_layout.addWidget(spacer)
        
        parent_layout.addWidget(row)
        
        # Update values
        self._update_battery_row()
        
    def _create_radio_row(self, parent_layout: QVBoxLayout):
        """Create Row 2: SNR bar, Channel Util bar, Air Util bar (left/center/right, no values)"""
        # Narrowed dimensions for compact card layout
        LABEL_WIDTH = 40
        BAR_WIDTH = 45
        
        row = QWidget()
        row.setFixedHeight(20)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        
        # Column 1: SNR bar (left-aligned, bar only)
        self._widgets['snr_bar'] = create_snr_bar(
            value=0, label="SNR", width=BAR_WIDTH, 
            show_value=False, label_width=LABEL_WIDTH
        )
        row_layout.addWidget(self._widgets['snr_bar'])
        
        row_layout.addStretch()  # Push channel util to center
        
        # Column 2: Channel Utilization bar (centered, bar only)
        self._widgets['channel_util_bar'] = create_utilization_bar(
            value=0, label="Ch Util", width=BAR_WIDTH, 
            show_value=False, label_width=LABEL_WIDTH
        )
        row_layout.addWidget(self._widgets['channel_util_bar'])
        
        row_layout.addStretch()  # Push air util to right
        
        # Column 3: Air Utilization bar (right-aligned, bar only)
        self._widgets['air_util_bar'] = create_utilization_bar(
            value=0, label="Air Util", width=BAR_WIDTH, 
            show_value=False, label_width=LABEL_WIDTH
        )
        row_layout.addWidget(self._widgets['air_util_bar'])
        
        # Right margin spacer
        spacer = QWidget()
        spacer.setFixedWidth(10)
        row_layout.addWidget(spacer)
        
        parent_layout.addWidget(row)
        
        # Update values
        self._update_radio_row()
        
    def _create_environment_row(self, parent_layout: QVBoxLayout):
        """Create Row 3: Temperature, Pressure, Humidity (left/center/right with labels)"""
        # Narrowed dimensions for compact card layout
        LABEL_WIDTH = 40
        VALUE_WIDTH = 50
        
        row = QWidget()
        row.setFixedHeight(20)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)
        
        # Column 1: Temperature (left-aligned)
        self._widgets['temp_label_text'] = QLabel("Temp:")
        self._widgets['temp_label_text'].setFont(get_font('card_label'))
        self._widgets['temp_label_text'].setStyleSheet(f"color: {self.colors['fg_secondary']}; background: transparent;")
        self._widgets['temp_label_text'].setFixedWidth(LABEL_WIDTH)
        self._widgets['temp_label_text'].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_layout.addWidget(self._widgets['temp_label_text'])
        
        self._widgets['temp_value'] = QLabel()
        self._widgets['temp_value'].setFont(get_font('card_value'))
        self._widgets['temp_value'].setStyleSheet(f"color: {self.colors['fg_normal']}; background: transparent;")
        self._widgets['temp_value'].setFixedWidth(VALUE_WIDTH)
        row_layout.addWidget(self._widgets['temp_value'])
        
        row_layout.addStretch()  # Push pressure to center
        
        # Column 2: Pressure (centered) - wider value for "hPa" suffix
        self._widgets['pres_label_text'] = QLabel("Pres:")
        self._widgets['pres_label_text'].setFont(get_font('card_label'))
        self._widgets['pres_label_text'].setStyleSheet(f"color: {self.colors['fg_secondary']}; background: transparent;")
        self._widgets['pres_label_text'].setFixedWidth(LABEL_WIDTH)
        self._widgets['pres_label_text'].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_layout.addWidget(self._widgets['pres_label_text'])
        
        self._widgets['pres_value'] = QLabel()
        self._widgets['pres_value'].setFont(get_font('card_value'))
        self._widgets['pres_value'].setStyleSheet(f"color: {self.colors['fg_normal']}; background: transparent;")
        # No fixed width - let it auto-size based on content
        row_layout.addWidget(self._widgets['pres_value'])
        
        row_layout.addStretch()  # Push humidity to right
        
        # Column 3: Humidity (right-aligned)
        self._widgets['hum_label_text'] = QLabel("Hum:")
        self._widgets['hum_label_text'].setFont(get_font('card_label'))
        self._widgets['hum_label_text'].setStyleSheet(f"color: {self.colors['fg_secondary']}; background: transparent;")
        self._widgets['hum_label_text'].setFixedWidth(LABEL_WIDTH)
        self._widgets['hum_label_text'].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_layout.addWidget(self._widgets['hum_label_text'])
        
        self._widgets['hum_value'] = QLabel()
        self._widgets['hum_value'].setFont(get_font('card_value'))
        self._widgets['hum_value'].setStyleSheet(f"color: {self.colors['fg_normal']}; background: transparent;")
        self._widgets['hum_value'].setFixedWidth(VALUE_WIDTH)
        row_layout.addWidget(self._widgets['hum_value'])
        
        parent_layout.addWidget(row)
        
        # Update values
        self._update_environment_row()
        
    # =========================================================================
    # Status/Data Helpers
    # =========================================================================
    
    def _get_telemetry_field_settings(self) -> Dict[str, bool]:
        """Get telemetry field visibility settings from config.
        
        Returns:
            Dict mapping field keys to visibility (True = show, False = hide)
        """
        defaults = {
            'voltage': True,
            'temperature': True,
            'humidity': True,
            'pressure': True,
            'battery': True,
            'snr': True,
            'channel_utilization': True,
            'current': True,
            'uptime': True
        }
        if self.config_manager:
            return self.config_manager.get('dashboard.telemetry_fields', defaults)
        return defaults
    
    def _is_field_enabled(self, field_key: str) -> bool:
        """Check if a telemetry field should be displayed.
        
        Args:
            field_key: The config key for the field (e.g., 'temperature', 'snr')
            
        Returns:
            True if the field should be shown, False to hide it
        """
        # DISABLED: Telemetry field visibility feature needs more work
        # return self._telemetry_fields.get(field_key, True)
        return True  # Always show all fields for now
    
    def _is_node_online(self) -> bool:
        """Check if node is online based on last heard time"""
        current_time = time.time()
        last_heard = self.node_data.get('Last Heard', 0)
        time_diff = current_time - last_heard if last_heard else float('inf')
        return time_diff <= self.ONLINE_THRESHOLD_SECONDS
    
    def _get_status(self) -> Tuple[str, str]:
        """Get node status and color based on last heard time (legacy method)"""
        if self._is_node_online():
            return "Online", self.colors['fg_good']
        else:
            return "Offline", self.colors['fg_bad']
    
    def _is_telemetry_stale(self) -> bool:
        """Check if telemetry data is stale (>16 min old)"""
        current_time = time.time()
        last_telemetry = self.node_data.get('Last Telemetry Time', 0)
        if not last_telemetry:
            return True
        return (current_time - last_telemetry) > self.ONLINE_THRESHOLD_SECONDS
    
    def _get_display_color(self, value_color: str) -> str:
        """Get display color, using grey if data is stale"""
        if self._is_telemetry_stale():
            return self.colors['fg_secondary']
        return value_color
    
    def _get_background_color(self) -> str:
        """Get background color based on card state (home, messages, normal)"""
        # Priority 1: Home node (local) - dark green
        if self.is_local:
            # If local node has messages, use alternating color
            if self.unread_messages:
                return self.colors['bg_message_alt'] if self._message_flash_state else self.colors['bg_local_node']
            return self.colors['bg_local_node']
        
        # Priority 2: Has unread messages - dark blue (alternating)
        if self.unread_messages:
            return self.colors['bg_message'] if self._message_flash_state else self.colors['bg_message_alt']
        
        # Default: normal card background
        return self.colors['bg_frame']
    
    # =========================================================================
    # Row Update Methods
    # =========================================================================
    
    def _update_status_line(self):
        """Update line 2 based on priority: messages > motion > last heard (for stale/offline)"""
        label = self._widgets.get('status_line')
        if not label:
            return
            
        # Priority 1: Unread messages - use ✉ mail icon
        if self.unread_messages:
            newest_msg = self.unread_messages[0]
            msg_text = newest_msg.get('text', '')
            msg_text = ''.join(c for c in msg_text if c.isprintable() or c == ' ')
            msg_from = newest_msg.get('from_name', 'Unknown')
            if len(msg_from) > 15:
                msg_from = msg_from.split()[0] if ' ' in msg_from else msg_from[:15]
            preview = msg_text[:40] + '...' if len(msg_text) > 40 else msg_text
            label.setText(f"✉ {msg_from}: {preview}")
            label.setStyleSheet(f"color: {self.colors['accent']}; background: transparent;")
            return
        
        status, _ = self._get_status()
        current_time = time.time()
        is_stale = self._is_telemetry_stale()
        
        # Priority 2: Motion detected (online, non-stale nodes only)
        if status == "Online" and not is_stale:
            last_motion = self.node_data.get('Last Motion')
            if last_motion:
                motion_threshold = self.MOTION_DISPLAY_SECONDS
                if self.config_manager:
                    motion_threshold = self.config_manager.get('dashboard.motion_display_seconds', 900)
                
                if (current_time - last_motion) <= motion_threshold:
                    label.setText("Motion detected")
                    label.setStyleSheet(f"color: {self.colors['fg_good']}; background: transparent;")
                    return
        
        # Priority 3: Last heard (offline nodes OR stale telemetry)
        if status == "Offline" or is_stale:
            last_heard = self.node_data.get('Last Heard')
            if last_heard and last_heard > 0:
                heard_dt = datetime.fromtimestamp(last_heard)
                # Use different colors: orange for stale-but-online, red for offline
                color = self.colors['fg_warning'] if status == "Online" else self.colors['fg_bad']
                label.setText(f"Last Heard: {heard_dt.strftime('%m-%d %H:%M')}")
                label.setStyleSheet(f"color: {color}; background: transparent;")
                return
            else:
                # No Last Heard data - show "Never heard" for offline nodes
                if status == "Offline":
                    label.setText("Last Heard: Never")
                    label.setStyleSheet(f"color: {self.colors['fg_bad']}; background: transparent;")
                    return
        
        # Default: empty
        label.setText("")
    
    def _update_battery_row(self):
        """Update Row 1: ICP Batt bar, Current text, Node Batt bar"""
        is_stale = self._is_telemetry_stale()
        
        # ICP Battery bar (Ch3 Voltage converted to %)
        icp_bar = self._widgets.get('icp_batt_bar')
        if icp_bar:
            ch3_voltage = self.node_data.get('Ch3 Voltage')
            if ch3_voltage is not None and self.data_collector and self._is_field_enabled('voltage'):
                battery_pct = self.data_collector.voltage_to_percentage(ch3_voltage)
                if battery_pct is not None:
                    icp_bar.set_value(battery_pct, stale=is_stale)
                else:
                    icp_bar.set_value(0, stale=True)
            else:
                icp_bar.set_value(0, stale=True)
            icp_bar.setVisible(True)  # Keep visible to preserve column position
        
        # Current (text display with arrow)
        current_label = self._widgets.get('current_label')
        if current_label:
            ch3_current = self.node_data.get('Ch3 Current')
            if ch3_current is not None and self._is_field_enabled('current'):
                # Apply scaling from config (per-node or default)
                scaled_current = scale_current(ch3_current, self.config_manager, self.node_id)
                # Format with auto mA/A units and direction arrow
                current_text = format_current(scaled_current, include_direction=True)
                current_color = get_current_color(scaled_current, self.colors)
                display_color = self.colors['fg_secondary'] if is_stale else current_color
                current_label.setText(current_text)
                current_label.setStyleSheet(f"color: {display_color}; background: transparent;")
            else:
                current_label.setText("")  # Clear but keep visible to preserve column position
            current_label.setVisible(True)
        
        # Node Battery bar
        node_bar = self._widgets.get('node_batt_bar')
        if node_bar:
            battery_level = self.node_data.get('Battery Level')
            if battery_level is not None and self._is_field_enabled('battery'):
                node_bar.set_value(battery_level, stale=is_stale)
            else:
                node_bar.set_value(0, stale=True)
            node_bar.setVisible(True)  # Keep visible to preserve column position
    
    def _update_radio_row(self):
        """Update Row 2: SNR bar, Channel Util bar, Air Util bar"""
        is_stale = self._is_telemetry_stale()
        
        # SNR bar
        snr_bar = self._widgets.get('snr_bar')
        if snr_bar:
            snr = self.node_data.get('SNR')
            if snr is not None and self._is_field_enabled('snr'):
                snr_bar.set_value(snr, stale=is_stale)
            else:
                snr_bar.set_value(0, stale=True)
            snr_bar.setVisible(True)  # Keep visible to preserve column position
        
        # Channel Utilization bar
        ch_bar = self._widgets.get('channel_util_bar')
        if ch_bar:
            channel_util = self.node_data.get('Channel Utilization')
            if channel_util is not None and self._is_field_enabled('channel_utilization'):
                ch_bar.set_value(channel_util, stale=is_stale)
            else:
                ch_bar.set_value(0, stale=True)
            ch_bar.setVisible(True)  # Keep visible to preserve column position
        
        # Air Utilization bar (uses same setting as channel_utilization)
        air_bar = self._widgets.get('air_util_bar')
        if air_bar:
            air_util = self.node_data.get('Air Utilization (TX)')
            if air_util is not None and self._is_field_enabled('channel_utilization'):
                air_bar.set_value(air_util, stale=is_stale)
            else:
                air_bar.set_value(0, stale=True)
            air_bar.setVisible(True)  # Keep visible to preserve column position
    
    def _update_environment_row(self):
        """Update Row 3: Temperature, Humidity, Pressure"""
        is_stale = self._is_telemetry_stale()
        stale_color = self.colors['fg_secondary']
        
        # Temperature
        temp_value_label = self._widgets.get('temp_value')
        if temp_value_label:
            temp = self.node_data.get('Temperature')
            if temp is not None and self._is_field_enabled('temperature'):
                temp_value, temp_unit, _ = convert_temperature(temp, self.config_manager)
                temp_color = get_temperature_color(temp, self.colors, self.config_manager)
                display_color = stale_color if is_stale else temp_color
                temp_value_label.setText(f" {temp_value:.0f}{temp_unit}")
                temp_value_label.setStyleSheet(f"color: {display_color}; background: transparent;")
            else:
                temp_value_label.setText("")
        
        # Humidity
        hum_value_label = self._widgets.get('hum_value')
        if hum_value_label:
            humidity = self.node_data.get('Humidity')
            if humidity is not None and self._is_field_enabled('humidity'):
                if humidity < 20 or humidity > 60:
                    hum_color = self.colors['fg_warning']
                else:
                    hum_color = self.colors['fg_good']
                display_color = stale_color if is_stale else hum_color
                hum_value_label.setText(f" {humidity:.0f}%")
                hum_value_label.setStyleSheet(f"color: {display_color}; background: transparent;")
            else:
                hum_value_label.setText("")
        
        # Pressure
        pres_value_label = self._widgets.get('pres_value')
        if pres_value_label:
            pressure = self.node_data.get('Pressure')
            if pressure is not None and self._is_field_enabled('pressure'):
                display_color = stale_color if is_stale else self.colors['fg_normal']
                pres_value_label.setText(f" {pressure:.1f}hPa")
                pres_value_label.setStyleSheet(f"color: {display_color}; background: transparent;")
            else:
                pres_value_label.setText("")
    
    def _format_rich_text(self, parts: List[Tuple[str, str, str]]) -> str:
        """Format rich text with multiple styled parts.
        
        Args:
            parts: List of (text, color, font_name) tuples
            
        Returns:
            HTML string for QLabel
        """
        html_parts = []
        for text, color, font_name in parts:
            family, size, weight = get_font(font_name).family(), get_font(font_name).pointSize(), get_font(font_name).weight()
            weight_str = "bold" if weight >= 600 else "normal"
            html_parts.append(f'<span style="color:{color}; font-size:{size}pt; font-weight:{weight_str};">{text}</span>')
        return "".join(html_parts)
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def update_data(self, node_data: Dict[str, Any], 
                    unread_messages: Optional[List[Dict]] = None,
                    flash: bool = False):
        """
        Update card with new data.
        
        Args:
            node_data: New node data dictionary
            unread_messages: Updated unread messages list
            flash: Whether to flash the card border for data change
        """
        self.node_data = node_data
        if unread_messages is not None:
            self.unread_messages = unread_messages
        
        # Update status indicator
        is_online = self._is_node_online()
        self._widgets['status_indicator'].set_online_offline(is_online)
        
        # Update name in case it changed
        long_name = self.node_data.get('Node LongName', 'Unknown')
        display_name = long_name.replace("AG6WR-", "") if long_name.startswith("AG6WR-") else long_name
        self._widgets['name_label'].setText(display_name)
        
        self._update_status_line()
        self._update_battery_row()
        self._update_radio_row()
        self._update_environment_row()
        
        if flash:
            self.flash_border()
    
    def flash_border(self, duration_ms: int = 2000):
        """Flash the card background to indicate data change"""
        if self._flash_active:
            return
            
        self._flash_active = True
        
        # Brief flash with lighter background
        flash_bg = '#3d3d4d'  # Slightly lighter/blue tint
        self.setStyleSheet(f"""
            NodeCardQt {{
                background-color: {flash_bg};
                border: 1px solid {self.colors['border_normal']};
                border-radius: 4px;
            }}
        """)
        
        # Schedule restoration
        self._flash_timer = QTimer(self)
        self._flash_timer.setSingleShot(True)
        self._flash_timer.timeout.connect(self._restore_border)
        self._flash_timer.start(duration_ms)
    
    def _restore_border(self):
        """Restore normal background after flash"""
        self._flash_active = False
        self._apply_current_style()
    
    def set_unread_messages(self, messages: List[Dict]):
        """Update unread messages and refresh status line"""
        self.unread_messages = messages
        self._update_status_line()
        
        # Update background color for cards with messages (alternating flash)
        if messages:
            self._message_flash_state = not self._message_flash_state
        self._apply_current_style()
    
    def _apply_current_style(self):
        """Apply the current style based on card state"""
        bg_color = self._get_background_color()
        self.setStyleSheet(f"""
            NodeCardQt {{
                background-color: {bg_color};
                border: 1px solid {self.colors['border_normal']};
                border-radius: 4px;
            }}
        """)
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press - emit clicked or context menu signal"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.node_id)
        elif event.button() == Qt.RightButton:
            self.context_menu_requested.emit(self.node_id, event.globalPosition().toPoint())
        super().mousePressEvent(event)


# =============================================================================
# Standalone Test
# =============================================================================

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QWidget, QGridLayout
    
    app = QApplication(sys.argv)
    
    # Test window
    window = QWidget()
    window.setWindowTitle("Card Renderer Test")
    window.setStyleSheet(f"background-color: {COLORS['bg_main']};")
    layout = QGridLayout(window)
    layout.setSpacing(8)
    
    # Sample node data
    sample_nodes = [
        {
            'node_id': '!a20a0de0',
            'Node LongName': 'AG6WR-Home',
            'Node ShortName': 'HOME',
            'Last Heard': time.time() - 60,  # 1 min ago (online)
            'Last Telemetry Time': time.time() - 120,
            'Ch3 Voltage': 12.8,
            'Ch3 Current': 250,
            'Battery Level': 85,
            'SNR': 8.5,
            'Channel Utilization': 35.2,
            'Air Utilization (TX)': 12.5,
            'Temperature': 28.5,
            'Humidity': 45,
            'Pressure': 1013.25,
        },
        {
            'node_id': '!a20a0fb0',
            'Node LongName': 'AG6WR-Mobile',
            'Node ShortName': 'MOBL',
            'Last Heard': time.time() - 1200,  # 20 min ago (offline)
            'Last Telemetry Time': time.time() - 1200,
            'Ch3 Voltage': 11.2,
            'Ch3 Current': -150,
            'Battery Level': 42,
            'SNR': 2.0,
            'Channel Utilization': 65.8,
            'Air Utilization (TX)': 28.3,
            'Temperature': 38.5,
            'Humidity': 72,
            'Pressure': 1008.5,
        },
        {
            'node_id': '!2f1b9773',
            'Node LongName': 'Remote Station',
            'Node ShortName': 'REMT',
            'Last Heard': time.time() - 300,  # 5 min ago (online)
            'Last Telemetry Time': time.time() - 300,
            'Battery Level': 100,
            'SNR': -5.0,
            'Channel Utilization': 88.5,
            'Temperature': 15.0,
        },
    ]
    
    # Mock data collector for voltage conversion
    class MockDataCollector:
        def voltage_to_percentage(self, voltage):
            if voltage >= 12.6:
                return 100
            elif voltage <= 10.5:
                return 0
            return int((voltage - 10.5) / 2.1 * 100)
    
    mock_collector = MockDataCollector()
    
    # Create cards
    for i, data in enumerate(sample_nodes):
        is_local = (i == 0)  # First card is local
        unread = [{'text': 'Test message from sender', 'from_name': 'TestUser'}] if i == 0 else []
        
        card = NodeCardQt(
            node_id=data['node_id'],
            node_data=data,
            is_local=is_local,
            unread_messages=unread,
            data_collector=mock_collector
        )
        
        def make_click_handler(nid):
            return lambda: print(f"Card clicked: {nid}")
        
        def make_context_handler(nid):
            return lambda node_id, pos: print(f"Context menu for {nid} at {pos}")
        
        card.clicked.connect(make_click_handler(data['node_id']))
        card.context_menu_requested.connect(make_context_handler(data['node_id']))
        
        layout.addWidget(card, i // 2, i % 2)
    
    window.resize(780, 340)
    window.show()
    
    sys.exit(app.exec())

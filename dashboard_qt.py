"""
Qt Dashboard - Main window for Meshtastic Telemetry Dashboard

This is the main application window that displays node cards in a scrollable grid,
with a header bar for controls and status. Optimized for 1280x720 Raspberry Pi touchscreen.

Architecture:
- Header: Title, connection status, control buttons
- Body: Scrollable grid of NodeCardQt widgets
- Updates: Timer-driven refresh from DataCollector

Usage:
    from dashboard_qt import DashboardQt
    
    app = QApplication(sys.argv)
    dashboard = DashboardQt()
    dashboard.show()
    sys.exit(app.exec())
"""

import sys
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QGridLayout, QFrame, QMenu,
    QSizePolicy, QSpacerItem, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSettings, QByteArray
from PySide6.QtGui import QFont, QAction

from qt_styles import COLORS, FONTS, get_font, create_button
from card_renderer_qt import NodeCardQt

logger = logging.getLogger(__name__)

# Version
VERSION = "2.0.2b"


class DashboardQt(QMainWindow):
    """Main dashboard window with scrollable card grid"""
    
    # Signals
    node_selected = Signal(str)  # node_id
    message_received = Signal(dict)  # message_data - for thread-safe message handling
    
    # Layout constants (narrowed ~20% for better fit)
    CARD_WIDTH = 368
    CARD_HEIGHT = 140
    CARD_SPACING = 8
    
    def __init__(self, config_manager=None, data_collector=None, message_manager=None):
        super().__init__()
        
        # Store references to backend components
        self.config_manager = config_manager
        self.data_collector = data_collector
        self.message_manager = message_manager
        
        # UI state
        self.card_widgets: Dict[str, NodeCardQt] = {}  # node_id -> card widget
        self.selected_node_id: Optional[str] = None
        self.is_fullscreen = False
        self.current_columns = 0
        self._geometry_restored = False  # Track if geometry has been restored
        
        # Track data for change detection
        self.last_node_data: Dict[str, Dict] = {}
        self.unread_messages: Dict[str, List[Dict]] = {}  # node_id -> list of unread messages
        
        # Message notification state
        self.notification_timer: Optional[QTimer] = None  # Timer to hide banner after 10 min
        self.notification_rotate_timer: Optional[QTimer] = None  # Timer to rotate messages
        self.notification_banner: Optional[QLabel] = None
        self.recent_notifications: List[Dict] = []  # Messages to rotate through
        self.current_notification_index: int = 0
        
        # Connect message signal to handler (for thread-safe message processing)
        self.message_received.connect(self._handle_message_on_main_thread)
        
        # Setup UI
        self._setup_window()
        self._setup_ui()
        
        # Set up message received callback
        if self.data_collector:
            self.data_collector.on_message_received = self._on_message_received
        
        # Setup refresh timer (updates every 5 seconds)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_display)
        self.refresh_timer.start(5000)
        
        # Initial refresh
        QTimer.singleShot(100, self._refresh_display)
    
    def _setup_window(self):
        """Configure main window properties"""
        self.setWindowTitle(f"CERT ICP Telemetry Dashboard v{VERSION}")
        self.setMinimumSize(800, 480)
        
        # Restore saved geometry or use defaults
        settings = QSettings("AG6WR", "MeshtasticDashboard")
        geometry = settings.value("window/geometry")
        window_state = settings.value("window/state")
        
        geometry_restored = False
        if geometry:
            geometry_restored = self.restoreGeometry(geometry)
        if window_state:
            self.restoreState(window_state)
        
        # Use explicit size/position fallback if restoreGeometry failed or no geometry
        if not geometry_restored:
            width = settings.value("window/width", 1160, type=int)
            height = settings.value("window/height", 720, type=int)
            # Sanity check: constrain to reasonable defaults for Pi (1280x720)
            width = min(max(width, 800), 1260)
            height = min(max(height, 480), 670)
            self.resize(width, height)
            # Skip position restore here - let showEvent handle it with screen info
        
        # Dark theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['bg_main']};
            }}
            QScrollArea {{
                background-color: {COLORS['bg_main']};
                border: none;
            }}
            QWidget#card_container {{
                background-color: {COLORS['bg_main']};
            }}
        """)
    
    def _setup_ui(self):
        """Build the main UI layout"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(8)
        
        # Header section
        self._create_header(self.main_layout)
        
        # Control buttons
        self._create_controls(self.main_layout)
        
        # Scrollable card area
        self._create_card_area(self.main_layout)
        
        # Message notification banner at bottom (hidden by default)
        self._create_notification_banner(self.main_layout)
    
    def _create_notification_banner(self, parent_layout: QVBoxLayout):
        """Create the message notification banner (hidden initially)"""
        self.notification_banner = QLabel("")
        self.notification_banner.setFont(get_font('ui_body'))
        self.notification_banner.setTextFormat(Qt.RichText)  # Enable rich text for bold names
        self.notification_banner.setStyleSheet("""
            QLabel {
                background-color: #FFA500;
                color: black;
                padding: 8px 12px;
                border-radius: 4px;
            }
        """)
        self.notification_banner.setWordWrap(True)
        self.notification_banner.hide()
        parent_layout.addWidget(self.notification_banner)
    
    def _create_header(self, parent_layout: QVBoxLayout):
        """Create header with title and connection status"""
        header = QWidget()
        header_layout = QHBoxLayout(header)
        # Right margin aligns with card area (accounting for scrollbar)
        header_layout.setContentsMargins(0, 0, 24, 0)
        
        # Title
        title = QLabel(f"CERT ICP Telemetry Dashboard")
        title.setFont(get_font('card_title'))
        title.setStyleSheet(f"color: {COLORS['fg_normal']};")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Right side: connection info stacked vertically, right-aligned
        right_info = QWidget()
        right_layout = QVBoxLayout(right_info)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        # Connection status row (right-aligned)
        conn_row = QWidget()
        conn_row_layout = QHBoxLayout(conn_row)
        conn_row_layout.setContentsMargins(0, 0, 0, 0)
        conn_row_layout.setSpacing(5)
        
        conn_label = QLabel("Connection:")
        conn_label.setFont(get_font('ui_body'))
        conn_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        conn_row_layout.addWidget(conn_label)
        
        self.conn_status = QLabel("Disconnected")
        self.conn_status.setFont(get_font('ui_body'))
        self.conn_status.setStyleSheet(f"color: {COLORS['fg_bad']};")
        conn_row_layout.addWidget(self.conn_status)
        
        right_layout.addWidget(conn_row, 0, Qt.AlignRight)
        
        # Version row (below connection, right-aligned)
        version_label = QLabel(f"v{VERSION}")
        version_label.setFont(get_font('ui_notes'))
        version_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        right_layout.addWidget(version_label, 0, Qt.AlignRight)
        
        header_layout.addWidget(right_info)
        
        # Status line (nodes count, last update)
        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(get_font('ui_notes'))
        self.status_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
        
        parent_layout.addWidget(header)
        parent_layout.addWidget(self.status_label)
    
    def _create_controls(self, parent_layout: QVBoxLayout):
        """Create control button bar"""
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        # Right margin aligns buttons with card area (accounting for scrollbar)
        controls_layout.setContentsMargins(0, 0, 24, 0)
        controls_layout.setSpacing(5)
        
        # Settings button
        self.btn_settings = create_button("Settings", "primary")
        self.btn_settings.clicked.connect(self._open_settings)
        controls_layout.addWidget(self.btn_settings)
        
        # Refresh button
        self.btn_refresh = create_button("Refresh", "primary")
        self.btn_refresh.clicked.connect(self._force_refresh)
        controls_layout.addWidget(self.btn_refresh)
        
        # Messages button
        self.btn_messages = create_button("Messages", "primary")
        self.btn_messages.clicked.connect(self._open_messages)
        controls_layout.addWidget(self.btn_messages)
        
        # Plot button
        self.btn_plot = create_button("Plot", "primary")
        self.btn_plot.clicked.connect(self._show_plot)
        controls_layout.addWidget(self.btn_plot)
        
        # Alerts button
        self.btn_alerts = create_button("Alerts", "primary")
        self.btn_alerts.clicked.connect(self._open_alerts)
        controls_layout.addWidget(self.btn_alerts)
        
        controls_layout.addStretch()
        
        # Fullscreen toggle
        self.btn_fullscreen = create_button("Fullscreen", "primary")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        controls_layout.addWidget(self.btn_fullscreen)
        
        # Quit button
        self.btn_quit = create_button("✗ Quit", "neutral")
        self.btn_quit.clicked.connect(self.close)
        controls_layout.addWidget(self.btn_quit)
        
        parent_layout.addWidget(controls)
    
    def _create_card_area(self, parent_layout: QVBoxLayout):
        """Create scrollable area for node cards"""
        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Make scrollbar wider for touch
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_main']};
                border: none;
            }}
            QScrollBar:vertical {{
                width: 24px;
                background: {COLORS['bg_frame']};
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['fg_secondary']};
                border-radius: 4px;
                min-height: 40px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Container widget for grid
        self.card_container = QWidget()
        self.card_container.setObjectName("card_container")
        self.card_layout = QGridLayout(self.card_container)
        self.card_layout.setSpacing(self.CARD_SPACING)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.scroll_area.setWidget(self.card_container)
        parent_layout.addWidget(self.scroll_area, stretch=1)
    
    def _get_local_node_id(self) -> str:
        """Get the local node ID"""
        if self.data_collector and hasattr(self.data_collector, 'connection_manager'):
            node_id = self.data_collector.connection_manager.get_local_node_id()
            if node_id:
                return node_id
        if self.config_manager:
            return self.config_manager.get('meshtastic.local_node_id', '')
        # Demo mode - return first node as local
        return '!a20a0de0'
    
    def _calculate_columns(self) -> int:
        """Calculate how many card columns fit in current width"""
        available_width = self.scroll_area.viewport().width()
        card_width_with_spacing = self.CARD_WIDTH + self.CARD_SPACING
        columns = max(1, available_width // card_width_with_spacing)
        return columns
    
    def _refresh_display(self):
        """Refresh dashboard with current data"""
        try:
            # Get data from collector
            if self.data_collector:
                nodes_data = self.data_collector.get_nodes_data()
                connection_status = self.data_collector.get_connection_status()
            else:
                # Demo mode with sample data
                nodes_data = self._get_sample_data()
                connection_status = {'connected': False}
            
            # Update connection status
            self._update_connection_status(connection_status)
            
            # Update cards
            self._update_cards(nodes_data)
            
            # Update status line
            now = datetime.now()
            node_count = len(nodes_data)
            online_count = self._count_online_nodes(nodes_data)
            self.status_label.setText(
                f"Updated: {now.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Nodes: {node_count} ({online_count} online)"
            )
            
        except Exception as e:
            logger.error(f"Error refreshing display: {e}")
    
    def _update_connection_status(self, status: Dict):
        """Update connection status display"""
        if status.get('connected'):
            interface_info = status.get('interface_info', {})
            conn_type = interface_info.get('type', 'unknown')
            if conn_type == 'tcp':
                conn_text = f"TCP {interface_info.get('host', '')}:{interface_info.get('port', '')}"
            elif conn_type == 'serial':
                port = interface_info.get('port', 'unknown')
                conn_text = f"Serial {port}"
            else:
                conn_text = conn_type.upper()
            self.conn_status.setText(f"Connected ({conn_text})")
            self.conn_status.setStyleSheet(f"color: {COLORS['fg_good']};")
        else:
            self.conn_status.setText("Disconnected")
            self.conn_status.setStyleSheet(f"color: {COLORS['fg_bad']};")
    
    def _update_cards(self, nodes_data: Dict[str, Dict]):
        """Update card widgets for all nodes"""
        local_node_id = self._get_local_node_id()
        columns = self._calculate_columns()
        
        # Check if we need to rebuild layout (column count changed or nodes changed)
        current_node_ids = set(nodes_data.keys())
        existing_node_ids = set(self.card_widgets.keys())
        
        need_rebuild = (
            columns != self.current_columns or
            current_node_ids != existing_node_ids
        )
        
        if need_rebuild:
            self._rebuild_cards(nodes_data, local_node_id, columns)
        else:
            # Just update existing cards
            for node_id, node_data in nodes_data.items():
                if node_id in self.card_widgets:
                    card = self.card_widgets[node_id]
                    unread = self.unread_messages.get(node_id, [])
                    card.update_data(node_data, unread_messages=unread)
        
        self.last_node_data = {k: dict(v) for k, v in nodes_data.items()}
    
    def _rebuild_cards(self, nodes_data: Dict[str, Dict], local_node_id: str, columns: int):
        """Rebuild all card widgets in grid"""
        self.current_columns = columns
        
        # Clear existing cards
        for card in self.card_widgets.values():
            card.deleteLater()
        self.card_widgets.clear()
        
        # Clear layout
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Sort nodes: local node first, then by name
        def sort_key(item):
            node_id, data = item
            is_local = node_id == local_node_id
            name = data.get('Node LongName', node_id)
            return (not is_local, name.lower())
        
        sorted_nodes = sorted(nodes_data.items(), key=sort_key)
        
        # Create cards
        for idx, (node_id, node_data) in enumerate(sorted_nodes):
            row = idx // columns
            col = idx % columns
            
            is_local = node_id == local_node_id
            unread = self.unread_messages.get(node_id, [])
            
            # Debug: Log unread messages for each card
            if unread:
                logger.info(f"Card {node_id}: has {len(unread)} unread messages")
            
            card = NodeCardQt(
                node_id=node_id,
                node_data=node_data,
                is_local=is_local,
                unread_messages=unread,
                config_manager=self.config_manager,
                data_collector=self.data_collector
            )
            
            # Connect signals
            card.clicked.connect(self._on_card_clicked)
            card.context_menu_requested.connect(self._on_card_context_menu)
            
            self.card_layout.addWidget(card, row, col)
            self.card_widgets[node_id] = card
    
    def _count_online_nodes(self, nodes_data: Dict) -> int:
        """Count nodes that are online (heard within 16 minutes)"""
        current_time = time.time()
        online_threshold = 960  # 16 minutes
        count = 0
        for data in nodes_data.values():
            last_heard = data.get('Last Heard', 0)
            if last_heard and (current_time - last_heard) < online_threshold:
                count += 1
        return count
    
    def _get_sample_data(self) -> Dict[str, Dict]:
        """Get sample data for demo/testing"""
        return {
            '!a20a0de0': {
                'node_id': '!a20a0de0',
                'Node LongName': 'AG6WR-Home',
                'Node ShortName': 'HOME',
                'Last Heard': time.time() - 60,
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
            '!a20a0fb0': {
                'node_id': '!a20a0fb0',
                'Node LongName': 'AG6WR-Mobile',
                'Node ShortName': 'MOBL',
                'Last Heard': time.time() - 1200,
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
            '!2f1b9773': {
                'node_id': '!2f1b9773',
                'Node LongName': 'Remote Station',
                'Node ShortName': 'REMT',
                'Last Heard': time.time() - 300,
                'Last Telemetry Time': time.time() - 300,
                'Battery Level': 100,
                'SNR': -5.0,
                'Channel Utilization': 88.5,
                'Temperature': 15.0,
            },
        }
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    @Slot(str)
    def _on_card_clicked(self, node_id: str):
        """Handle card click - open node detail window"""
        logger.info(f"Card clicked: {node_id}")
        self.selected_node_id = node_id
        self.node_selected.emit(node_id)
        
        # Open node detail window
        try:
            from node_detail_window_qt import NodeDetailWindowQt
            node_data = self.last_node_data.get(node_id, {})
            
            # Create callbacks for buttons
            def on_logs():
                self._open_logs_for(node_id)
            
            def on_csv():
                self._open_csv_for(node_id)
            
            def on_plot():
                self._show_plot_for(node_id)
            
            detail_window = NodeDetailWindowQt(
                parent=self,
                node_id=node_id,
                node_data=node_data,
                on_logs=on_logs,
                on_csv=on_csv,
                on_plot=on_plot,
                data_collector=self.data_collector
            )
            detail_window.show()
        except Exception as e:
            logger.error(f"Failed to open node detail: {e}")
    
    @Slot(str, object)
    def _on_card_context_menu(self, node_id: str, pos):
        """Handle card right-click - show context menu"""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['bg_frame']};
                color: {COLORS['fg_normal']};
                border: 1px solid {COLORS['fg_secondary']};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['accent']};
            }}
        """)
        
        # View Details
        action_details = menu.addAction("View Details")
        action_details.triggered.connect(lambda: self._on_card_clicked(node_id))
        
        menu.addSeparator()
        
        # Send Message
        action_message = menu.addAction("Send Message")
        action_message.triggered.connect(lambda: self._send_message_to(node_id))
        
        # View Messages
        action_messages = menu.addAction("View Messages")
        action_messages.triggered.connect(lambda: self._view_messages_for(node_id))
        
        menu.addSeparator()
        
        # Show Plot
        action_plot = menu.addAction("Show Plot")
        action_plot.triggered.connect(lambda: self._show_plot_for(node_id))
        
        menu.exec(pos)
    
    def _send_message_to(self, node_id: str):
        """Open message dialog to send message to node"""
        try:
            from message_dialog_qt import MessageDialogQt
            
            # Get node name - check both data_collector and last_node_data
            node_name = node_id
            if self.data_collector:
                nodes_data = self.data_collector.get_nodes_data()
                if nodes_data and node_id in nodes_data:
                    node_name = nodes_data[node_id].get('Node LongName', node_id)
            elif node_id in self.last_node_data:
                node_name = self.last_node_data[node_id].get('Node LongName', node_id)
            
            dialog = MessageDialogQt(
                parent=self,
                node_id=node_id,
                node_name=node_name,
                send_callback=self._actual_send_message
            )
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to open message dialog: {e}")
    
    def _actual_send_message(self, node_id: str, message: str, bell_flag: bool = False):
        """Actually send the message via connection manager"""
        import time
        try:
            if self.data_collector and hasattr(self.data_collector, 'connection_manager'):
                success = self.data_collector.connection_manager.send_message(node_id, message)
                if success:
                    logger.info(f"Message sent to {node_id}")
                    # Also save to message manager for tracking
                    if self.message_manager:
                        local_node_id = self._get_local_node_id()
                        message_dict = {
                            'message_id': f"{local_node_id}_{int(time.time() * 1000)}",
                            'from_node_id': local_node_id,
                            'from_name': 'Me',
                            'to_node_ids': [node_id],
                            'text': message,
                            'timestamp': time.time(),
                            'direction': 'sent',
                            'is_bulletin': False,
                            'read': True,  # We read our own message
                            'delivery_status': 'sent'
                        }
                        self.message_manager.save_message(message_dict)
                else:
                    logger.error(f"Failed to send message to {node_id}")
                    QMessageBox.warning(self, "Send Failed", f"Failed to send message to {node_id}")
            else:
                logger.error("No connection manager available")
                QMessageBox.warning(self, "Not Connected", "Cannot send message: not connected to Meshtastic")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            QMessageBox.critical(self, "Error", f"Error sending message: {e}")
    
    def _on_message_received(self, message_data: Dict):
        """Handle incoming message from data collector (called from background thread)
        
        This method is called from the Meshtastic connection thread.
        We emit a signal to safely process on the main UI thread.
        """
        # Emit signal to process on main thread (thread-safe)
        self.message_received.emit(message_data)
    
    @Slot(dict)
    def _handle_message_on_main_thread(self, message_data: Dict):
        """Process message on the main UI thread (connected via signal)"""
        try:
            from_node = message_data.get('from', 'Unknown')
            to_node = message_data.get('to', 'Unknown')
            text = message_data.get('text', '')
            timestamp = message_data.get('timestamp', time.time())
            
            # Get node names
            from_name = self._get_node_name(from_node)
            local_node_id = self._get_local_node_id()
            
            # Only process messages TO our local node (or broadcast)
            if to_node != local_node_id and to_node != '^all':
                logger.debug(f"Ignoring message not addressed to us: to={to_node}")
                return
            
            logger.info(f"Processing incoming message from {from_name} ({from_node}) to {to_node}")
            
            # Store messages under RECIPIENT's node ID so they appear on the receiving card
            # This means the home/local card shows messages sent TO us
            recipient_key = to_node if to_node != '^all' else local_node_id
            
            # Debug: Log node ID formats for comparison
            if self.data_collector:
                known_ids = list(self.data_collector.nodes_data.keys())
                logger.debug(f"Storing message under recipient: '{recipient_key}' | Known nodes: {known_ids}")
            
            # Add to unread messages for the RECIPIENT (enrich with from_name for card display)
            if recipient_key not in self.unread_messages:
                self.unread_messages[recipient_key] = []
            enriched_message = dict(message_data)
            enriched_message['from_name'] = from_name
            self.unread_messages[recipient_key].append(enriched_message)
            
            # Save to message manager if available
            if self.message_manager:
                message_dict = {
                    'message_id': f"{from_node}_{int(timestamp * 1000)}",
                    'from_node_id': from_node,
                    'from_name': from_name,
                    'to_node_ids': [to_node],
                    'text': text,
                    'timestamp': timestamp,
                    'direction': 'received',
                    'is_bulletin': to_node == '^all',
                    'read': False,
                    'rxSnr': message_data.get('rxSnr'),
                    'hopLimit': message_data.get('hopLimit')
                }
                self.message_manager.save_message(message_dict)
            
            # Show notification banner
            self._show_message_notification(from_node, from_name, text)
            
            # Update Messages button with unread count
            self._update_messages_button()
            
            # Force refresh to update card flex-use line
            self._refresh_display()
            
        except Exception as e:
            logger.error(f"Error handling received message: {e}")
    
    def _get_node_name(self, node_id: str) -> str:
        """Get the display name for a node"""
        if self.data_collector and node_id in self.data_collector.nodes_data:
            return self.data_collector.nodes_data[node_id].get('Node LongName', node_id)
        return node_id
    
    def _show_message_notification(self, from_node: str, from_name: str, text: str):
        """Add message to notification rotation and show banner for 10 minutes"""
        import time as time_module
        
        # Get local node name
        local_node_id = self._get_local_node_id()
        local_name = self._get_node_name(local_node_id) if local_node_id else "Local"
        
        # Add to recent notifications
        notification = {
            'from_name': from_name,
            'to_name': local_name,
            'text': text,
            'timestamp': time_module.time()
        }
        self.recent_notifications.append(notification)
        
        # Remove notifications older than 10 minutes
        cutoff = time_module.time() - 600  # 10 minutes
        self.recent_notifications = [n for n in self.recent_notifications if n['timestamp'] > cutoff]
        
        # Update the banner display
        self._update_notification_display()
        self.notification_banner.show()
        
        # Reset the hide timer to 10 minutes from now
        if self.notification_timer:
            self.notification_timer.stop()
        self.notification_timer = QTimer(self)
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(self._hide_notification)
        self.notification_timer.start(600000)  # 10 minutes
        
        # Start rotation timer if multiple messages (rotate every 5 seconds)
        if len(self.recent_notifications) > 1:
            if not self.notification_rotate_timer:
                self.notification_rotate_timer = QTimer(self)
                self.notification_rotate_timer.timeout.connect(self._rotate_notification)
                self.notification_rotate_timer.start(5000)  # Rotate every 5 seconds
    
    def _update_notification_display(self):
        """Update the banner with the current notification"""
        if not self.recent_notifications:
            return
        
        # Get current notification
        idx = self.current_notification_index % len(self.recent_notifications)
        notif = self.recent_notifications[idx]
        
        # Format time as HH:MM
        from datetime import datetime
        dt = datetime.fromtimestamp(notif['timestamp'])
        time_str = dt.strftime("%H:%M")
        
        # Truncate long messages
        text = notif['text']
        display_text = text[:80] + '...' if len(text) > 80 else text
        
        # Format with bold names: <HH:MM> **FromNode** to **ToNode**: message
        html = f"&lt;{time_str}&gt; <b>{notif['from_name']}</b> to <b>{notif['to_name']}</b>: {display_text}"
        
        # Add indicator if multiple messages
        if len(self.recent_notifications) > 1:
            html = f"[{idx + 1}/{len(self.recent_notifications)}] " + html
        
        self.notification_banner.setText(html)
    
    def _rotate_notification(self):
        """Rotate to the next notification"""
        import time as time_module
        
        # Remove old notifications first
        cutoff = time_module.time() - 600
        self.recent_notifications = [n for n in self.recent_notifications if n['timestamp'] > cutoff]
        
        if not self.recent_notifications:
            self._hide_notification()
            return
        
        # Advance to next message
        self.current_notification_index = (self.current_notification_index + 1) % len(self.recent_notifications)
        self._update_notification_display()
        
        # Stop rotation timer if only one message left
        if len(self.recent_notifications) <= 1 and self.notification_rotate_timer:
            self.notification_rotate_timer.stop()
            self.notification_rotate_timer = None
    
    def _hide_notification(self):
        """Hide the notification banner and clear state"""
        if self.notification_banner:
            self.notification_banner.hide()
        if self.notification_rotate_timer:
            self.notification_rotate_timer.stop()
            self.notification_rotate_timer = None
        self.recent_notifications.clear()
        self.current_notification_index = 0
    
    def _update_messages_button(self):
        """Update Messages button text with unread count"""
        total_unread = sum(len(msgs) for msgs in self.unread_messages.values())
        if total_unread > 0:
            self.btn_messages.setText(f"Messages ({total_unread})")
        else:
            self.btn_messages.setText("Messages")
    
    def _view_messages_for(self, node_id: str):
        """Open message list for specific node"""
        try:
            from message_list_window_qt import MessageListWindowQt
            window = MessageListWindowQt(
                parent=self,
                message_manager=self.message_manager,
                on_view_message=self._view_message,
                on_send_message=self._send_message_to
            )
            window.show()
        except Exception as e:
            logger.error(f"Failed to open message list: {e}")
    
    def _show_plot_for(self, node_id: str):
        """Show plot for specific node"""
        logger.info(f"Show plot for {node_id}")
        try:
            from plotter_qt import TelemetryPlotterQt
            plotter = TelemetryPlotterQt(self, self.config_manager)
            plotter.show_plot_dialog(preselect_node_id=node_id)
        except Exception as e:
            logger.error(f"Failed to show plot: {e}")
    
    def _open_logs_for(self, node_id: str):
        """Open logs folder for specific node"""
        import os
        import subprocess
        
        log_dir = 'logs'
        if self.config_manager:
            log_dir = self.config_manager.get('data.log_directory', 'logs')
        
        clean_id = node_id[1:] if node_id.startswith('!') else node_id
        node_log_path = os.path.join(log_dir, clean_id)
        
        if os.path.exists(node_log_path):
            self._open_path(node_log_path)
        else:
            QMessageBox.information(self, "No Logs", f"No log directory found for {node_id}")
    
    def _open_csv_for(self, node_id: str):
        """Open today's CSV file for specific node"""
        import os
        from datetime import datetime
        
        log_dir = 'logs'
        if self.config_manager:
            log_dir = self.config_manager.get('data.log_directory', 'logs')
        
        clean_id = node_id[1:] if node_id.startswith('!') else node_id
        today = datetime.now()
        csv_path = os.path.join(log_dir, clean_id, today.strftime('%Y'), today.strftime('%Y%m%d') + '.csv')
        
        if os.path.exists(csv_path):
            self._open_path(csv_path)
        else:
            QMessageBox.information(self, "No CSV", f"No CSV file found for today for {node_id}")
    
    def _open_path(self, path: str):
        """Open file or folder in system default application"""
        import os
        import subprocess
        import sys
        
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open {path}: {e}")
    
    # =========================================================================
    # Button Handlers
    # =========================================================================
    
    def _open_settings(self):
        """Open settings dialog"""
        try:
            from settings_dialog_qt import SettingsDialogQt
            dialog = SettingsDialogQt(
                config_manager=self.config_manager,
                parent=self
            )
            # Connect to settings_changed signal for immediate refresh on Apply
            dialog.settings_changed.connect(self._on_settings_changed)
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to open settings: {e}")
    
    def _on_settings_changed(self):
        """Handle settings changed signal - refresh display immediately"""
        logger.info("Settings changed, refreshing display")
        # Clear cache to force full update with new settings
        self.last_node_data.clear()
        self._refresh_display()
    
    def _force_refresh(self):
        """Force immediate refresh"""
        logger.info("Manual refresh triggered")
        # Clear cache to force full update
        self.last_node_data.clear()
        self._refresh_display()
        # Update status to show refresh happened
        now = datetime.now()
        self.status_label.setText(
            f"Manual refresh: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def _open_messages(self):
        """Open message list window"""
        try:
            from message_list_window_qt import MessageListWindowQt
            window = MessageListWindowQt(
                parent=self,
                message_manager=self.message_manager,
                on_view_message=self._view_message,
                on_send_message=self._send_message_to
            )
            window.show()
            
            # Clear unread messages when viewing
            self.unread_messages.clear()
            self._update_messages_button()
        except Exception as e:
            logger.error(f"Failed to open messages: {e}")
    
    def _show_plot(self):
        """Show telemetry plot"""
        logger.info("Show plot")
        try:
            from plotter_qt import TelemetryPlotterQt
            plotter = TelemetryPlotterQt(self, self.config_manager)
            plotter.show_plot_dialog()
        except Exception as e:
            logger.error(f"Failed to show plot: {e}")
    
    def _open_alerts(self):
        """Open alerts configuration"""
        logger.info("Open alerts")
        try:
            from node_alert_config_qt import NodeAlertConfigDialogQt
            
            # Get current nodes data
            nodes_data = {}
            if self.data_collector:
                nodes_data = self.data_collector.get_nodes_data()
            
            if not nodes_data:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "No Nodes",
                    "No nodes available to configure alerts for.\n\n"
                    "Nodes will appear here once they are discovered on the mesh."
                )
                return
            
            dialog = NodeAlertConfigDialogQt(
                nodes_data=nodes_data,
                config_manager=self.config_manager,
                parent=self
            )
            dialog.exec()
        except Exception as e:
            logger.error(f"Failed to open alerts dialog: {e}")
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.showFullScreen()
            self.btn_fullscreen.setText("Exit Fullscreen")
        else:
            self.showNormal()
            self.btn_fullscreen.setText("Fullscreen")
    
    def resizeEvent(self, event):
        """Handle window resize - reflow cards if needed"""
        super().resizeEvent(event)
        # Trigger card reflow after resize
        QTimer.singleShot(100, self._check_reflow)
    
    def _check_reflow(self):
        """Check if cards need to be reflowed due to column change"""
        new_columns = self._calculate_columns()
        if new_columns != self.current_columns and self.card_widgets:
            self._refresh_display()
    
    def _view_message(self, message_id: str):
        """View a single message in a dialog"""
        try:
            if not self.message_manager:
                logger.warning("No message manager available")
                return
            
            message = self.message_manager.get_message_by_id(message_id)
            if not message:
                QMessageBox.warning(self, "Not Found", "Message not found.")
                return
            
            # Mark as read
            self.message_manager.mark_as_read(message_id)
            
            # Clear from unread tracking - messages are keyed by recipient (local node)
            # For received messages, the recipient is our local node
            local_node_id = self._get_local_node_id()
            to_node_ids = message.get('to_node_ids', [])
            recipient_key = to_node_ids[0] if to_node_ids and to_node_ids[0] != '^all' else local_node_id
            
            if recipient_key in self.unread_messages:
                self.unread_messages[recipient_key] = [
                    m for m in self.unread_messages[recipient_key] 
                    if m.get('message_id') != message_id
                ]
                if not self.unread_messages[recipient_key]:
                    del self.unread_messages[recipient_key]
            self._update_messages_button()
            
            # Build message details
            direction = message.get('direction', 'received')
            from_name = message.get('from_name', 'Unknown')
            to_ids = message.get('to_node_ids', [])
            is_bulletin = message.get('is_bulletin', False)
            text = message.get('text', '')
            timestamp = message.get('timestamp', 0)
            
            # Format timestamp
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Build header info
            if direction == 'sent':
                if is_bulletin:
                    header = f"Sent Bulletin\nTo: Everyone\nTime: {time_str}"
                elif len(to_ids) > 1:
                    header = f"Sent Message\nTo: {', '.join(to_ids)}\nTime: {time_str}"
                else:
                    header = f"Sent Message\nTo: {to_ids[0] if to_ids else 'Unknown'}\nTime: {time_str}"
            else:
                if is_bulletin:
                    header = f"Bulletin from {from_name}\nTime: {time_str}"
                else:
                    header = f"Message from {from_name}\nTime: {time_str}"
            
            # Create view dialog
            from PySide6.QtWidgets import QDialog, QTextEdit
            dialog = QDialog(self)
            dialog.setWindowTitle("View Message")
            dialog.setMinimumSize(500, 350)
            dialog.setStyleSheet(f"""
                QDialog {{
                    background-color: {COLORS['bg_main']};
                }}
                QLabel {{
                    color: {COLORS['fg_normal']};
                }}
                QTextEdit {{
                    background-color: {COLORS['bg_frame']};
                    color: {COLORS['fg_normal']};
                    border: 1px solid {COLORS['fg_secondary']};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.setContentsMargins(16, 16, 16, 16)
            
            # Header label
            header_label = QLabel(header)
            header_label.setFont(get_font('ui_body'))
            header_label.setStyleSheet(f"color: {COLORS['fg_secondary']};")
            layout.addWidget(header_label)
            
            # Message text
            text_edit = QTextEdit()
            text_edit.setFont(get_font('ui_body'))
            text_edit.setPlainText(text)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit, stretch=1)
            
            # Buttons
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            # Reply button (if received message)
            if direction == 'received':
                reply_btn = create_button("Reply", "success")
                reply_btn.clicked.connect(lambda: self._reply_to_message(message, dialog))
                btn_layout.addWidget(reply_btn)
            
            close_btn = create_button("Close", "secondary")
            close_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(close_btn)
            
            layout.addLayout(btn_layout)
            
            # Position relative to parent
            parent_geo = self.geometry()
            dialog.move(parent_geo.x() + 100, parent_geo.y() + 50)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"Error viewing message: {e}")
            QMessageBox.critical(self, "Error", f"Failed to view message: {e}")
    
    def _reply_to_message(self, message: Dict, parent_dialog: QWidget):
        """Reply to a message"""
        logger.info(f"Reply button clicked, message: {message}")
        parent_dialog.accept()  # Close view dialog
        from_node = message.get('from_node_id', '')
        logger.info(f"Reply to from_node: '{from_node}'")
        if from_node:
            self._send_message_to(from_node)
        else:
            logger.warning("No from_node_id in message, cannot reply")
    
    def keyPressEvent(self, event):
        """Handle key presses"""
        if event.key() == Qt.Key_F11:
            self._toggle_fullscreen()
        elif event.key() == Qt.Key_Escape and self.is_fullscreen:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)
    
    def showEvent(self, event):
        """Restore geometry after window is shown (for Wayland/other WMs that need it)"""
        super().showEvent(event)
        if not self._geometry_restored:
            self._geometry_restored = True
            # Defer geometry restoration slightly to ensure window is fully shown
            QTimer.singleShot(50, self._apply_saved_geometry)
    
    def _apply_saved_geometry(self):
        """Apply saved geometry after window is shown, with sanity checks"""
        settings = QSettings("AG6WR", "MeshtasticDashboard")
        width = settings.value("window/width", type=int)
        height = settings.value("window/height", type=int)
        x = settings.value("window/x", type=int)
        y = settings.value("window/y", type=int)
        
        # Get available screen geometry
        screen = self.screen()
        if screen:
            screen_rect = screen.availableGeometry()
            screen_width = screen_rect.width()
            screen_height = screen_rect.height()
            screen_x = screen_rect.x()
            screen_y = screen_rect.y()
        else:
            # Fallback to common Pi resolution
            screen_width, screen_height = 1280, 720
            screen_x, screen_y = 0, 0
        
        # Leave room for window decorations (title bar ~30px, borders ~10px)
        max_width = screen_width - 20
        max_height = screen_height - 50
        
        # Apply size with sanity checks
        if width and height:
            # Constrain to screen size
            width = min(width, max_width)
            height = min(height, max_height)
            # Ensure minimum size
            width = max(width, 800)
            height = max(height, 480)
            self.resize(width, height)
        
        # Apply position with sanity checks
        if x is not None and y is not None:
            # Ensure window is visible (at least 100px on screen)
            x = max(screen_x, min(x, screen_x + screen_width - 100))
            y = max(screen_y, min(y, screen_y + screen_height - 100))
            self.move(x, y)
    
    def closeEvent(self, event):
        """Save window geometry on close"""
        settings = QSettings("AG6WR", "MeshtasticDashboard")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState())
        # Also save explicit size/position as fallback
        settings.setValue("window/width", self.width())
        settings.setValue("window/height", self.height())
        settings.setValue("window/x", self.x())
        settings.setValue("window/y", self.y())
        super().closeEvent(event)


# =============================================================================
# Standalone Test
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    # Create dashboard in demo mode (no backend)
    dashboard = DashboardQt()
    dashboard.show()
    
    sys.exit(app.exec())

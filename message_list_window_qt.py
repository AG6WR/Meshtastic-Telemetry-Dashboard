"""
Message List Window (Qt/PySide6) - Central messaging hub

Shows all messages in tabbed interface:
- Inbox: Received messages (not archived)
- Sent: Sent messages (not archived)
- Archived: Archived messages

Click message row to view. Use checkboxes for bulk actions.

This is the PySide6 port of message_list_window.py.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QTabWidget, QCheckBox,
    QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QCursor

from qt_styles import create_button, create_close_button, create_cancel_button, COLORS, BUTTON_STYLES, get_font, TAB_STYLE, CHECKBOX_STYLE

logger = logging.getLogger(__name__)


class MessageListWindowQt(QDialog):
    """Qt window for viewing message list with tabs"""
    
    def __init__(self, parent, message_manager,
                 on_view_message: Optional[Callable] = None,
                 on_send_message: Optional[Callable] = None):
        """Initialize message list window
        
        Args:
            parent: Parent window
            message_manager: MessageManager instance
            on_view_message: Callback when message clicked - receives (message_id)
            on_send_message: Callback when compose clicked - receives (node_id)
        """
        super().__init__(parent)
        
        self.parent_window = parent
        self.message_manager = message_manager
        self.on_view_message_callback = on_view_message
        self.on_send_message_callback = on_send_message
        
        # Get colors from parent (dark theme)
        self.colors = getattr(parent, 'colors', {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'fg_secondary': '#b0b0b0',
            'fg_good': '#228B22',
            'fg_warning': '#FFA500',
            'fg_bad': '#FF6B9D',
            'accent': '#4a90d9',
            'button_bg': '#0d47a1',
            'button_fg': '#ffffff'
        })
        
        # Track checkbox items per tab: list of (QCheckBox, message_id)
        self.inbox_items: List[Tuple[QCheckBox, str]] = []
        self.sent_items: List[Tuple[QCheckBox, str]] = []
        self.archived_items: List[Tuple[QCheckBox, str]] = []
        
        # State tracking for auto-refresh
        self._last_messages_hash = None
        self._auto_refresh_timer = None
        
        self.setWindowTitle("Messages")
        self.setMinimumSize(756, 650)
        self.setModal(False)  # Non-modal so user can interact with main window
        
        self._apply_dark_theme()
        self._create_ui()
        
        # Load initial data
        self._refresh_all_tabs()
        
        # Start auto-refresh timer (2 seconds)
        self._start_auto_refresh()
        
        # Position relative to parent
        if parent:
            parent_geo = parent.geometry()
            self.move(parent_geo.x() + 50, parent_geo.y() + 30)
    
    def _apply_dark_theme(self):
        """Apply dark theme styling - match settings_dialog_qt exactly"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['bg_main']};
            }}
            QLabel {{
                color: {self.colors['fg_normal']};
            }}
            {CHECKBOX_STYLE}
            {TAB_STYLE}
        """)
    
    def _create_ui(self):
        """Create the main UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
        # Title bar with buttons
        self._create_title_bar(layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.inbox_tab, self.inbox_scroll, self.inbox_content = self._create_tab()
        self.sent_tab, self.sent_scroll, self.sent_content = self._create_tab()
        self.archived_tab, self.archived_scroll, self.archived_content = self._create_tab()
        
        self.tab_widget.addTab(self.inbox_tab, "Inbox")
        self.tab_widget.addTab(self.sent_tab, "Sent")
        self.tab_widget.addTab(self.archived_tab, "Archived")
        
        layout.addWidget(self.tab_widget)
        
        # Action buttons at bottom
        self._create_action_bar(layout)
    
    def _create_title_bar(self, parent_layout):
        """Create title bar with compose and close buttons"""
        title_frame = QFrame()
        title_frame.setStyleSheet(f"background-color: {self.colors['bg_frame']}; padding: 6px;")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(10, 6, 10, 6)
        
        # Compose button (left side - additive action)
        compose_btn = create_button("Compose", "success", self._on_compose)
        title_layout.addWidget(compose_btn)
        
        title_layout.addStretch()
        
        # Title (center)
        title_label = QLabel("Message Center")
        title_label.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 14pt; font-weight: bold;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # Close button (right side - standard neutral/grey style)
        close_btn = create_close_button(self.close)
        title_layout.addWidget(close_btn)
        
        parent_layout.addWidget(title_frame)
    
    def _create_tab(self) -> Tuple[QWidget, QScrollArea, QWidget]:
        """Create a tab with scrollable message list
        
        Returns:
            Tuple of (tab_widget, scroll_area, content_widget)
        """
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_widget.setObjectName("tabContent")
        # Use specific selector to avoid cascading to child widgets (breaks checkboxes)
        content_widget.setStyleSheet(f"QWidget#tabContent {{ background-color: {self.colors['bg_main']}; }}")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(4)
        content_layout.addStretch()  # Push content to top
        
        scroll_area.setWidget(content_widget)
        tab_layout.addWidget(scroll_area)
        
        return tab, scroll_area, content_widget
    
    def _create_action_bar(self, parent_layout):
        """Create action button bar at bottom"""
        action_frame = QFrame()
        action_frame.setStyleSheet(f"background-color: {self.colors['bg_frame']}; padding: 6px;")
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(10, 6, 10, 6)
        
        # Selection count label (left side)
        self.selection_label = QLabel("No selection")
        self.selection_label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt;")
        action_layout.addWidget(self.selection_label)
        
        action_layout.addStretch()
        
        # Delete button (separated from other actions)
        delete_btn = create_button("Delete", "danger", self._on_delete_selected)
        action_layout.addWidget(delete_btn)
        
        # Spacer between delete and other actions
        spacer = QLabel("  ")
        spacer.setStyleSheet("background: transparent;")
        action_layout.addWidget(spacer)
        
        # Archive button
        archive_btn = create_button("Archive", "warning", self._on_archive_selected)
        action_layout.addWidget(archive_btn)
        
        # Reply button
        reply_btn = create_button("Reply", "success", self._on_reply_selected)
        action_layout.addWidget(reply_btn)
        
        # View button (rightmost - primary action)
        view_btn = create_button("View", "primary", self._on_view_selected)
        action_layout.addWidget(view_btn)
        
        parent_layout.addWidget(action_frame)
    
    def _refresh_all_tabs(self):
        """Refresh all tab contents"""
        self._refresh_tab("inbox")
        self._refresh_tab("sent")
        self._refresh_tab("archived")
    
    def _refresh_tab(self, tab_type: str):
        """Refresh a specific tab
        
        Args:
            tab_type: "inbox", "sent", or "archived"
        """
        # Get the appropriate content widget and items list
        if tab_type == "inbox":
            content_widget = self.inbox_content
            items_list = self.inbox_items
        elif tab_type == "sent":
            content_widget = self.sent_content
            items_list = self.sent_items
        else:  # archived
            content_widget = self.archived_content
            items_list = self.archived_items
        
        # Clear existing items
        layout = content_widget.layout()
        while layout.count() > 1:  # Keep the stretch at the end
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        items_list.clear()
        
        # Get messages
        all_messages = self.message_manager.load_messages()
        
        # Filter messages based on tab type
        if tab_type == "inbox":
            messages = [m for m in all_messages 
                       if m.get('direction') == 'received' and not m.get('archived', False)]
        elif tab_type == "sent":
            messages = [m for m in all_messages 
                       if m.get('direction') == 'sent' and not m.get('archived', False)]
        else:  # archived
            messages = [m for m in all_messages if m.get('archived', False)]
        
        # Sort by timestamp (newest first)
        messages.sort(key=lambda m: m.get('timestamp', 0), reverse=True)
        
        # Add messages as rows (insert before the stretch)
        for msg in messages:
            row_widget = self._create_message_row(msg, items_list)
            layout.insertWidget(layout.count() - 1, row_widget)
        
        # Update selection count
        self._update_selection_count()
    
    def _create_message_row(self, message: Dict[str, Any], items_list: list) -> QFrame:
        """Create a message row widget
        
        Args:
            message: Message dictionary
            items_list: List to track checkbox references
            
        Returns:
            QFrame containing the message row
        """
        message_id = message.get('message_id', 'unknown')
        direction = message.get('direction', 'received')
        from_name = message.get('from_name', 'Unknown')
        to_ids = message.get('to_node_ids', [])
        is_bulletin = message.get('is_bulletin', False)
        text = message.get('text', '')
        timestamp = message.get('timestamp', 0)
        is_read = message.get('read', False)
        structured = message.get('structured', True)
        
        # Create row frame
        row_frame = QFrame()
        row_frame.setObjectName("messageRow")
        # TESTING: No stylesheet on row frame
        row_frame.setCursor(QCursor(Qt.PointingHandCursor))
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(8, 6, 8, 6)
        row_layout.setSpacing(10)
        
        # Checkbox for selection - no styling, use Qt defaults
        checkbox = QCheckBox()
        checkbox.stateChanged.connect(self._update_selection_count)
        row_layout.addWidget(checkbox)
        
        # Store reference
        items_list.append((checkbox, message_id))
        
        # Message content
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)
        
        # Direction label
        if direction == 'sent':
            dir_label = "Sent:"
        elif is_bulletin:
            dir_label = "Bulletin:"
        else:
            dir_label = "Received:"
        
        # From/To display
        if direction == 'sent':
            if is_bulletin:
                from_to = "To: Everyone"
            elif len(to_ids) > 1:
                from_to = f"To: {len(to_ids)} nodes"
            else:
                from_to = f"To: {to_ids[0] if to_ids else 'Unknown'}"
        else:
            from_to = f"From: {from_name}"
        
        # Clean text for display
        clean_text = ''.join(c for c in text if c.isprintable() or c == ' ')
        preview = clean_text[:120] + "..." if len(clean_text) > 120 else clean_text
        
        # Status indicators
        status_icons = []
        if direction == 'received' and not is_read:
            status_icons.append("[UNREAD]")
        elif direction == 'sent' and structured:
            read_receipts = message.get('read_receipts', {})
            if read_receipts:
                read_count = sum(1 for r in read_receipts.values() if r.get('read'))
                total_recipients = len(to_ids)
                if read_count > 0:
                    if read_count == total_recipients:
                        status_icons.append(f"✓✓ Read by all ({read_count})")
                    else:
                        status_icons.append(f"✓ Read by {read_count}/{total_recipients}")
        
        if not structured:
            status_icons.append("[Plain]")
        
        if status_icons:
            preview = " ".join(status_icons) + " • " + preview
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%m/%d %H:%M")
        
        if direction == 'sent' and structured:
            read_receipts = message.get('read_receipts', {})
            if read_receipts:
                read_times = [r.get('read_at') for r in read_receipts.values() if r.get('read_at')]
                if read_times:
                    latest_read = max(read_times)
                    read_dt = datetime.fromtimestamp(latest_read)
                    time_str = f"Sent {time_str}, Read {read_dt.strftime('%m/%d %H:%M')}"
        
        # Top line: direction + from/to + time
        top_line = QHBoxLayout()
        top_line.setSpacing(10)
        
        dir_lbl = QLabel(dir_label)
        dir_lbl.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 12pt; font-weight: bold;")
        top_line.addWidget(dir_lbl)
        
        from_to_lbl = QLabel(from_to)
        from_to_lbl.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 12pt;")
        top_line.addWidget(from_to_lbl)
        
        top_line.addStretch()
        
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 11pt;")
        top_line.addWidget(time_lbl)
        
        content_layout.addLayout(top_line)
        
        # Preview line
        preview_lbl = QLabel(preview)
        preview_lbl.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 12pt;")
        preview_lbl.setWordWrap(True)
        content_layout.addWidget(preview_lbl)
        
        row_layout.addWidget(content_widget, stretch=1)
        
        # Make row clickable (but not checkbox)
        def on_row_click(event):
            # Check if click was on checkbox area
            checkbox_rect = checkbox.geometry()
            click_pos = event.position().toPoint()  # Use position() to avoid deprecation warning
            if click_pos.x() > checkbox_rect.right() + 5:
                if self.on_view_message_callback:
                    self.on_view_message_callback(message_id)
                    # Refresh after viewing
                    QTimer.singleShot(500, self._refresh_all_tabs)
        
        row_frame.mousePressEvent = on_row_click
        
        return row_frame
    
    def _update_selection_count(self):
        """Update the selection count label"""
        count = self._get_selected_count()
        if count == 0:
            self.selection_label.setText("No selection")
        elif count == 1:
            self.selection_label.setText("1 message selected")
        else:
            self.selection_label.setText(f"{count} messages selected")
    
    def _get_selected_count(self) -> int:
        """Get count of selected checkboxes"""
        count = 0
        for checkbox, _ in self.inbox_items + self.sent_items + self.archived_items:
            if checkbox.isChecked():
                count += 1
        return count
    
    def _get_selected_message_ids(self) -> List[str]:
        """Get list of selected message IDs"""
        selected = []
        for checkbox, message_id in self.inbox_items + self.sent_items + self.archived_items:
            if checkbox.isChecked():
                selected.append(message_id)
        return selected
    
    def _on_view_selected(self):
        """View the selected message(s)"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select a message to view.")
            return
        
        if len(selected) > 1:
            QMessageBox.warning(self, "Multiple Selection", "Please select only one message to view.")
            return
        
        message_id = selected[0]
        if self.on_view_message_callback:
            self.on_view_message_callback(message_id)
            QTimer.singleShot(500, self._refresh_all_tabs)
    
    def _on_reply_selected(self):
        """Reply to the selected message"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select a message to reply to.")
            return
        
        if len(selected) > 1:
            QMessageBox.warning(self, "Multiple Selection", "Please select only one message to reply to.")
            return
        
        message_id = selected[0]
        message = self.message_manager.get_message_by_id(message_id)
        if message:
            if message.get('direction') == 'received':
                reply_to_id = message.get('from_node_id')
            else:
                to_ids = message.get('to_node_ids', [])
                reply_to_id = to_ids[0] if to_ids else None
            
            if reply_to_id and self.on_send_message_callback:
                self.on_send_message_callback(reply_to_id)
    
    def _on_archive_selected(self):
        """Archive the selected message(s)"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select message(s) to archive.")
            return
        
        archived_count = 0
        for message_id in selected:
            if self.message_manager.archive_message(message_id):
                archived_count += 1
        
        if archived_count > 0:
            logger.info(f"Archived {archived_count} message(s)")
            self._refresh_all_tabs()
            QMessageBox.information(self, "Archived", f"Archived {archived_count} message(s).")
    
    def _on_delete_selected(self):
        """Delete the selected message(s)"""
        selected = self._get_selected_message_ids()
        
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select message(s) to delete.")
            return
        
        count = len(selected)
        result = QMessageBox.warning(
            self,
            "Delete Messages",
            f"Are you sure you want to delete {count} message(s)?\n\n"
            "⚠️ Warning: For EmComm/emergency use, consider Archive instead.\n"
            "Deleted messages cannot be recovered.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            deleted_count = 0
            for message_id in selected:
                self.message_manager.delete_message(message_id)
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} message(s)")
                self._refresh_all_tabs()
    
    def _on_compose(self):
        """Handle compose button click - show node selector"""
        if not hasattr(self.parent_window, 'data_collector') or not self.parent_window.data_collector:
            logger.warning("No data collector available")
            return
        
        nodes_data = self.parent_window.data_collector.get_nodes_data()
        if not nodes_data:
            QMessageBox.information(self, "No Nodes", "No nodes available to send message to.")
            return
        
        # Create node selector dialog
        selector = QDialog(self)
        selector.setWindowTitle("Select Recipient")
        selector.setMinimumSize(480, 500)
        selector.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['bg_frame']};
            }}
            QLabel {{
                color: {self.colors['fg_normal']};
            }}
            QScrollArea {{
                background-color: {self.colors['bg_main']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['bg_frame']};
                width: 20px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #555555;
                min-height: 30px;
            }}
        """)
        
        layout = QVBoxLayout(selector)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Select recipient(s):")
        title.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 12pt; font-weight: bold;")
        layout.addWidget(title)
        
        # Scrollable checkbox list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {self.colors['bg_main']};")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        node_checkboxes = {}
        for node_id, node_data in sorted(nodes_data.items(), key=lambda x: x[1].get('Node LongName', x[0])):
            node_name = node_data.get('Node LongName', node_id)
            display_name = f"{node_name} ({node_id})"
            
            cb = QCheckBox(display_name)
            scroll_layout.addWidget(cb)
            node_checkboxes[node_id] = cb
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        compose_btn = create_button("Compose", "success")
        cancel_btn = create_cancel_button()
        
        def on_compose_click():
            selected_nodes = [(nid, nodes_data[nid].get('Node LongName', nid))
                            for nid, cb in node_checkboxes.items() if cb.isChecked()]
            
            if not selected_nodes:
                QMessageBox.warning(selector, "No Selection", "Please select at least one recipient.")
                return
            
            selector.accept()
            
            selected_node_id = selected_nodes[0][0]
            if len(selected_nodes) > 1:
                QMessageBox.information(
                    self,
                    "Note",
                    f"Multiple recipients selected. Opening compose for {selected_nodes[0][1]}.\n"
                    "Multi-recipient messaging will be supported in a future update."
                )
            
            if self.on_send_message_callback:
                self.on_send_message_callback(selected_node_id)
        
        compose_btn.clicked.connect(on_compose_click)
        cancel_btn.clicked.connect(selector.reject)
        
        btn_layout.addWidget(compose_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        selector.exec()
    
    def _compute_messages_hash(self) -> str:
        """Compute a hash of current message state for change detection"""
        try:
            all_messages = self.message_manager.load_messages()
            state_data = []
            for msg in all_messages:
                state_data.append((
                    msg.get('message_id', ''),
                    msg.get('read', False),
                    msg.get('archived', False),
                    msg.get('direction', ''),
                    len(msg.get('read_receipts', {}))
                ))
            state_data.sort()
            return str(hash(tuple(state_data)))
        except Exception as e:
            logger.warning(f"Error computing messages hash: {e}")
            return str(hash(str(e)))
    
    def _start_auto_refresh(self):
        """Start auto-refresh timer (2 second interval)"""
        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._on_auto_refresh)
        self._auto_refresh_timer.start(2000)
    
    def _on_auto_refresh(self):
        """Handle auto-refresh timer tick"""
        try:
            current_hash = self._compute_messages_hash()
            if current_hash != self._last_messages_hash:
                logger.debug("Message state changed, refreshing tabs")
                self._last_messages_hash = current_hash
                self._refresh_all_tabs()
        except Exception as e:
            logger.warning(f"Auto-refresh error: {e}")
    
    def closeEvent(self, event):
        """Handle window close"""
        if self._auto_refresh_timer:
            self._auto_refresh_timer.stop()
        event.accept()


# Test standalone
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    # Mock message manager for testing
    class MockMessageManager:
        def load_messages(self):
            return [
                # INBOX - Received messages (not archived)
                {
                    'message_id': 'msg1',
                    'direction': 'received',
                    'from_name': 'TestNode',
                    'from_node_id': '!abc123',
                    'to_node_ids': ['!local'],
                    'text': 'Hello, this is a test message from the mesh network.',
                    'timestamp': 1702800000,
                    'read': False,
                    'archived': False,
                    'structured': True
                },
                {
                    'message_id': 'msg4',
                    'direction': 'received',
                    'from_name': 'WeatherStation',
                    'from_node_id': '!weather1',
                    'to_node_ids': ['!local'],
                    'text': 'Current conditions: 72F, 45% humidity, wind NW 5mph. Forecast looks good for the weekend.',
                    'timestamp': 1702790000,
                    'read': True,
                    'archived': False,
                    'structured': True
                },
                {
                    'message_id': 'msg5',
                    'direction': 'received',
                    'from_name': 'EmergencyAlert',
                    'from_node_id': '!alert99',
                    'to_node_ids': ['!local'],
                    'text': '[DRILL] This is a test of the emergency broadcast system. No action required.',
                    'timestamp': 1702785000,
                    'read': False,
                    'archived': False,
                    'structured': True,
                    'is_bulletin': True
                },
                {
                    'message_id': 'msg6',
                    'direction': 'received',
                    'from_name': 'HikerBob',
                    'from_node_id': '!hiker42',
                    'to_node_ids': ['!local'],
                    'text': 'Made it to the summit! Great views today. Signal is strong up here.',
                    'timestamp': 1702780000,
                    'read': True,
                    'archived': False,
                    'structured': False
                },
                # SENT messages (not archived)
                {
                    'message_id': 'msg2',
                    'direction': 'sent',
                    'from_name': 'Local',
                    'to_node_ids': ['!abc123'],
                    'text': 'This is a sent message reply.',
                    'timestamp': 1702803600,
                    'read': True,
                    'archived': False,
                    'structured': True,
                    'read_receipts': {'!abc123': {'read': True, 'read_at': 1702804000}}
                },
                {
                    'message_id': 'msg7',
                    'direction': 'sent',
                    'from_name': 'Local',
                    'to_node_ids': ['!weather1'],
                    'text': 'Thanks for the weather update! Will plan accordingly.',
                    'timestamp': 1702791000,
                    'read': True,
                    'archived': False,
                    'structured': True,
                    'read_receipts': {}
                },
                {
                    'message_id': 'msg8',
                    'direction': 'sent',
                    'from_name': 'Local',
                    'to_node_ids': ['!hiker42', '!base1'],
                    'text': 'Checking in - all stations report status please.',
                    'timestamp': 1702775000,
                    'read': True,
                    'archived': False,
                    'structured': True,
                    'read_receipts': {'!hiker42': {'read': True, 'read_at': 1702776000}}
                },
                # ARCHIVED messages
                {
                    'message_id': 'msg3',
                    'direction': 'received',
                    'from_name': 'OldNode',
                    'from_node_id': '!def456',
                    'to_node_ids': ['!local'],
                    'text': 'This message has been archived.',
                    'timestamp': 1702700000,
                    'read': True,
                    'archived': True,
                    'structured': True
                },
                {
                    'message_id': 'msg9',
                    'direction': 'sent',
                    'from_name': 'Local',
                    'to_node_ids': ['!oldnode1'],
                    'text': 'Old sent message that was archived for record keeping.',
                    'timestamp': 1702600000,
                    'read': True,
                    'archived': True,
                    'structured': True
                },
                {
                    'message_id': 'msg10',
                    'direction': 'received',
                    'from_name': 'NetControl',
                    'from_node_id': '!netctrl',
                    'to_node_ids': ['!local'],
                    'text': 'Net check complete. All stations accounted for. Next check 1800 local.',
                    'timestamp': 1702500000,
                    'read': True,
                    'archived': True,
                    'structured': True
                }
            ]
        
        def get_message_by_id(self, msg_id):
            for msg in self.load_messages():
                if msg['message_id'] == msg_id:
                    return msg
            return None
        
        def archive_message(self, msg_id):
            return True
        
        def delete_message(self, msg_id):
            return True
    
    # Mock parent with colors
    class MockParent:
        colors = {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'fg_secondary': '#b0b0b0',
            'fg_good': '#228B22',
            'fg_warning': '#FFA500',
            'fg_bad': '#FF6B9D',
            'accent': '#4a90d9',
            'button_bg': '#0d47a1',
            'button_fg': '#ffffff'
        }
        data_collector = None
        
        def geometry(self):
            class Geo:
                def x(self): return 100
                def y(self): return 100
            return Geo()
    
    app = QApplication(sys.argv)
    
    mock_parent = MockParent()
    mock_manager = MockMessageManager()
    
    def on_view(msg_id):
        print(f"View message: {msg_id}")
    
    def on_send(node_id):
        print(f"Send to: {node_id}")
    
    window = MessageListWindowQt(None, mock_manager, on_view, on_send)
    window.colors = mock_parent.colors
    window.show()
    
    sys.exit(app.exec())

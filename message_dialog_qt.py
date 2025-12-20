"""
Message Dialog (Qt/PySide6) for sending Meshtastic text messages

This is the PySide6 port of message_dialog.py. For touchscreen virtual keyboard
support on Raspberry Pi, Qt's built-in virtual keyboard can be enabled via
QT_IM_MODULE=qtvirtualkeyboard environment variable, or a custom Qt keyboard
widget can be added later.

Usage:
    from message_dialog_qt import MessageDialogQt
    
    dialog = MessageDialogQt(parent, node_id, node_name, send_callback)
    dialog.exec()
"""

import logging
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette

from qt_styles import create_button, create_send_button, create_cancel_button, COLORS, get_font

logger = logging.getLogger(__name__)

# Meshtastic maximum payload length is 233 bytes
# Protocol overhead: [MSG:a20a0de0_1765667875991] = 28 bytes
# Available for user text: 233 - 28 = 205 bytes
# Using 180 bytes to leave margin for safety
MAX_MESSAGE_LENGTH = 180


class MessageDialogQt(QDialog):
    """Qt dialog for composing and sending text messages to Meshtastic nodes"""
    
    message_sent = Signal(str, str, bool)  # node_id, message, bell_flag
    
    def __init__(self, parent, node_id: str, node_name: str, 
                 send_callback: Callable[[str, str, bool], None],
                 positioning_parent: Optional[object] = None):
        """
        Create a message dialog
        
        Args:
            parent: Parent window
            node_id: Target node ID (e.g., "!a20a0de0")
            node_name: Display name for the node
            send_callback: Function to call when sending - callback(node_id, message, bell_unused)
            positioning_parent: Window to position relative to (defaults to parent)
        """
        super().__init__(parent)
        
        self.node_id = node_id
        self.node_name = node_name
        self.send_callback = send_callback
        self.result = None
        
        # Get colors from parent (dark theme) or use defaults
        self.colors = getattr(parent, 'colors', {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'fg_secondary': '#b0b0b0',
            'button_bg': '#0d47a1',
            'fg_good': '#228B22',
            'fg_bad': '#FF6B9D'
        })
        
        self.setWindowTitle(f"Send Message to {node_name}")
        self.setMinimumSize(630, 200)
        self.setModal(True)
        
        # Use FramelessWindowHint - Wayland may allow positioning frameless windows
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # Apply dark theme (with border since frameless)
        self._apply_dark_theme()
        
        self._create_widgets()
        
        # Position at top of screen for virtual keyboard
        self._position_for_keyboard()
    
    def _apply_dark_theme(self):
        """Apply dark theme colors to dialog"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['bg_frame']};
                border: 2px solid #555;
                border-radius: 8px;
            }}
            QLabel {{
                color: {self.colors['fg_normal']};
            }}
            QTextEdit {{
                background-color: {self.colors['bg_main']};
                color: {self.colors['fg_normal']};
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }}
            QScrollBar:vertical {{
                background-color: {self.colors['bg_main']};
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #555;
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #666;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QPushButton {{
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12pt;
            }}
        """)
    
    def _position_for_keyboard(self):
        """Position dialog at top of screen to leave room for virtual keyboard"""
        self.adjustSize()
        screen = self.screen().geometry()
        dialog_width = max(self.width(), 630)
        dialog_height = max(self.height(), 200)
        x = (screen.width() - dialog_width) // 2
        y = 10  # Near top of screen for keyboard room
        # Use setGeometry which may work better on some Wayland compositors
        self.setGeometry(x, y, dialog_width, dialog_height)
    
    def _create_widgets(self):
        """Create dialog widgets"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Header with recipient info and close button
        header_layout = QHBoxLayout()
        
        to_label = QLabel("To:")
        to_label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt;")
        header_layout.addWidget(to_label)
        
        recipient_label = QLabel(f" {self.node_name} ({self.node_id})")
        recipient_label.setStyleSheet(f"color: {self.colors['fg_normal']}; font-size: 12pt; font-weight: bold;")
        header_layout.addWidget(recipient_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Message label
        msg_label = QLabel("Message:")
        msg_label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt;")
        layout.addWidget(msg_label)
        
        # Text area for message
        self.text_area = QTextEdit()
        self.text_area.setMinimumHeight(60)
        self.text_area.setMaximumHeight(80)
        self.text_area.setPlaceholderText("Type your message here...")
        self.text_area.setFont(QFont("Liberation Sans", 12))
        self.text_area.textChanged.connect(self._on_text_change)
        layout.addWidget(self.text_area)
        
        # Button row with character counter on left
        button_layout = QHBoxLayout()
        
        self.char_count_label = QLabel(f"0/{MAX_MESSAGE_LENGTH}")
        self.char_count_label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt; background: transparent;")
        button_layout.addWidget(self.char_count_label)
        
        button_layout.addStretch()
        
        cancel_btn = create_cancel_button(self._cancel)
        button_layout.addWidget(cancel_btn)
        
        send_btn = create_send_button(self._send_message)
        button_layout.addWidget(send_btn)
        
        layout.addLayout(button_layout)
        
        # Set focus to text area
        self.text_area.setFocus()
    
    def _on_text_change(self):
        """Update character count and enforce limit"""
        text = self.text_area.toPlainText()
        text_bytes = text.encode('utf-8')
        byte_count = len(text_bytes)
        
        # Update counter
        self.char_count_label.setText(f"{byte_count}/{MAX_MESSAGE_LENGTH}")
        
        # Change color based on length
        if byte_count > MAX_MESSAGE_LENGTH:
            self.char_count_label.setStyleSheet("color: #FF6B9D; font-size: 12pt; background: transparent;")  # Coral pink for error
            
            # Trim to max length
            while byte_count > MAX_MESSAGE_LENGTH and text:
                text = text[:-1]
                text_bytes = text.encode('utf-8')
                byte_count = len(text_bytes)
            
            # Block signals to prevent recursion
            self.text_area.blockSignals(True)
            cursor = self.text_area.textCursor()
            cursor_pos = cursor.position()
            self.text_area.setPlainText(text)
            # Restore cursor position (at end if beyond new length)
            cursor.setPosition(min(cursor_pos, len(text)))
            self.text_area.setTextCursor(cursor)
            self.text_area.blockSignals(False)
            
            # Update count after trim
            self.char_count_label.setText(f"{byte_count}/{MAX_MESSAGE_LENGTH}")
            
        elif byte_count > MAX_MESSAGE_LENGTH * 0.9:
            self.char_count_label.setStyleSheet("color: #FFA500; font-size: 12pt; background: transparent;")  # Orange for warning
        else:
            self.char_count_label.setStyleSheet(f"color: {self.colors['fg_secondary']}; font-size: 12pt; background: transparent;")
    
    def _send_message(self):
        """Send the message"""
        text = self.text_area.toPlainText().strip()
        
        if not text:
            QMessageBox.warning(self, "Empty Message", "Please enter a message to send.")
            return
        
        # Check byte length
        text_bytes = text.encode('utf-8')
        if len(text_bytes) > MAX_MESSAGE_LENGTH:
            QMessageBox.critical(self, "Message Too Long",
                               f"Message is {len(text_bytes)} bytes, maximum is {MAX_MESSAGE_LENGTH} bytes.")
            return
        
        logger.info(f"Sending message to {self.node_id} ({self.node_name}): {repr(text)}")
        
        # Call the send callback
        try:
            self.send_callback(self.node_id, text, False)
            self.result = "sent"
            self.accept()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            QMessageBox.critical(self, "Send Error", f"Failed to send message: {e}")
    
    def _cancel(self):
        """Cancel and close dialog"""
        self.result = "cancelled"
        self.reject()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Ctrl+Enter to send
        if event.key() == Qt.Key_Return and event.modifiers() & Qt.ControlModifier:
            self._send_message()
        # Escape to cancel
        elif event.key() == Qt.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)


# Test harness for standalone testing
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    def mock_send(node_id, message, bell):
        print(f"MOCK SEND: to={node_id}, message={message}, bell={bell}")
    
    app = QApplication(sys.argv)
    
    # Create a mock parent with colors
    class MockParent:
        colors = {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'fg_secondary': '#b0b0b0',
            'button_bg': '#0d47a1',
            'fg_good': '#228B22',
            'fg_bad': '#FF6B9D'
        }
    
    dialog = MessageDialogQt(None, "!a20a0de0", "TestNode", mock_send)
    result = dialog.exec()
    
    print(f"Dialog result: {dialog.result}")
    sys.exit(0)

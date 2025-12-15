"""
Message Viewer Dialog - Display full message with reply/delete options

Shows complete message details including:
- Sender and recipient names
- Timestamp
- Full message text
- Read receipt status (for sent messages)

Actions:
- Reply: Opens MessageDialog pre-filled with recipient
- Delete: Removes message from storage
- Close: Marks as read and sends read receipt (for received messages)
"""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class MessageViewer:
    """Modal dialog for viewing full message details"""
    
    def __init__(self, parent, message_data: Dict[str, Any], 
                 on_reply: Optional[Callable] = None,
                 on_delete: Optional[Callable] = None,
                 on_close: Optional[Callable] = None,
                 on_mark_read: Optional[Callable] = None,
                 on_archive: Optional[Callable] = None,
                 positioning_parent: Optional[Any] = None):
        """Initialize message viewer dialog
        
        Args:
            parent: Parent window (for transient relationship and color scheme)
            message_data: Message dictionary from MessageManager
            on_reply: Callback when Reply clicked - receives (node_id, node_name)
            on_delete: Callback when Delete clicked - receives (message_id)
            on_close: Callback when dialog closes - receives (message_id, direction)
            on_mark_read: Callback when Mark as Read clicked - receives (message_id)
            on_archive: Callback when Archive clicked - receives (message_id)
            positioning_parent: Window to position relative to (defaults to parent)
        """
        self.parent = parent
        self.positioning_parent = positioning_parent if positioning_parent else parent
        self.message_data = message_data
        self.on_reply_callback = on_reply
        self.on_delete_callback = on_delete
        self.on_close_callback = on_close
        self.on_mark_read_callback = on_mark_read
        self.on_archive_callback = on_archive
        
        # Extract message details
        self.message_id = message_data.get('message_id', 'unknown')
        self.from_id = message_data.get('from_node_id', '')
        self.from_name = message_data.get('from_name', 'Unknown')
        self.to_ids = message_data.get('to_node_ids', [])
        self.is_bulletin = message_data.get('is_bulletin', False)
        self.text = message_data.get('text', '')
        self.timestamp = message_data.get('timestamp', 0)
        self.direction = message_data.get('direction', 'received')
        self.read_receipts = message_data.get('read_receipts', {})
        self.archived = message_data.get('archived', False)
        self.structured = message_data.get('structured', True)
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Message from {node_name}")
        self.dialog.geometry("650x500")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.configure(bg=self.colors['bg_frame'])
        
        self._create_widgets()
        
        # Set grab after window is created and visible (fixes Linux timing issue)
        self.dialog.update_idletasks()
        self.dialog.grab_set()
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def _create_widgets(self):
        """Create dialog widgets"""
        # Main content area (scrollable)
        content_frame = tk.Frame(self.dialog, bg=self.colors['bg_frame'])
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header: From/To
        header_frame = tk.Frame(content_frame, bg=self.colors['bg_frame'])
        header_frame.pack(fill="x", pady=(0, 11))
        
        if self.direction == 'sent':
            # Sent message: show "To:"
            to_label = tk.Label(header_frame, text="To:",
                              bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'],
                              font=("Liberation Sans", 12))
            to_label.pack(side="left")
            
            if self.is_bulletin:
                to_value = "All Nodes (Bulletin)"
            elif self.to_ids:
                # Just show first recipient for now (we only support single recipient currently)
                to_value = self.to_ids[0]
            else:
                to_value = "Unknown"
            
            to_name_label = tk.Label(header_frame, text=f" {to_value}",
                                    bg=self.colors['bg_frame'], fg=self.colors['fg_normal'],
                                    font=("Liberation Sans", 12, "bold"))
            to_name_label.pack(side="left")
        else:
            # Received message: show "From:"
            from_label = tk.Label(header_frame, text="From:",
                                bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'],
                                font=("Liberation Sans", 12))
            from_label.pack(side="left")
            
            from_name_label = tk.Label(header_frame, text=f" {self.from_name}",
                                      bg=self.colors['bg_frame'], fg=self.colors['fg_normal'],
                                      font=("Liberation Sans", 12, "bold"))
            from_name_label.pack(side="left")
        
        # Timestamp
        timestamp_frame = tk.Frame(content_frame, bg=self.colors['bg_frame'])
        timestamp_frame.pack(fill="x", pady=(0, 11))
        
        ts_label = tk.Label(timestamp_frame, text="Received:" if self.direction == 'received' else "Sent:",
                          bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'],
                          font=("Liberation Sans", 12))
        ts_label.pack(side="left")
        
        dt = datetime.fromtimestamp(self.timestamp)
        ts_value = tk.Label(timestamp_frame, text=f"{dt.strftime('%Y-%m-%d %H:%M:%S')}",
                          bg=self.colors['bg_frame'], fg=self.colors['fg_normal'],
                          font=("Liberation Sans", 12))
        ts_value.pack(side="left")
        
        # Message text area (scrollable)
        text_label = tk.Label(content_frame, text="Message:",
                            bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'],
                            font=("Liberation Sans", 12))
        text_label.pack(anchor="w", pady=(0, 5))
        
        text_frame = tk.Frame(content_frame, bg=self.colors['bg_frame'], height=80)
        text_frame.pack(fill="x", expand=False)
        text_frame.pack_propagate(False)  # Maintain fixed height
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.text_display = tk.Text(text_frame, wrap="word", 
                                    font=("Liberation Sans", 12),
                                    bg='#1e1e1e', fg=self.colors['fg_normal'],
                                    yscrollcommand=scrollbar.set,
                                    relief="sunken", bd=2,
                                    state="normal",
                                    height=3)
        self.text_display.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_display.yview)
        
        # Insert message text
        self.text_display.insert("1.0", self.text)
        self.text_display.config(state="disabled")  # Make read-only
        
        # Read receipt status (for sent messages)
        if self.direction == 'sent' and self.read_receipts:
            receipt_frame = tk.Frame(content_frame, bg=self.colors['bg_frame'])
            receipt_frame.pack(fill="x", pady=(10, 0))
            
            receipt_label = tk.Label(receipt_frame, text="Read receipts:",
                                   bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'],
                                   font=("Liberation Sans", 12))
            receipt_label.pack(anchor="w")
            
            for node_id, receipt_data in self.read_receipts.items():
                if receipt_data.get('read'):
                    read_at = receipt_data.get('read_at')
                    if read_at:
                        dt = datetime.fromtimestamp(read_at)
                        status_text = f"  ✓ {node_id} read at {dt.strftime('%Y-%m-%d %H:%M:%S')}"
                    else:
                        status_text = f"  ✓ {node_id} read"
                    
                    status_label = tk.Label(receipt_frame, text=status_text,
                                          bg=self.colors['bg_frame'], fg=self.colors['fg_good'],
                                          font=("Liberation Sans", 12))
                    status_label.pack(anchor="w")
        
        # Button bar at bottom
        button_frame = tk.Frame(self.dialog, bg=self.colors['bg_frame'])
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Mark as Read button (only for unread received messages)
        if self.direction == 'received' and not self.message_data.get('read', False) and self.on_mark_read_callback:
            mark_read_btn = tk.Button(button_frame, text="Mark as Read", width=12, height=2,
                                     command=self._on_mark_read,
                                     bg='#2e7d32', fg='white',
                                     font=("Liberation Sans", 12))
            mark_read_btn.pack(side="left", padx=(0, 11))
        
        # Reply button
        if self.on_reply_callback:
            reply_btn = tk.Button(button_frame, text="Reply", width=10, height=2,
                                 command=self._on_reply,
                                 bg='#0d47a1', fg='white',
                                 font=("Liberation Sans", 12))
            reply_btn.pack(side="left", padx=(0, 11))
        
        # Archive button (only if not already archived)
        if not self.archived and self.on_archive_callback:
            archive_btn = tk.Button(button_frame, text="Archive", width=10, height=2,
                                   command=self._on_archive,
                                   bg='#f57c00', fg='white',
                                   font=("Liberation Sans", 12))
            archive_btn.pack(side="left", padx=(0, 11))
        
        # Delete button
        if self.on_delete_callback:
            delete_btn = tk.Button(button_frame, text="Delete...", width=10, height=2,
                                  command=self._on_delete,
                                  bg='#c62828', fg='white',
                                  font=("Liberation Sans", 12))
            delete_btn.pack(side="left", padx=(0, 11))
        
        # Close button (always present on right side)
        close_btn = tk.Button(button_frame, text="Close", width=10, height=2,
                             command=self._on_window_close,
                             bg='#424242', fg='white',
                             font=("Liberation Sans", 12))
        close_btn.pack(side="right")
    
    def _on_mark_read(self):
        """Handle Mark as Read button click"""
        if self.on_mark_read_callback:
            self.on_mark_read_callback(self.message_id)
        self.dialog.destroy()
    
    def _on_reply(self):
        """Handle Reply button click"""
        if self.on_reply_callback:
            # Call reply callback with sender info (to reply to the sender)
            self.on_reply_callback(self.from_id, self.from_name)
        self.dialog.destroy()
    
    def _on_archive(self):
        """Handle Archive button click"""
        if self.on_archive_callback:
            self.on_archive_callback(self.message_id)
        self.dialog.destroy()
    
    def _on_delete(self):
        """Handle Delete button click"""
        # Confirm deletion with EmComm warning
        result = messagebox.askyesno(
            "Delete Message",
            "Are you sure you want to delete this message?\n\n"
            "⚠️ Warning: For EmComm/emergency use, consider Archive instead.\n"
            "Deleted messages cannot be recovered.",
            parent=self.dialog,
            icon='warning'
        )
        if result:
            if self.on_delete_callback:
                self.on_delete_callback(self.message_id)
            self.dialog.destroy()
    
    def _on_window_close(self):
        """Handle dialog close (X button or Close button)"""
        if self.on_close_callback:
            # Notify parent that viewer is closing (for marking as read, etc.)
            self.on_close_callback(self.message_id, self.direction)
        self.dialog.destroy()

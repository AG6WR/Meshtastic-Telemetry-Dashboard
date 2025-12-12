"""
Message Dialog for sending Meshtastic text messages
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)

# Meshtastic maximum payload length is 233 bytes
# But text messages should be conservative to allow for encoding overhead
MAX_MESSAGE_LENGTH = 200

class MessageDialog:
    """Dialog for composing and sending text messages to Meshtastic nodes"""
    
    def __init__(self, parent, node_id: str, node_name: str, send_callback: Callable[[str, str, bool], None]):
        """
        Create a message dialog
        
        Args:
            parent: Parent window
            node_id: Target node ID (e.g., "!a20a0de0")
            node_name: Display name for the node
            send_callback: Function to call when sending - callback(node_id, message, send_bell)
        """
        self.parent = parent
        self.node_id = node_id
        self.node_name = node_name
        self.send_callback = send_callback
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Send Message to {node_name}")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.dialog.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self._create_widgets()
        
        # Set focus to text area
        self.text_area.focus_set()
        
    def _create_widgets(self):
        """Create dialog widgets"""
        # Header
        header_frame = tk.Frame(self.dialog)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(header_frame, text=f"To: {self.node_name} ({self.node_id})", 
                font=("Courier New", 11, "bold")).pack(anchor="w")
        
        # Message text area with scrollbar
        text_frame = tk.Frame(self.dialog)
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        tk.Label(text_frame, text="Message:", font=("Courier New", 10)).pack(anchor="w")
        
        text_container = tk.Frame(text_frame)
        text_container.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side="right", fill="y")
        
        self.text_area = tk.Text(text_container, 
                                 wrap="word", 
                                 font=("Courier New", 10),
                                 yscrollcommand=scrollbar.set)
        self.text_area.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_area.yview)
        
        # Bind text change event
        self.text_area.bind('<<Modified>>', self._on_text_change)
        self.text_area.bind('<KeyRelease>', self._on_text_change)
        
        # Character counter
        counter_frame = tk.Frame(self.dialog)
        counter_frame.pack(fill="x", padx=10, pady=5)
        
        self.char_count_label = tk.Label(counter_frame, 
                                         text=f"0/{MAX_MESSAGE_LENGTH}",
                                         font=("Courier New", 9))
        self.char_count_label.pack(side="right")
        
        # Bell character option
        self.send_bell_var = tk.BooleanVar(value=False)
        bell_check = tk.Checkbutton(counter_frame, 
                                    text="Send bell character (\\a) to alert",
                                    variable=self.send_bell_var,
                                    font=("Courier New", 9))
        bell_check.pack(side="left")
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(button_frame, text="Send", command=self._send_message,
                 width=10, font=("Courier New", 10, "bold")).pack(side="right", padx=5)
        tk.Button(button_frame, text="Cancel", command=self._cancel,
                 width=10, font=("Courier New", 10)).pack(side="right")
        
        # Bind Enter key (Ctrl+Enter to send)
        self.dialog.bind('<Control-Return>', lambda e: self._send_message())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
        
    def _on_text_change(self, event=None):
        """Update character count and enforce limit"""
        # Get current text
        text = self.text_area.get("1.0", "end-1c")
        text_bytes = text.encode('utf-8')
        byte_count = len(text_bytes)
        
        # Update counter
        self.char_count_label.config(text=f"{byte_count}/{MAX_MESSAGE_LENGTH}")
        
        # Change color if approaching/exceeding limit
        if byte_count > MAX_MESSAGE_LENGTH:
            self.char_count_label.config(fg="red")
            # Delete excess characters
            while byte_count > MAX_MESSAGE_LENGTH:
                # Remove last character
                text = text[:-1]
                text_bytes = text.encode('utf-8')
                byte_count = len(text_bytes)
            
            # Update text area
            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", text)
            self.text_area.mark_set("insert", "end")
        elif byte_count > MAX_MESSAGE_LENGTH * 0.9:
            self.char_count_label.config(fg="orange")
        else:
            self.char_count_label.config(fg="black")
        
        # Reset modified flag
        self.text_area.edit_modified(False)
    
    def _send_message(self):
        """Send the message"""
        text = self.text_area.get("1.0", "end-1c").strip()
        
        if not text:
            messagebox.showwarning("Empty Message", "Please enter a message to send.", parent=self.dialog)
            return
        
        # Check byte length
        text_bytes = text.encode('utf-8')
        if len(text_bytes) > MAX_MESSAGE_LENGTH:
            messagebox.showerror("Message Too Long", 
                               f"Message is {len(text_bytes)} bytes, maximum is {MAX_MESSAGE_LENGTH} bytes.",
                               parent=self.dialog)
            return
        
        # Add bell character if requested
        send_bell = self.send_bell_var.get()
        if send_bell:
            text = "\a" + text  # Bell character at start
        
        logger.info(f"Sending message to {self.node_id} ({self.node_name}): {repr(text)}")
        
        # Call the send callback
        try:
            self.send_callback(self.node_id, text, send_bell)
            self.result = "sent"
            self.dialog.destroy()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            messagebox.showerror("Send Error", f"Failed to send message: {e}", parent=self.dialog)
    
    def _cancel(self):
        """Cancel and close dialog"""
        self.result = "cancelled"
        self.dialog.destroy()
    
    def show(self):
        """Show the dialog and wait for result"""
        self.dialog.wait_window()
        return self.result

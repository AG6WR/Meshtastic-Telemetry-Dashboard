"""
Message Dialog for sending Meshtastic text messages
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional
import logging
from virtual_keyboard import VirtualKeyboard

logger = logging.getLogger(__name__)

# Meshtastic maximum payload length is 233 bytes
# Protocol overhead: [MSG:a20a0de0_1765667875991] = 28 bytes
# Available for user text: 233 - 28 = 205 bytes
# Using 180 bytes to leave margin for safety
MAX_MESSAGE_LENGTH = 180

class MessageDialog:
    """Dialog for composing and sending text messages to Meshtastic nodes"""
    
    def __init__(self, parent, node_id: str, node_name: str, send_callback: Callable[[str, str, bool], None],
                 positioning_parent: Optional = None):
        """
        Create a message dialog
        
        Args:
            parent: Parent window (for transient relationship and color scheme)
            node_id: Target node ID (e.g., "!a20a0de0")
            node_name: Display name for the node
            send_callback: Function to call when sending - callback(node_id, message, send_bell)
            positioning_parent: Window to position relative to (defaults to parent)
        """
        self.parent = parent
        self.positioning_parent = positioning_parent if positioning_parent else parent
        self.node_id = node_id
        self.node_name = node_name
        self.send_callback = send_callback
        self.result = None
        
        # Get colors from parent (dark theme)
        self.colors = getattr(parent, 'colors', {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'fg_secondary': '#b0b0b0',
            'button_bg': '#0d47a1',
            'fg_good': '#228B22',
            'fg_bad': '#FF6B9D'
        })
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Send Message to {node_name}")
        self.dialog.configure(bg=self.colors['bg_frame'])
        
        # Use overrideredirect for precise positioning (bypasses window manager)
        # Position at top of screen to leave room for keyboard below
        self.dialog.overrideredirect(True)
        
        # Position at top of screen, centered horizontally
        self.dialog.update_idletasks()
        screen_width = self.dialog.winfo_screenwidth()
        dialog_width = 630
        dialog_height = 280  # Increased to fit close button
        x = (screen_width - dialog_width) // 2
        y = 10  # Near top of screen
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        self.dialog.grab_set()
        
        self._create_widgets()
        
        # Create virtual keyboard (hidden initially)
        self.virtual_keyboard = VirtualKeyboard(self.dialog, self.text_area, self.colors)
        self.virtual_keyboard.window.withdraw()  # Start hidden
        
        # Bind events for auto-show/hide keyboard
        self.dialog.bind_all('<FocusIn>', self._on_focus_event, add='+')
        self.dialog.bind_all('<Button-1>', self._on_click_event, add='+')
        
        # Set focus to text area
        self.text_area.focus_set()
        
    def _create_widgets(self):
        """Create dialog widgets"""
        # Header with close button (since overrideredirect removes window decorations)
        header_frame = tk.Frame(self.dialog, bg=self.colors['bg_frame'])
        header_frame.pack(fill="x", padx=10, pady=(5, 5))
        
        tk.Label(header_frame, text=f"To: {self.node_name} ({self.node_id})", 
                font=("Liberation Sans", 12, "bold"),
                bg=self.colors['bg_frame'], fg=self.colors['fg_normal']).pack(side="left", anchor="w")
        
        # Close button in header
        tk.Button(header_frame, text='✕', 
                 bg='#c62828', fg='#ffffff',
                 font=("Liberation Sans", 14, "bold"),
                 relief='flat', bd=0, padx=8, pady=0,
                 command=self._cancel).pack(side="right")
        
        # Message text area with scrollbar
        text_frame = tk.Frame(self.dialog, bg=self.colors['bg_frame'])
        text_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(text_frame, text="Message:", font=("Liberation Sans", 12),
                bg=self.colors['bg_frame'], fg=self.colors['fg_normal']).pack(anchor="w")
        
        text_container = tk.Frame(text_frame, bg=self.colors['bg_frame'])
        text_container.pack(fill="x")
        
        scrollbar = tk.Scrollbar(text_container, bg=self.colors['bg_frame'])
        scrollbar.pack(side="right", fill="y")
        
        self.text_area = tk.Text(text_container, 
                                 wrap="word", 
                                 font=("Liberation Sans", 12),
                                 height=3,  # 3 lines tall (enough for 180 chars)
                                 bg=self.colors['bg_main'], fg=self.colors['fg_normal'],
                                 insertbackground='yellow',  # Bright yellow - highly visible
                                 insertwidth=6,  # VERY wide cursor
                                 insertontime=1000,  # On longer
                                 insertofftime=200,  # Off shorter
                                 yscrollcommand=scrollbar.set)
        self.text_area.pack(side="left", fill="x", expand=True)
        scrollbar.config(command=self.text_area.yview)
        
        # Set focus to text area so cursor is visible
        self.text_area.focus_set()
        
        # Character counter will update when Send is clicked (no bindings to avoid Wayland IME issues)

        
        # Character counter
        counter_frame = tk.Frame(self.dialog, bg=self.colors['bg_frame'])
        counter_frame.pack(fill="x", padx=10, pady=5)
        
        self.char_count_label = tk.Label(counter_frame, 
                                         text=f"0/{MAX_MESSAGE_LENGTH}",
                                         font=("Liberation Sans", 12),
                                         bg=self.colors['bg_frame'], fg=self.colors['fg_secondary'])
        self.char_count_label.pack(side="right")
        
        # Bell character option
        self.send_bell_var = tk.BooleanVar(value=False)
        bell_check = tk.Checkbutton(counter_frame, 
                                    text="Send bell character (\\a) to alert",
                                    variable=self.send_bell_var,
                                    font=("Liberation Sans", 12),
                                    bg=self.colors['bg_frame'], fg=self.colors['fg_normal'],
                                    selectcolor=self.colors['bg_main'],
                                    activebackground=self.colors['bg_frame'],
                                    activeforeground=self.colors['fg_normal'])
        bell_check.pack(side="left")
        
        # Buttons - enlarged for touch input
        button_frame = tk.Frame(self.dialog, bg=self.colors['bg_frame'])
        button_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(button_frame, text="Send", command=self._send_message,
                 width=12, height=2, font=("Liberation Sans", 12, "bold"),
                 bg=self.colors['fg_good'], fg='white').pack(side="right", padx=5)
        tk.Button(button_frame, text="Cancel", command=self._cancel,
                 width=12, height=2, font=("Liberation Sans", 12),
                 bg=self.colors['button_bg'], fg='white').pack(side="right")
        
        # Bind Enter key (Ctrl+Enter to send)
        self.dialog.bind('<Control-Return>', lambda e: self._send_message())
        self.dialog.bind('<Escape>', lambda e: self._cancel())
        
        # Clean up keyboard when dialog closes
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _on_text_change(self, event=None):
        """Update character count and enforce limit"""
        # Get current text
        text = self.text_area.get("1.0", "end-1c")
        text_bytes = text.encode('utf-8')
        byte_count = len(text_bytes)
        
        logger.info(f"_on_text_change called: event={event}, text='{text}', bytes={byte_count}")
        
        # Update counter
        self.char_count_label.config(text=f"{byte_count}/{MAX_MESSAGE_LENGTH}")
        
        # Change color if approaching/exceeding limit
        if byte_count > MAX_MESSAGE_LENGTH:
            logger.info(f"Exceeded limit, trimming from {byte_count} to {MAX_MESSAGE_LENGTH}")
            self.char_count_label.config(fg="#FF6B9D")  # Coral pink for error
            # Delete excess characters
            while byte_count > MAX_MESSAGE_LENGTH:
                # Remove last character
                text = text[:-1]
                text_bytes = text.encode('utf-8')
                byte_count = len(text_bytes)
            
            # Update text area
            logger.info(f"Rewriting text area with trimmed text: '{text}'")
            self.text_area.delete("1.0", "end")
            self.text_area.insert("1.0", text)
            self.text_area.mark_set("insert", "end")
        elif byte_count > MAX_MESSAGE_LENGTH * 0.9:
            self.char_count_label.config(fg="#FFA500")  # Orange for warning
        else:
            self.char_count_label.config(fg=self.colors['fg_secondary'])  # Grey for normal
        
        # Reset modified flag
        self.text_area.edit_modified(False)
    
    def _on_focus_event(self, event):
        """Handle FocusIn events to show keyboard for text widgets"""
        w = event.widget
        logger.info(f"FocusIn event: widget={w}, class={w.winfo_class()}")
        
        # CRITICAL: Don't process events from keyboard's own widgets
        # Walk up the parent chain to check if widget is inside keyboard
        if self.virtual_keyboard and hasattr(self.virtual_keyboard, 'window'):
            parent = w
            while parent:
                if parent == self.virtual_keyboard.window:
                    logger.info(f"Ignoring keyboard widget: {w}")
                    return  # Ignore keyboard's own widgets
                try:
                    parent = parent.master
                except AttributeError:
                    break
            
            # Show keyboard when Text or Entry gets focus
            if w.winfo_class() in ('Text', 'Entry'):
                # Only show if currently hidden
                kb_state = self.virtual_keyboard.window.state()
                logger.info(f"Text/Entry focused, keyboard state: {kb_state}")
                if kb_state == 'withdrawn':
                    logger.info(f"Showing keyboard for widget: {w}")
                    self.virtual_keyboard.target_widget = w
                    self.virtual_keyboard.show()
                else:
                    # Already visible, just update target if needed
                    if self.virtual_keyboard.target_widget != w:
                        logger.info(f"Updating keyboard target: {w}")
                        self.virtual_keyboard.target_widget = w
    
    def _on_click_event(self, event):
        """Handle Button-1 events to hide keyboard when clicking buttons"""
        w = event.widget
        logger.info(f"Button-1 event: widget={w}, class={w.winfo_class()}")
        
        # CRITICAL: Don't process events from keyboard's own widgets
        # Walk up the parent chain to check if widget is inside keyboard
        if self.virtual_keyboard and hasattr(self.virtual_keyboard, 'window'):
            parent = w
            while parent:
                if parent == self.virtual_keyboard.window:
                    logger.info(f"Ignoring keyboard widget click: {w}")
                    return  # Ignore keyboard's own widgets
                try:
                    parent = parent.master
                except AttributeError:
                    break
            
            # Hide keyboard when clicking buttons (but not keyboard's buttons!)
            if w.winfo_class() == 'Button':
                logger.info(f"Hiding keyboard due to button click: {w}")
                self.virtual_keyboard.hide()
                # Give focus back to the clicked button
                w.focus_force()
    
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
        self._cleanup_keyboard()
        self.result = "cancelled"
        self.dialog.destroy()
    
    def _on_close(self):
        """Handle window close event"""
        self._cleanup_keyboard()
        self.dialog.destroy()
    
    def _cleanup_keyboard(self):
        """Clean up virtual keyboard if it exists"""
        if self.virtual_keyboard:
            try:
                self.virtual_keyboard.destroy()
            except:
                pass
            self.virtual_keyboard = None
        
        # Unbind events
        try:
            self.dialog.unbind_all('<FocusIn>')
            self.dialog.unbind_all('<Button-1>')
        except:
            pass
    
    def show(self):
        """Show the dialog and wait for result"""
        self.dialog.wait_window()
        return self.result

"""
Virtual Keyboard for Tkinter Text Widgets
Required for Raspberry Pi kiosk mode where Wayland keyboard doesn't work with Tkinter
"""

import tkinter as tk
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VirtualKeyboard:
    """Virtual keyboard that integrates with Tkinter Text and Entry widgets"""
    
    def __init__(self, parent, target_widget, colors: dict = None):
        """
        Initialize virtual keyboard
        
        Args:
            parent: Parent window
            target_widget: Text or Entry widget to type into
            colors: Color scheme dictionary (optional)
        """
        self.parent = parent
        self.target_widget = target_widget
        self.shift_on = False
        self.caps_lock = False
        
        # Default colors if none provided
        self.colors = colors or {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'button_bg': '#404040',
            'button_active': '#0d47a1'
        }
        
        # Create keyboard window
        self.window = tk.Toplevel(parent)
        self.window.title("Keyboard")
        self.window.configure(bg=self.colors['bg_frame'])
        
        # Position below parent
        self.window.update_idletasks()
        x = parent.winfo_x()
        y = parent.winfo_y() + parent.winfo_height() + 5
        self.window.geometry(f"+{x}+{y}")
        
        # Make it stay on top
        self.window.attributes('-topmost', True)
        
        # Create keyboard layout
        self._create_keyboard()
        
        logger.info("Virtual keyboard created")
    
    def _create_keyboard(self):
        """Create the keyboard layout"""
        main_frame = tk.Frame(self.window, bg=self.colors['bg_frame'], padx=5, pady=5)
        main_frame.pack()
        
        # Row 1: Numbers
        row1_keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=']
        row1_frame = tk.Frame(main_frame, bg=self.colors['bg_frame'])
        row1_frame.pack(pady=2)
        
        for key in row1_keys:
            self._create_key_button(row1_frame, key, width=5)
        
        self._create_key_button(row1_frame, '⌫', width=8, command=self._backspace, bg='#c62828')
        
        # Row 2: QWERTY
        row2_keys = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']']
        row2_frame = tk.Frame(main_frame, bg=self.colors['bg_frame'])
        row2_frame.pack(pady=2)
        
        for key in row2_keys:
            self._create_key_button(row2_frame, key, width=5)
        
        self._create_key_button(row2_frame, '\\', width=5)
        
        # Row 3: ASDFGH
        row3_keys = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"]
        row3_frame = tk.Frame(main_frame, bg=self.colors['bg_frame'])
        row3_frame.pack(pady=2)
        
        self._create_key_button(row3_frame, '⇪', width=8, command=self._caps_lock, bg='#2e7d32')
        
        for key in row3_keys:
            self._create_key_button(row3_frame, key, width=5)
        
        self._create_key_button(row3_frame, '↵', width=8, command=self._enter, bg='#0d47a1')
        
        # Row 4: ZXCVBN
        row4_keys = ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/']
        row4_frame = tk.Frame(main_frame, bg=self.colors['bg_frame'])
        row4_frame.pack(pady=2)
        
        self._create_key_button(row4_frame, '⇧', width=10, command=self._shift, bg='#f57c00')
        
        for key in row4_keys:
            self._create_key_button(row4_frame, key, width=5)
        
        self._create_key_button(row4_frame, '⇧', width=10, command=self._shift, bg='#f57c00')
        
        # Row 5: Space bar and special
        row5_frame = tk.Frame(main_frame, bg=self.colors['bg_frame'])
        row5_frame.pack(pady=2)
        
        self._create_key_button(row5_frame, '!@#', width=8, command=self._symbols, bg='#9c27b0')
        self._create_key_button(row5_frame, ' ', width=40, label='Space')
        self._create_key_button(row5_frame, 'Close', width=12, command=self._close, bg='#424242')
    
    def _create_key_button(self, parent, key, width=5, label=None, command=None, bg=None):
        """Create a key button
        
        Args:
            parent: Parent frame
            key: Key character
            width: Button width
            label: Display label (defaults to key)
            command: Custom command (defaults to _key_press)
            bg: Background color (defaults to button_bg)
        """
        if label is None:
            label = key
        
        if command is None:
            command = lambda k=key: self._key_press(k)
        
        if bg is None:
            bg = self.colors['button_bg']
        
        btn = tk.Button(parent, text=label, width=width, height=2,
                       font=("Liberation Sans", 10),
                       bg=bg, fg='white',
                       command=command,
                       relief='raised', bd=2)
        btn.pack(side='left', padx=2)
        return btn
    
    def _key_press(self, key):
        """Handle key press"""
        # Apply shift/caps transformations
        if self.shift_on or self.caps_lock:
            if key.isalpha():
                key = key.upper()
            else:
                # Shift symbols
                shift_map = {
                    '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
                    '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
                    '-': '_', '=': '+', '[': '{', ']': '}', '\\': '|',
                    ';': ':', "'": '"', ',': '<', '.': '>', '/': '?'
                }
                key = shift_map.get(key, key)
        
        # Insert into target widget
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.insert('insert', key)
            # Trigger any text change events
            self.target_widget.event_generate('<<Modified>>')
            self.target_widget.event_generate('<KeyRelease>')
        elif isinstance(self.target_widget, tk.Entry):
            current_pos = self.target_widget.index('insert')
            self.target_widget.insert(current_pos, key)
        
        # Turn off shift after key press (but not caps lock)
        if self.shift_on:
            self.shift_on = False
    
    def _backspace(self):
        """Handle backspace"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.delete('insert-1c', 'insert')
            self.target_widget.event_generate('<<Modified>>')
            self.target_widget.event_generate('<KeyRelease>')
        elif isinstance(self.target_widget, tk.Entry):
            current_pos = self.target_widget.index('insert')
            if current_pos > 0:
                self.target_widget.delete(current_pos - 1, current_pos)
    
    def _enter(self):
        """Handle enter/return"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.insert('insert', '\n')
            self.target_widget.event_generate('<<Modified>>')
            self.target_widget.event_generate('<KeyRelease>')
    
    def _shift(self):
        """Toggle shift"""
        self.shift_on = not self.shift_on
        logger.debug(f"Shift: {self.shift_on}")
    
    def _caps_lock(self):
        """Toggle caps lock"""
        self.caps_lock = not self.caps_lock
        logger.debug(f"Caps Lock: {self.caps_lock}")
    
    def _symbols(self):
        """Show symbol keyboard (future enhancement)"""
        # For now, just toggle shift for quick symbol access
        self.shift_on = not self.shift_on
    
    def _close(self):
        """Close keyboard"""
        self.window.destroy()
    
    def show(self):
        """Show the keyboard"""
        self.window.deiconify()
    
    def hide(self):
        """Hide the keyboard"""
        self.window.withdraw()
    
    def destroy(self):
        """Destroy the keyboard"""
        self.window.destroy()

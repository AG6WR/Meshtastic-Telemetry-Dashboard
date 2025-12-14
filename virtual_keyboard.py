"""
Virtual Keyboard for Tkinter Text and Entry Widgets
Adapted from vKeyboard by Fantilein1990 (GPL v3)
https://github.com/Fantilein1990/vKeyboard

Required for Raspberry Pi kiosk mode where Wayland keyboard doesn't work with Tkinter

Modifications for Meshtastic Dashboard:
- Ported from Python 2 to Python 3
- Adapted to work with Text widgets (not just Entry)
- Applied dark theme color scheme
- Simplified to singleton pattern (show/hide instead of destroy/recreate)
- Removed page navigation (kept keyboard-only functionality)
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VirtualKeyboard(ttk.Frame):
    """Virtual keyboard optimized for touchscreens with 3-layer layout (lowercase, uppercase, symbols)"""
    
    def __init__(self, parent, target_widget, colors: dict = None):
        """
        Initialize virtual keyboard
        
        Args:
            parent: Parent window
            target_widget: Text or Entry widget to type into
            colors: Color scheme dictionary (optional)
        """
        ttk.Frame.__init__(self, parent)
        
        self.target_widget = target_widget
        self.keysize = 4  # Button width in characters
        
        # Default colors if none provided
        self.colors = colors or {
            'bg_frame': '#2b2b2b',
            'bg_main': '#1e1e1e',
            'fg_normal': '#e0e0e0',
            'button_bg': '#404040',
            'button_special': '#9c27b0'
        }
        
        # Create keyboard window
        self.window = tk.Toplevel(parent)
        self.window.title("Keyboard")
        self.window.configure(bg=self.colors['bg_frame'])
        
        # Don't show at instantiation (will be shown on focus)
        # Position will be set when first shown
        self._positioned = False
        
        # Make it stay on top
        self.window.attributes('-topmost', True)
        
        # Configure button styles
        style = ttk.Style()
        style.configure("vKeyboard.TButton", 
                       font=("Liberation Sans", 10),
                       background=self.colors['button_bg'],
                       foreground='white')
        style.configure("vKeyboardSpecial.TButton",
                       font=("Liberation Sans", 10, "bold"),
                       background=self.colors['button_special'],
                       foreground='white')
        
        # Create container frame
        self.container = tk.Frame(self.window, bg=self.colors['bg_frame'])
        self.container.pack(padx=5, pady=5)
        
        # Define keyboard layouts
        self.lowercase = {
            'row1': ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', 'Bksp'],
            'row2': ['Sym', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
            'row3': ['ABC', 'z', 'x', 'c', 'v', 'b', 'n', 'm', 'ENTER'],
            'row4': ['[ space ]', 'Close']
        }
        self.uppercase = {
            'row1': ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', 'Bksp'],
            'row2': ['Sym', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            'row3': ['abc', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', 'ENTER'],
            'row4': ['[ space ]', 'Close']
        }
        self.symbols = {
            'row1': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'Bksp'],
            'row2': ['abc', '!', '"', '$', '%', '&', '/', '(', ')', '[', ']', '='],
            'row3': ['@', '-', '_', '?', '#', '*', '{', '}', ':', ';', 'ENTER'],
            'row4': ['+', '[ space ]', '.', ',', 'Close']
        }
        
        # Create frames for each keyboard layer
        self.lowercase_frame = tk.Frame(self.container, bg=self.colors['bg_frame'])
        self.lowercase_frame.grid(row=0, column=0, sticky="nsew")
        
        self.uppercase_frame = tk.Frame(self.container, bg=self.colors['bg_frame'])
        self.uppercase_frame.grid(row=0, column=0, sticky="nsew")
        
        self.symbols_frame = tk.Frame(self.container, bg=self.colors['bg_frame'])
        self.symbols_frame.grid(row=0, column=0, sticky="nsew")
        
        # Initialize all keyboard layers
        self._init_keyboard_layer(self.lowercase_frame, self.lowercase)
        self._init_keyboard_layer(self.uppercase_frame, self.uppercase)
        self._init_keyboard_layer(self.symbols_frame, self.symbols)
        
        # Show lowercase by default
        self.lowercase_frame.tkraise()
        
        logger.info("Virtual keyboard created")
    
    def _init_keyboard_layer(self, frame, layout):
        """Initialize a keyboard layer with buttons"""
        rows = []
        for i in range(1, 5):
            row_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
            row_frame.grid(row=i)
            rows.append(row_frame)
        
        # Row 1
        for i, key in enumerate(layout['row1']):
            if key == 'Bksp':
                width = self.keysize * 2
                style = "vKeyboardSpecial.TButton"
            else:
                width = self.keysize
                style = "vKeyboard.TButton"
            
            ttk.Button(rows[0], text=key, width=width, style=style,
                      command=lambda k=key: self._key_press(k)).grid(row=0, column=i, padx=1, pady=1)
        
        # Row 2
        for i, key in enumerate(layout['row2']):
            if key in ['Sym', 'abc']:
                width = self.keysize * 1.5
                style = "vKeyboardSpecial.TButton"
            else:
                width = self.keysize
                style = "vKeyboard.TButton"
            
            ttk.Button(rows[1], text=key, width=width, style=style,
                      command=lambda k=key: self._key_press(k)).grid(row=0, column=i+2, padx=1, pady=1)
        
        # Row 3
        for i, key in enumerate(layout['row3']):
            if key in ['ABC', 'abc']:
                width = self.keysize * 1.5
                style = "vKeyboardSpecial.TButton"
            elif key == 'ENTER':
                width = self.keysize * 2.5
                style = "vKeyboardSpecial.TButton"
            else:
                width = self.keysize
                style = "vKeyboard.TButton"
            
            ttk.Button(rows[2], text=key, width=width, style=style,
                      command=lambda k=key: self._key_press(k)).grid(row=0, column=i+2, padx=1, pady=1)
        
        # Row 4
        col = 3
        for key in layout['row4']:
            if key == '[ space ]':
                width = self.keysize * 6
                text = '     '
            elif key == 'Close':
                width = self.keysize * 2
                text = key
            else:
                width = self.keysize
                text = key
            
            ttk.Button(rows[3], text=text, width=width, style="vKeyboard.TButton",
                      command=lambda k=key: self._key_press(k)).grid(row=0, column=col, padx=1, pady=1)
            col += 1
    
    def _key_press(self, key):
        """Handle key press"""
        if key == 'Sym':
            self.symbols_frame.tkraise()
        elif key == 'abc':
            self.lowercase_frame.tkraise()
        elif key == 'ABC':
            self.uppercase_frame.tkraise()
        elif key == 'Bksp':
            self._backspace()
        elif key == 'ENTER':
            self._enter()
        elif key == 'Close':
            self._close()
        elif key == '[ space ]':
            self._insert_char(' ')
        else:
            self._insert_char(key)
    
    def _insert_char(self, char):
        """Insert character into target widget"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.insert('insert', char)
            self.target_widget.event_generate('<<Modified>>')
            self.target_widget.event_generate('<KeyRelease>')
        elif isinstance(self.target_widget, tk.Entry):
            current_pos = self.target_widget.index('insert')
            self.target_widget.insert(current_pos, char)
    
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
    
    def _close(self):
        """Close keyboard"""
        self.window.destroy()
    
    def show(self):
        """Show the keyboard"""
        # Position below parent on first show
        if not self._positioned:
            self.window.update_idletasks()
            parent = self.window.master
            x = parent.winfo_x()
            y = parent.winfo_y() + parent.winfo_height() + 5
            self.window.geometry(f"+{x}+{y}")
            self._positioned = True
        
        self.window.deiconify()
    
    def hide(self):
        """Hide the keyboard"""
        self.window.withdraw()
    
    def destroy(self):
        """Destroy the keyboard"""
        self.window.destroy()

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
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VirtualKeyboard:
    """Virtual keyboard optimized for touchscreens with 3-layer layout (lowercase, uppercase, symbols)"""
    
    def __init__(self, parent, target_widget, colors: dict = None):
        """
        Initialize virtual keyboard
        
        Args:
            parent: Parent window
            target_widget: Text or Entry widget to type into
            colors: Color scheme dictionary (optional)
        """
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
        
        # Key color scheme
        self.key_colors = {
            'letter': {'bg': '#404040', 'fg': '#ffffff'},      # Dark grey, white text
            'punctuation': {'bg': '#505050', 'fg': '#d0d0d0'}, # Medium grey, light grey text
            'special': {'bg': '#9c27b0', 'fg': '#ffffff'},     # Purple for mode switches
            'action': {'bg': '#0d47a1', 'fg': '#ffffff'},      # Blue for enter/backspace
            'close': {'bg': '#c62828', 'fg': '#ffffff'}        # Red for close
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
        
        # Create container frame
        self.container = tk.Frame(self.window, bg=self.colors['bg_frame'])
        self.container.pack(padx=5, pady=5)
        
        # Define keyboard layouts
        self.lowercase = {
            'row1': ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Bksp'],
            'row2': ['Tab', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],
            'row3': ['Caps', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'Enter'],
            'row4': ['Shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'Shift'],
            'row5': ['Sym', 'space', 'Close']
        }
        self.uppercase = {
            'row1': ['~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', 'Bksp'],
            'row2': ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '|'],
            'row3': ['Caps', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', 'Enter'],
            'row4': ['Shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?', 'Shift'],
            'row5': ['abc', 'space', 'Close']
        }
        self.symbols = {
            'row1': ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Bksp'],
            'row2': ['Tab', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '[', ']', '\\'],
            'row3': ['abc', '+', '=', '-', '_', '/', '\\', '|', '{', '}', ';', ':', 'Enter'],
            'row4': ['Shift', '<', '>', ',', '.', '?', '!', '"', "'", '`', '~', 'Shift'],
            'row5': ['abc', 'space', 'Close']
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
        # Row 1 - number/symbol row - NO stagger
        row1_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row1_frame.pack()
        for key in layout['row1']:
            width, colors = self._get_key_style(key)
            tk.Button(row1_frame, text=key, width=width,
                     font=("Liberation Sans", 10, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='raised', bd=2,
                     command=lambda k=key: self._key_press(k)).pack(side='left', padx=1, pady=1)
        
        # Row 2 - qwerty row - stagger 1/4 key (8 pixels)
        row2_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row2_frame.pack()
        tk.Frame(row2_frame, width=8, bg=self.colors['bg_frame']).pack(side='left')
        for key in layout['row2']:
            width, colors = self._get_key_style(key)
            tk.Button(row2_frame, text=key, width=width,
                     font=("Liberation Sans", 10, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='raised', bd=2,
                     command=lambda k=key: self._key_press(k)).pack(side='left', padx=1, pady=1)
        
        # Row 3 - asdf row - stagger 2/4 key (16 pixels)
        row3_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row3_frame.pack()
        tk.Frame(row3_frame, width=16, bg=self.colors['bg_frame']).pack(side='left')
        for key in layout['row3']:
            width, colors = self._get_key_style(key)
            tk.Button(row3_frame, text=key, width=width,
                     font=("Liberation Sans", 10, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='raised', bd=2,
                     command=lambda k=key: self._key_press(k)).pack(side='left', padx=1, pady=1)
        
        # Row 4 - zxcv row - stagger 3/4 key (24 pixels)
        row4_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row4_frame.pack()
        tk.Frame(row4_frame, width=24, bg=self.colors['bg_frame']).pack(side='left')
        for key in layout['row4']:
            width, colors = self._get_key_style(key)
            tk.Button(row4_frame, text=key, width=width,
                     font=("Liberation Sans", 10, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='raised', bd=2,
                     command=lambda k=key: self._key_press(k)).pack(side='left', padx=1, pady=1)
        
        # Row 5 - space bar row
        row5_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row5_frame.pack()
        for key in layout['row5']:
            if key == 'space':
                width = int(self.keysize * 20)  # Wide space bar
                text = ' '
                colors = self.key_colors['letter']
            else:
                width, colors = self._get_key_style(key)
                text = key
            
            tk.Button(row5_frame, text=text, width=width,
                     font=("Liberation Sans", 10, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='raised', bd=2,
                     command=lambda k=key: self._key_press(k)).pack(side='left', padx=1, pady=1)
    
    def _get_key_style(self, key):
        """Get width and colors for a key"""
        # Modifier keys (wider)
        if key in ['Tab', 'Bksp']:
            return int(self.keysize * 1.5), self.key_colors['action']
        elif key in ['Caps', 'Enter']:
            return int(self.keysize * 1.75), self.key_colors['action']
        elif key in ['Shift']:
            return int(self.keysize * 2), self.key_colors['action']
        elif key in ['Sym', 'abc']:
            return int(self.keysize * 1.5), self.key_colors['special']
        elif key == 'Close':
            return int(self.keysize * 2), self.key_colors['close']
        # Letter keys
        elif key.isalpha():
            return int(self.keysize), self.key_colors['letter']
        # Punctuation/numbers
        else:
            return int(self.keysize), self.key_colors['punctuation']
    
    def _key_press(self, key):
        """Handle key press"""
        # Mode switching
        if key == 'Sym':
            self.symbols_frame.tkraise()
        elif key == 'abc':
            self.lowercase_frame.tkraise()
        elif key == 'Caps':
            self.uppercase_frame.tkraise()
        # Action keys
        elif key == 'Bksp':
            self._backspace()
        elif key == 'Enter':
            self._enter()
        elif key == 'Close':
            self._close()
        elif key == 'Tab':
            self._insert_char('\t')
        elif key == 'space':
            self._insert_char(' ')
        elif key == 'Shift':
            # Toggle uppercase temporarily
            if self.lowercase_frame.winfo_ismapped():
                self.uppercase_frame.tkraise()
            else:
                self.lowercase_frame.tkraise()
        # Regular keys
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

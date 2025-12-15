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
        
        # Use overrideredirect for precise positioning (bypasses window manager)
        # Acceptable for touch keyboard - no decorations needed
        self.window.overrideredirect(True)
        
        # Don't show at instantiation - start withdrawn (StackOverflow pattern)
        self.window.withdraw()
        # Position will be set when first shown
        self._positioned = False
        
        # Make it stay on top
        self.window.attributes('-topmost', True)
        
        # Add minimal close button (since overrideredirect removes title bar)
        close_btn = tk.Button(self.window, text='✕', 
                             bg='#c62828', fg='#ffffff',
                             font=("Liberation Sans", 16, "bold"),
                             relief='flat', bd=0, padx=3, pady=0,
                             command=self._close)
        close_btn.pack(side='top', anchor='ne')
        
        # Create container frame
        self.container = tk.Frame(self.window, bg=self.colors['bg_frame'])
        self.container.pack(padx=5, pady=5)
        
        # Define keyboard layouts
        self.lowercase = {
            'row1': ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'Bksp'],
            'row2': ['Tab', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],
            'row3': ['Caps', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'Enter'],
            'row4': ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', '↑'],
            'row5': ['Close', 'gap1', 'space', 'gap', '←', '↓', '→']
        }
        self.uppercase = {
            'row1': ['~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', 'Bksp'],
            'row2': ['Tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}', '|'],
            'row3': ['Caps', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '"', 'Enter'],
            'row4': ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?', '↑'],
            'row5': ['Close', 'gap1', 'space', 'gap', '←', '↓', '→']
        }
        
        # Create frames for each keyboard layer
        self.lowercase_frame = tk.Frame(self.container, bg=self.colors['bg_frame'])
        self.lowercase_frame.grid(row=0, column=0, sticky="nsew")
        
        self.uppercase_frame = tk.Frame(self.container, bg=self.colors['bg_frame'])
        self.uppercase_frame.grid(row=0, column=0, sticky="nsew")
        
        # Initialize caps lock state and button storage BEFORE creating layers
        self._caps_enabled = False
        self._buttons = {}
        
        # Initialize all keyboard layers
        self._init_keyboard_layer(self.lowercase_frame, self.lowercase)
        self._init_keyboard_layer(self.uppercase_frame, self.uppercase)
        
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
            btn = tk.Button(row1_frame, text=key, width=width,
                     font=("Liberation Sans", 16, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='flat', bd=0, takefocus=0)
            btn.config(command=lambda k=key, b=btn: self._key_press(k, b))
            btn.pack(side='left', padx=2, pady=2)
            self._buttons[key] = btn
        
        # Row 2 - qwerty row - stagger 1/6 key (8 pixels)
        row2_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row2_frame.pack()
        tk.Frame(row2_frame, width=8, bg=self.colors['bg_frame']).pack(side='left')
        for key in layout['row2']:
            width, colors = self._get_key_style(key)
            btn = tk.Button(row2_frame, text=key, width=width,
                     font=("Liberation Sans", 16, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='flat', bd=0, takefocus=0)
            btn.config(command=lambda k=key, b=btn: self._key_press(k, b))
            btn.pack(side='left', padx=2, pady=2)
            self._buttons[key] = btn
        
        # Row 3 - asdf row - stagger 2/4 key (16 pixels)
        row3_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row3_frame.pack()
        tk.Frame(row3_frame, width=16, bg=self.colors['bg_frame']).pack(side='left')
        for key in layout['row3']:
            width, colors = self._get_key_style(key)
            btn = tk.Button(row3_frame, text=key, width=width,
                     font=("Liberation Sans", 16, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='flat', bd=0, takefocus=0)
            btn.config(command=lambda k=key, b=btn: self._key_press(k, b))
            btn.pack(side='left', padx=2, pady=2)
            self._buttons[key] = btn
        
        # Row 4 - zxcv row - stagger 1 key (32 pixels)
        row4_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row4_frame.pack()
        tk.Frame(row4_frame, width=32, bg=self.colors['bg_frame']).pack(side='left')
        for key in layout['row4']:
            width, colors = self._get_key_style(key)
            btn = tk.Button(row4_frame, text=key, width=width,
                     font=("Liberation Sans", 16, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='flat', bd=0, takefocus=0)
            btn.config(command=lambda k=key, b=btn: self._key_press(k, b))
            btn.pack(side='left', padx=2, pady=2)
            self._buttons[key] = btn
        
        # Row 5 - space bar row
        row5_frame = tk.Frame(frame, bg=self.colors['bg_frame'])
        row5_frame.pack()
        # Add left spacer - shift right by 3/5 key (approx 48px)
        tk.Frame(row5_frame, width=48, bg=self.colors['bg_frame']).pack(side='left')
        for key in layout['row5']:
            if key == 'gap1':
                # Gap between Close and space bar to prevent accidental touches
                tk.Frame(row5_frame, width=int(self.keysize * 1.5 * 8), bg=self.colors['bg_frame']).pack(side='left')
                continue
            elif key == 'gap':
                # 2.5 key width spacer between space bar and arrows
                tk.Frame(row5_frame, width=int(self.keysize * 2.5 * 8), bg=self.colors['bg_frame']).pack(side='left')
                continue
            elif key == 'space':
                width = int(self.keysize * 6.5)  # Space bar width of c-m (5 keys visually)
                text = ' '
                colors = self.key_colors['letter']
            else:
                width, colors = self._get_key_style(key)
                text = key
            
            btn = tk.Button(row5_frame, text=text, width=width,
                     font=("Liberation Sans", 16, "bold"),
                     bg=colors['bg'], fg=colors['fg'],
                     activebackground=colors['bg'], activeforeground=colors['fg'],
                     relief='flat', bd=0, takefocus=0)
            btn.config(command=lambda k=key, b=btn: self._key_press(k, b))
            btn.pack(side='left', padx=2, pady=2)
            self._buttons[key] = btn
    
    def _get_key_style(self, key):
        """Get width and colors for a key"""
        # Modifier keys (wider)
        if key in ['Tab', 'Bksp']:
            return int(self.keysize * 1.5), self.key_colors['action']
        elif key in ['Caps', 'Enter']:
            return int(self.keysize * 1.75), self.key_colors['action']
        elif key == 'Close':
            return int(self.keysize * 2), self.key_colors['close']
        # Arrow keys
        elif key in ['↑', '↓', '←', '→']:
            return int(self.keysize), self.key_colors['action']
        # Letter keys
        elif key.isalpha():
            return int(self.keysize), self.key_colors['letter']
        # Punctuation/numbers
        else:
            return int(self.keysize), self.key_colors['punctuation']
    
    def _flash_key(self, button):
        """Flash the pressed key briefly"""
        if not button:
            return
        try:
            if button.winfo_exists():
                original_bg = button.cget('bg')
                # Flash to lighter color
                button.config(bg='#ffffff')
                # Restore original color after 100ms
                button.after(100, lambda: button.config(bg=original_bg) if button.winfo_exists() else None)
        except tk.TclError:
            # Button was destroyed or doesn't exist
            pass
    
    def _key_press(self, key, button=None):
        """Handle key press"""
        # Mode switching (do this first, before flash, to minimize redraw artifacts)
        if key == 'Caps':
            # Toggle caps lock on/off
            if hasattr(self, '_caps_enabled') and self._caps_enabled:
                # Turn off caps
                self._caps_enabled = False
                self.lowercase_frame.tkraise()
            else:
                # Turn on caps
                self._caps_enabled = True
                self.uppercase_frame.tkraise()
            # Flash AFTER tkraise to avoid double-draw - DISABLED for testing
            #if button:
            #    self._flash_key(button)
            # Keep focus on target widget to prevent flash
            self.target_widget.focus_set()
            return
        
        # Flash the key (for non-Caps keys) - DISABLED for testing
        #if button:
        #    self._flash_key(button)
        
        # Action keys
        if key == 'Bksp':
            self._backspace()
        elif key == 'Enter':
            self._enter()
        elif key == 'Close':
            self._close()
        elif key == 'Tab':
            self._insert_char('\t')
        elif key == 'space':
            self._insert_char(' ')
        # Arrow keys
        elif key == '↑':
            self._arrow_up()
        elif key == '↓':
            self._arrow_down()
        elif key == '←':
            self._arrow_left()
        elif key == '→':
            self._arrow_right()
        # Regular keys
        else:
            self._insert_char(key)
        
        # CRITICAL FIX: Restore focus to target widget after every key press
        # This prevents focus events from triggering and causing window flash
        self.target_widget.focus_set()
    
    def _insert_char(self, char):
        """Insert character into target widget"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.insert('insert', char)
            # DISABLED - these event_generate calls may trigger window redraws
            #self.target_widget.event_generate('<<Modified>>')
            #self.target_widget.event_generate('<KeyRelease>')
        elif isinstance(self.target_widget, tk.Entry):
            current_pos = self.target_widget.index('insert')
            self.target_widget.insert(current_pos, char)
    
    def _backspace(self):
        """Handle backspace"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.delete('insert-1c', 'insert')
            # DISABLED - these event_generate calls may trigger window redraws
            #self.target_widget.event_generate('<<Modified>>')
            #self.target_widget.event_generate('<KeyRelease>')
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
    
    def _arrow_up(self):
        """Move cursor up"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.mark_set('insert', 'insert-1l')
    
    def _arrow_down(self):
        """Move cursor down"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.mark_set('insert', 'insert+1l')
    
    def _arrow_left(self):
        """Move cursor left"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.mark_set('insert', 'insert-1c')
        elif isinstance(self.target_widget, tk.Entry):
            pos = self.target_widget.index('insert')
            if pos > 0:
                self.target_widget.icursor(pos - 1)
    
    def _arrow_right(self):
        """Move cursor right"""
        if isinstance(self.target_widget, tk.Text):
            self.target_widget.mark_set('insert', 'insert+1c')
        elif isinstance(self.target_widget, tk.Entry):
            pos = self.target_widget.index('insert')
            self.target_widget.icursor(pos + 1)
    
    def _close(self):
        """Close keyboard - withdraw instead of destroy (StackOverflow pattern)"""
        self.hide()
    
    def show(self):
        """Show the keyboard"""
        logger.info(f"show() called, current state: {self.window.state()}")
        # Position below parent on first show
        if not self._positioned:
            self.window.update_idletasks()
            parent = self.window.master
            
            # Get screen dimensions and keyboard size
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            kb_width = self.window.winfo_reqwidth()
            kb_height = self.window.winfo_reqheight()
            
            # Calculate Y position (above or below parent)
            parent_bottom = parent.winfo_rooty() + parent.winfo_height()
            space_below = screen_height - parent_bottom
            
            if space_below < kb_height + 20:
                # Position above parent
                y = parent.winfo_rooty() - kb_height - 5
                logger.info(f"Insufficient space below ({space_below}px), positioning above")
            else:
                # Position below parent
                y = parent_bottom + 5
                logger.info(f"Sufficient space below ({space_below}px), positioning below")
            
            # Center keyboard horizontally relative to parent
            parent_center_x = parent.winfo_rootx() + (parent.winfo_width() // 2)
            x = parent_center_x - (kb_width // 2)
            
            # Ensure keyboard doesn't go off-screen
            if x < 0:
                x = 0
                logger.info(f"Adjusted X to 0 (would have been off left edge)")
            elif x + kb_width > screen_width:
                x = screen_width - kb_width
                logger.info(f"Adjusted X to {x} (would have been off right edge)")
            
            logger.info(f"Positioning keyboard at ({x}, {y}), centered on parent")
            self.window.geometry(f"+{x}+{y}")
            self._positioned = True
        
        self.window.deiconify()
        logger.info(f"Keyboard shown, new state: {self.window.state()}")
    
    def hide(self):
        """Hide the keyboard"""
        logger.info(f"hide() called, current state: {self.window.state()}")
        self.window.withdraw()
        logger.info(f"Keyboard hidden, new state: {self.window.state()}")
    
    def destroy(self):
        """Destroy the keyboard"""
        self.window.destroy()

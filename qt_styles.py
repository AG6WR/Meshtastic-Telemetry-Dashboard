"""
Shared Qt styles, fonts, and button factory for consistent UI across all windows.

Standard button spec:
- min-width: 80px
- min-height: 32px  
- padding: 8px 16px
- font-size: 12pt
- border-radius: 4px

Font Categories:
- Card fonts: Liberation Sans for dashboard node cards
- UI fonts: Liberation Sans family for windows/dialogs
"""

import sys
from typing import Optional, Tuple, List
from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QColor, QPen

# =============================================================================
# FONT DEFINITIONS
# =============================================================================

# Base font families
FONT_UI = "Liberation Sans"
FONT_UI_NARROW = "Liberation Sans Narrow"

# Card view fonts - Liberation Sans for card display
FONTS = {
    # Card fonts (Liberation Sans)
    'card_base': (FONT_UI, 11, QFont.Normal),
    'card_bold': (FONT_UI, 11, QFont.Bold),
    'card_data': (FONT_UI, 12, QFont.Normal),
    'card_data_bold': (FONT_UI, 12, QFont.Bold),
    'card_header': (FONT_UI, 14, QFont.Bold),          # Card header 14pt
    'card_line2': (FONT_UI, 11, QFont.Normal),         # Motion/Last Heard
    'card_line3': (FONT_UI, 14, QFont.Bold),           # V/I/T row
    'card_label': (FONT_UI, 8, QFont.Normal),          # Small labels "ICP Batt:", "Ch:"
    'card_value': (FONT_UI, 12, QFont.Bold),           # Data values 12pt
    'card_title': (FONT_UI, 18, QFont.Bold),           # Dashboard title
    
    # UI fonts (Liberation Sans)
    'ui_button': (FONT_UI, 12, QFont.Normal),          # All buttons
    'ui_tab': (FONT_UI, 12, QFont.Normal),             # Notebook tabs
    'ui_section_title': (FONT_UI, 13, QFont.Bold),     # Section headers in detail windows
    'ui_window_title': (FONT_UI, 16, QFont.Bold),      # Window/dialog main titles
    'ui_body': (FONT_UI, 12, QFont.Normal),            # Message text, labels, general content
    'ui_notes': (FONT_UI_NARROW, 11, QFont.Normal),    # Timestamps, help text
    'ui_context_menu': (FONT_UI, 12, QFont.Normal),    # Context menus (larger for touch)
    'ui_input': (FONT_UI, 11, QFont.Normal),           # Text entry, comboboxes
}


def get_font(font_name: str) -> QFont:
    """
    Get a QFont object by name.
    
    Args:
        font_name: Key from FONTS dict (e.g., 'ui_button', 'card_header')
    
    Returns:
        Configured QFont object
    
    Usage:
        from qt_styles import get_font
        label.setFont(get_font('ui_section_title'))
    """
    family, size, weight = FONTS.get(font_name, FONTS['ui_body'])
    font = QFont(family, size)
    font.setWeight(weight)
    return font


def get_font_style(font_name: str) -> str:
    """
    Get a CSS font style string by name.
    
    Args:
        font_name: Key from FONTS dict
    
    Returns:
        CSS style string like "font-family: Liberation Sans; font-size: 12pt; font-weight: bold;"
    
    Usage:
        label.setStyleSheet(get_font_style('ui_section_title'))
    """
    family, size, weight = FONTS.get(font_name, FONTS['ui_body'])
    weight_str = "bold" if weight == QFont.Bold else "normal"
    return f"font-family: '{family}'; font-size: {size}pt; font-weight: {weight_str};"


# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    # Backgrounds
    'bg_main': '#1e1e1e',
    'bg_frame': '#2b2b2b',
    'bg_input': '#3c3c3c',
    
    # Text
    'fg_normal': '#e0e0e0',
    'fg_secondary': '#b0b0b0',
    'fg_good': '#228B22',            # Forest green - positive values
    'fg_bad': '#FF6B9D',             # Coral pink - errors/warnings
    'fg_warning': '#FFA500',         # Orange - warning state
    'accent': '#4a90d9',             # Blue accent
    
    # Button colors
    'btn_primary': '#0d47a1',        # Blue - primary actions
    'btn_primary_hover': '#1565c0',
    'btn_success': '#2e7d32',        # Green - confirm/send/ok
    'btn_success_hover': '#388e3c',
    'btn_warning': '#f57c00',        # Orange - caution/test
    'btn_warning_hover': '#ff9800',
    'btn_danger': '#c62828',         # Red - delete/destructive
    'btn_danger_hover': '#e53935',
    'btn_neutral': '#424242',        # Gray - cancel/close
    'btn_neutral_hover': '#616161',
}


# =============================================================================
# DARK THEME WIDGET STYLES
# =============================================================================

# Checkbox style - use Qt defaults (no customization)
# The fix for checkbox visibility in message center is using #id selectors
# on parent widgets instead of raw background-color properties
CHECKBOX_STYLE = ""

# Radio button style - use Qt defaults (no customization)
RADIOBUTTON_STYLE = ""

# Tab widget style - minimal dark theme colors
TAB_STYLE = """
    QTabWidget::pane {
        border: 1px solid #555555;
        background-color: #2b2b2b;
    }
    QTabWidget > QWidget {
        background-color: #2b2b2b;
    }
    QTabBar::tab {
        background-color: #3c3c3c;
        color: #a0a0a0;
        padding: 8px 16px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #2b2b2b;
        color: #ffffff;
    }
    QTabBar::tab:hover:!selected {
        background-color: #4a4a4a;
    }
"""

# GroupBox style for dark theme
GROUPBOX_STYLE = """
    QGroupBox {
        color: #e0e0e0;
        font-size: 11pt;
        font-weight: bold;
        border: 1px solid #555555;
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
"""

# Combined dark theme styles for common widgets
DARK_THEME_STYLES = f"""
    {CHECKBOX_STYLE}
    {RADIOBUTTON_STYLE}
    {TAB_STYLE}
    {GROUPBOX_STYLE}
"""


# =============================================================================
# BUTTON STYLES
# =============================================================================

# Base button style template
_BUTTON_BASE = """
    QPushButton {{
        background-color: {bg};
        color: white;
        min-width: 80px;
        min-height: 32px;
        padding: 8px 16px;
        font-size: 12pt;
        border: none;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        background-color: {bg_hover};
    }}
"""

# Pre-built style strings
BUTTON_STYLES = {
    'primary': _BUTTON_BASE.format(bg=COLORS['btn_primary'], bg_hover=COLORS['btn_primary_hover']),
    'success': _BUTTON_BASE.format(bg=COLORS['btn_success'], bg_hover=COLORS['btn_success_hover']),
    'warning': _BUTTON_BASE.format(bg=COLORS['btn_warning'], bg_hover=COLORS['btn_warning_hover']),
    'danger': _BUTTON_BASE.format(bg=COLORS['btn_danger'], bg_hover=COLORS['btn_danger_hover']),
    'neutral': _BUTTON_BASE.format(bg=COLORS['btn_neutral'], bg_hover=COLORS['btn_neutral_hover']),
}


def create_button(text: str, style: str = 'primary', callback=None) -> QPushButton:
    """
    Create a standard styled button.
    
    Args:
        text: Button label
        style: One of 'primary', 'success', 'warning', 'danger', 'neutral'
        callback: Optional click handler
    
    Returns:
        Configured QPushButton
    
    Usage:
        from qt_styles import create_button
        
        ok_btn = create_button("OK", "success", self.on_ok)
        cancel_btn = create_button("Cancel", "neutral", self.on_cancel)
        delete_btn = create_button("Delete", "danger", self.on_delete)
    """
    btn = QPushButton(text)
    btn.setStyleSheet(BUTTON_STYLES.get(style, BUTTON_STYLES['primary']))
    if callback:
        btn.clicked.connect(callback)
    return btn


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_ok_button(callback=None) -> QPushButton:
    """Create standard OK button (green)"""
    return create_button("OK", "success", callback)


def create_cancel_button(callback=None) -> QPushButton:
    """Create standard Cancel button (gray)"""
    return create_button("Cancel", "neutral", callback)


def create_close_button(callback=None) -> QPushButton:
    """Create standard Close button (gray)"""
    return create_button("Close", "neutral", callback)


def create_apply_button(callback=None) -> QPushButton:
    """Create standard Apply button (blue)"""
    return create_button("Apply", "primary", callback)


def create_send_button(callback=None) -> QPushButton:
    """Create standard Send button (green)"""
    return create_button("Send", "success", callback)


def create_delete_button(text: str = "Delete", callback=None) -> QPushButton:
    """Create standard Delete button (red)"""
    return create_button(text, "danger", callback)


# =============================================================================
# COLOR BAR WIDGET
# =============================================================================

class ColorBar(QWidget):
    """
    A horizontal color-coded bar widget for displaying values like battery % or SNR.
    
    The bar shows a filled portion proportional to the value, with color based on
    configurable thresholds (good/warning/bad ranges).
    
    Usage:
        # Battery bar (0-100%, higher is better)
        bar = ColorBar(label="Batt", value=75, max_value=100, 
                       thresholds=[(50, 'good'), (25, 'warning'), (0, 'bad')])
        
        # SNR bar (-20 to +15, higher is better)  
        bar = ColorBar(label="SNR", value=8.5, min_value=-20, max_value=15,
                       thresholds=[(5, 'good'), (-5, 'warning'), (-20, 'bad')])
    """
    
    def __init__(self, 
                 label: str = "",
                 value: float = 0,
                 min_value: float = 0,
                 max_value: float = 100,
                 thresholds: Optional[List[Tuple[float, str]]] = None,
                 width: int = 80,
                 height: int = 14,
                 show_value: bool = True,
                 value_format: str = "{:.0f}",
                 suffix: str = "",
                 label_width: int = 0,
                 parent: Optional[QWidget] = None):
        """
        Create a color bar widget.
        
        Args:
            label: Text label shown before the bar (e.g., "Batt", "SNR")
            value: Current value to display
            min_value: Minimum possible value (for scaling)
            max_value: Maximum possible value (for scaling)
            thresholds: List of (threshold, color_name) tuples in descending order.
                       Color names: 'good' (green), 'warning' (orange), 'bad' (red)
                       Value >= threshold uses that color.
            width: Bar width in pixels
            height: Bar height in pixels
            show_value: Whether to show numeric value after bar
            value_format: Format string for value display
            suffix: Suffix after value (e.g., "%", "dB")
            label_width: Fixed width for label column (0 = auto-size)
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._label = label
        self._value = value
        self._min_value = min_value
        self._max_value = max_value
        self._thresholds = thresholds or [(50, 'good'), (25, 'warning'), (0, 'bad')]
        self._bar_width = width
        self._bar_height = height
        self._show_value = show_value
        self._value_format = value_format
        self._suffix = suffix
        self._label_width = label_width
        self._stale = False  # Grey out when data is stale
        
        # Color mapping
        self._color_map = {
            'good': QColor(COLORS['fg_good']),
            'warning': QColor(COLORS['fg_warning']),
            'bad': QColor(COLORS['fg_bad']),
            'stale': QColor(COLORS['fg_secondary']),
        }
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the widget layout"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Label (right-aligned within its column so it's flush against bar)
        if self._label:
            self._label_widget = QLabel(f"{self._label}:")
            self._label_widget.setFont(get_font('card_label'))
            self._label_widget.setStyleSheet(f"color: {COLORS['fg_secondary']}; background: transparent;")
            self._label_widget.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if self._label_width > 0:
                self._label_widget.setFixedWidth(self._label_width)
            layout.addWidget(self._label_widget)
        
        # Bar canvas (custom painted)
        self._bar_widget = _BarCanvas(
            width=self._bar_width,
            height=self._bar_height,
            parent=self
        )
        layout.addWidget(self._bar_widget)
        
        # Value label
        if self._show_value:
            self._value_widget = QLabel()
            self._value_widget.setFont(get_font('card_value'))
            self._value_widget.setStyleSheet(f"color: {COLORS['fg_normal']}; background: transparent;")
            self._value_widget.setMinimumWidth(35)
            layout.addWidget(self._value_widget)
        
        self._update_display()
        
    def _get_fill_ratio(self) -> float:
        """Calculate fill ratio (0.0 to 1.0) based on value and range"""
        range_span = self._max_value - self._min_value
        if range_span <= 0:
            return 0.0
        ratio = (self._value - self._min_value) / range_span
        return max(0.0, min(1.0, ratio))
    
    def _get_bar_color(self) -> QColor:
        """Get bar color based on value and thresholds"""
        if self._stale:
            return self._color_map['stale']
        
        for threshold, color_name in self._thresholds:
            if self._value >= threshold:
                return self._color_map.get(color_name, self._color_map['good'])
        
        # Below all thresholds - use last color
        return self._color_map.get(self._thresholds[-1][1], self._color_map['bad'])
    
    def _update_display(self):
        """Update bar fill and value text"""
        fill_ratio = self._get_fill_ratio()
        bar_color = self._get_bar_color()
        
        self._bar_widget.set_fill(fill_ratio, bar_color)
        
        if self._show_value:
            value_str = self._value_format.format(self._value) + self._suffix
            text_color = COLORS['fg_secondary'] if self._stale else bar_color.name()
            self._value_widget.setText(value_str)
            self._value_widget.setStyleSheet(f"color: {text_color}; background: transparent;")
    
    def set_value(self, value: float, stale: bool = False):
        """Update the displayed value"""
        self._value = value
        self._stale = stale
        self._update_display()
    
    def set_stale(self, stale: bool):
        """Set stale mode (grey display)"""
        self._stale = stale
        self._update_display()


class _BarCanvas(QWidget):
    """Internal widget that paints the actual bar"""
    
    def __init__(self, width: int, height: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._fill_ratio = 0.0
        self._fill_color = QColor(COLORS['fg_good'])
        self._bg_color = QColor(COLORS['bg_input'])
        self._border_color = QColor(COLORS['fg_secondary'])
        
        self.setFixedSize(width, height)
        
    def set_fill(self, ratio: float, color: QColor):
        """Set fill ratio and color, then repaint"""
        self._fill_ratio = ratio
        self._fill_color = color
        self.update()
        
    def paintEvent(self, event):
        """Paint the bar"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, self._bg_color)
        
        # Filled portion
        fill_width = int(w * self._fill_ratio)
        if fill_width > 0:
            painter.fillRect(0, 0, fill_width, h, self._fill_color)
        
        # Border
        painter.setPen(QPen(self._border_color, 1))
        painter.drawRect(0, 0, w - 1, h - 1)


# =============================================================================
# COLOR BAR FACTORY FUNCTIONS
# =============================================================================

def create_battery_bar(value: float = 0, stale: bool = False, 
                       label: str = "Batt", width: int = 60,
                       show_value: bool = True, label_width: int = 0) -> ColorBar:
    """
    Create a battery percentage bar (0-100%).
    
    Color thresholds:
    - >50%: Green (good)
    - 25-50%: Orange (warning)
    - <25%: Red (bad)
    
    Args:
        value: Battery percentage (0-100)
        stale: Whether data is stale (grey display)
        label: Label text (default "Batt")
        width: Bar width in pixels
        show_value: Whether to show numeric value after bar
        label_width: Fixed width for label column (0 = auto-size)
        
    Returns:
        Configured ColorBar widget
    """
    bar = ColorBar(
        label=label,
        value=value,
        min_value=0,
        max_value=100,
        thresholds=[(50, 'good'), (25, 'warning'), (0, 'bad')],
        width=width,
        height=12,
        show_value=show_value,
        value_format="{:.0f}",
        suffix="%",
        label_width=label_width
    )
    bar.set_stale(stale)
    return bar


def create_snr_bar(value: float = 0, stale: bool = False,
                   label: str = "SNR", width: int = 60, 
                   show_value: bool = True, label_width: int = 0) -> ColorBar:
    """
    Create an SNR (Signal-to-Noise Ratio) bar.
    
    SNR range: -20 dB to +15 dB (typical Meshtastic range)
    
    Color thresholds:
    - >= 5 dB: Green (good signal)
    - >= -5 dB: Orange (marginal)
    - < -5 dB: Red (poor signal)
    
    Args:
        value: SNR in dB
        stale: Whether data is stale (grey display)
        label: Label text (default "SNR")
        width: Bar width in pixels
        show_value: Whether to show numeric value after bar
        label_width: Fixed width for label column (0 = auto-size)
        
    Returns:
        Configured ColorBar widget
    """
    bar = ColorBar(
        label=label,
        value=value,
        min_value=-20,
        max_value=15,
        thresholds=[(5, 'good'), (-5, 'warning'), (-20, 'bad')],
        width=width,
        height=12,
        show_value=show_value,
        value_format="{:.1f}",
        suffix="dB",
        label_width=label_width
    )
    bar.set_stale(stale)
    return bar


def create_utilization_bar(value: float = 0, stale: bool = False,
                           label: str = "Util", width: int = 60, 
                           show_value: bool = True, label_width: int = 0) -> ColorBar:
    """
    Create a utilization bar (0-100%) where LOWER is better.
    
    Color thresholds (inverted - high util is bad):
    - <25%: Green (good - low utilization)
    - 25-50%: Orange (moderate)
    - >50%: Red (congested)
    
    Args:
        value: Utilization percentage (0-100)
        stale: Whether data is stale (grey display)
        label: Label text
        width: Bar width in pixels
        show_value: Whether to show numeric value after bar
        label_width: Fixed width for label column (0 = auto-size)
        
    Returns:
        Configured ColorBar widget
    """
    # Inverted thresholds - lower values are better
    bar = ColorBar(
        label=label,
        value=value,
        min_value=0,
        max_value=100,
        thresholds=[(50, 'bad'), (25, 'warning'), (0, 'good')],
        width=width,
        height=12,
        show_value=show_value,
        value_format="{:.1f}",
        suffix="%",
        label_width=label_width
    )
    bar.set_stale(stale)
    return bar

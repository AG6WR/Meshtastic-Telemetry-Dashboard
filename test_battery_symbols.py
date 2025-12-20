#!/usr/bin/env python3
"""
Test various battery symbol options for display on Raspberry Pi.
Run this to see which symbols render correctly on your display.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Symbol categories to test
BATTERY_SYMBOLS = {
    "Unicode Battery Icons": [
        ("🔋", "U+1F50B Battery"),
        ("🪫", "U+1FAAB Low Battery"),
        ("⚡", "U+26A1 Lightning"),
        ("⏻", "U+23FB Power Symbol"),
        ("⌁", "U+2301 Electric Arrow"),
    ],
    "Box Drawing / Geometric": [
        ("▮", "U+25AE Black Rectangle"),
        ("█", "U+2588 Full Block"),
        ("▌", "U+258C Left Half Block"),
        ("▐", "U+2590 Right Half Block"),
        ("■", "U+25A0 Black Square"),
        ("□", "U+25A1 White Square"),
        ("▪", "U+25AA Black Small Square"),
        ("▫", "U+25AB White Small Square"),
    ],
    "Arrows / Indicators": [
        ("►", "U+25BA Black Right Triangle"),
        ("▶", "U+25B6 Black Right Triangle"),
        ("◄", "U+25C4 Black Left Triangle"),
        ("▲", "U+25B2 Black Up Triangle"),
        ("▼", "U+25BC Black Down Triangle"),
        ("→", "U+2192 Right Arrow"),
        ("↑", "U+2191 Up Arrow"),
        ("↓", "U+2193 Down Arrow"),
    ],
    "Miscellaneous Symbols": [
        ("●", "U+25CF Black Circle"),
        ("○", "U+25CB White Circle"),
        ("◉", "U+25C9 Fisheye"),
        ("◎", "U+25CE Bullseye"),
        ("★", "U+2605 Black Star"),
        ("☆", "U+2606 White Star"),
        ("+", "Plus Sign (ASCII)"),
        ("-", "Minus Sign (ASCII)"),
    ],
    "Technical / Electrical": [
        ("Ω", "U+03A9 Omega (resistance)"),
        ("±", "U+00B1 Plus-Minus"),
        ("∞", "U+221E Infinity"),
        ("℃", "U+2103 Celsius"),
        ("℉", "U+2109 Fahrenheit"),
        ("µ", "U+00B5 Micro"),
        ("Δ", "U+0394 Delta"),
        ("V", "V for Voltage (ASCII)"),
    ],
    "ASCII Art Style Labels": [
        ("[+]", "Plus in brackets"),
        ("(+)", "Plus in parens"),
        ("[V]", "V in brackets"),
        ("[B]", "B in brackets"),
        ("Batt", "Text: Batt"),
        ("Pwr", "Text: Pwr"),
        ("V:", "V colon"),
        ("B:", "B colon"),
    ],
}


class SymbolTestWindow(QWidget):
    """Window to display and test various symbols"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Battery Symbol Test - Check Rendering on Pi")
        self.setMinimumSize(700, 600)
        
        # Dark theme
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
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
            QLabel {
                color: #e0e0e0;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Battery Symbol Options - Test on Raspberry Pi")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        instructions = QLabel(
            "Symbols that render as boxes or question marks won't work on the Pi.\n"
            "Look for symbols that display correctly and are visually clear."
        )
        instructions.setStyleSheet("color: #888888; font-size: 10pt;")
        instructions.setAlignment(Qt.AlignCenter)
        layout.addWidget(instructions)
        
        # Create groups for each category
        for category_name, symbols in BATTERY_SYMBOLS.items():
            group = QGroupBox(category_name)
            grid = QGridLayout(group)
            grid.setSpacing(8)
            
            for i, (symbol, description) in enumerate(symbols):
                row = i // 4
                col = i % 4
                
                # Container for symbol + description
                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(5, 5, 5, 5)
                container_layout.setSpacing(2)
                
                # Large symbol display
                symbol_label = QLabel(symbol)
                symbol_label.setFont(QFont("Arial", 16))
                symbol_label.setAlignment(Qt.AlignCenter)
                symbol_label.setStyleSheet("""
                    background-color: #2d2d2d;
                    border: 1px solid #444444;
                    border-radius: 4px;
                    padding: 5px;
                    min-width: 40px;
                    min-height: 30px;
                """)
                container_layout.addWidget(symbol_label)
                
                # Description
                desc_label = QLabel(description)
                desc_label.setFont(QFont("Arial", 7))
                desc_label.setStyleSheet("color: #888888;")
                desc_label.setAlignment(Qt.AlignCenter)
                desc_label.setWordWrap(True)
                container_layout.addWidget(desc_label)
                
                grid.addWidget(container, row, col)
            
            layout.addWidget(group)
        
        # Example usage section
        example_group = QGroupBox("Example Usage in Card Labels")
        example_layout = QVBoxLayout(example_group)
        
        examples = [
            ("ICP", "Current label (no symbol)"),
            ("Node", "Current label (no symbol)"),
            ("[+] ICP", "Brackets + plus"),
            ("[+] Node", "Brackets + plus"),
            ("▮ ICP", "Black rectangle"),
            ("▮ Node", "Black rectangle"),
            ("■ ICP", "Black square"),
            ("■ Node", "Black square"),
            ("► ICP", "Triangle"),
            ("► Node", "Triangle"),
            ("● ICP", "Filled circle"),
            ("● Node", "Filled circle"),
        ]
        
        example_grid = QGridLayout()
        for i, (label, desc) in enumerate(examples):
            row = i // 4
            col = i % 4
            
            example_widget = QWidget()
            example_widget_layout = QVBoxLayout(example_widget)
            example_widget_layout.setContentsMargins(5, 2, 5, 2)
            example_widget_layout.setSpacing(1)
            
            label_display = QLabel(label)
            label_display.setFont(QFont("Arial", 11))
            label_display.setAlignment(Qt.AlignCenter)
            label_display.setStyleSheet("""
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 3px;
                padding: 4px 8px;
            """)
            example_widget_layout.addWidget(label_display)
            
            desc_label = QLabel(desc)
            desc_label.setFont(QFont("Arial", 7))
            desc_label.setStyleSheet("color: #666666;")
            desc_label.setAlignment(Qt.AlignCenter)
            example_widget_layout.addWidget(desc_label)
            
            example_grid.addWidget(example_widget, row, col)
        
        example_layout.addLayout(example_grid)
        layout.addWidget(example_group)


def main():
    app = QApplication(sys.argv)
    window = SymbolTestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

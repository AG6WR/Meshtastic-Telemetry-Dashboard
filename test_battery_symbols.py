#!/usr/bin/env python3
"""
Test various battery symbol options for display on Raspberry Pi.
Run this to see which symbols render correctly on your display.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase

# Symbol categories to test
BATTERY_SYMBOLS = {
    "ASCII Only (Should Always Work)": [
        ("+", "Plus"),
        ("-", "Minus"),
        ("*", "Asterisk"),
        ("#", "Hash"),
        ("@", "At"),
        ("=", "Equals"),
        ("[+]", "Bracketed plus"),
        ("(+)", "Paren plus"),
    ],
    "Basic Latin Extended": [
        ("±", "Plus-Minus U+00B1"),
        ("×", "Multiply U+00D7"),
        ("÷", "Divide U+00F7"),
        ("°", "Degree U+00B0"),
        ("µ", "Micro U+00B5"),
        ("·", "Middle dot U+00B7"),
        ("«", "Left guillemet"),
        ("»", "Right guillemet"),
    ],
    "Box Drawing (U+2500 range)": [
        ("─", "U+2500 Light horiz"),
        ("│", "U+2502 Light vert"),
        ("┌", "U+250C Corner"),
        ("└", "U+2514 Corner"),
        ("├", "U+251C T-left"),
        ("┼", "U+253C Cross"),
        ("═", "U+2550 Double horiz"),
        ("║", "U+2551 Double vert"),
    ],
    "Block Elements (U+2580 range)": [
        ("▀", "U+2580 Upper half"),
        ("▄", "U+2584 Lower half"),
        ("█", "U+2588 Full block"),
        ("▌", "U+258C Left half"),
        ("▐", "U+2590 Right half"),
        ("░", "U+2591 Light shade"),
        ("▒", "U+2592 Medium shade"),
        ("▓", "U+2593 Dark shade"),
    ],
    "Geometric Shapes (U+25A0 range)": [
        ("■", "U+25A0 Black square"),
        ("□", "U+25A1 White square"),
        ("▪", "U+25AA Small black sq"),
        ("▫", "U+25AB Small white sq"),
        ("▬", "U+25AC Black rect"),
        ("▮", "U+25AE Black vert rect"),
        ("▰", "U+25B0 Black parallelogram"),
        ("▱", "U+25B1 White parallelogram"),
    ],
    "Triangles and Arrows": [
        ("▲", "U+25B2 Black up tri"),
        ("△", "U+25B3 White up tri"),
        ("▶", "U+25B6 Black right tri"),
        ("▷", "U+25B7 White right tri"),
        ("▼", "U+25BC Black down tri"),
        ("◀", "U+25C0 Black left tri"),
        ("►", "U+25BA Black right ptr"),
        ("◄", "U+25C4 Black left ptr"),
    ],
    "Circles": [
        ("●", "U+25CF Black circle"),
        ("○", "U+25CB White circle"),
        ("◉", "U+25C9 Fisheye"),
        ("◎", "U+25CE Bullseye"),
        ("◐", "U+25D0 Half black"),
        ("◑", "U+25D1 Half black R"),
        ("◒", "U+25D2 Half black B"),
        ("◓", "U+25D3 Half black T"),
    ],
    "Misc Symbols": [
        ("★", "U+2605 Black star"),
        ("☆", "U+2606 White star"),
        ("✓", "U+2713 Check mark"),
        ("✗", "U+2717 X mark"),
        ("✦", "U+2726 4-pointed star"),
        ("⬤", "U+2B24 Large circle"),
        ("⚡", "U+26A1 Lightning"),
        ("⏻", "U+23FB Power"),
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
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Show available fonts for debugging
        font_db = QFontDatabase()
        families = font_db.families()
        print(f"Available font families ({len(families)}):")
        for f in families[:20]:  # First 20
            print(f"  - {f}")
        if len(families) > 20:
            print(f"  ... and {len(families) - 20} more")
        
        # Use Liberation Sans - the font installed on Pi
        FONT_FAMILY = "Liberation Sans"
        
        # Title
        title = QLabel("Battery Symbol Options - Test on Raspberry Pi")
        title_font = QFont(FONT_FAMILY, 14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Show which font is being used
        actual_font = QFont(FONT_FAMILY)
        font_info = QLabel(f"Requested: {FONT_FAMILY} | Actual: {actual_font.family()}")
        font_info.setStyleSheet("color: #00ff00; font-size: 9pt;")
        font_info.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(font_info)
        
        instructions = QLabel(
            "Symbols that render as boxes or question marks won't work on the Pi.\n"
            "Look for symbols that display correctly and are visually clear."
        )
        instructions.setStyleSheet("color: #888888; font-size: 10pt;")
        instructions.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(instructions)
        
        # Scrollable area for the content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        
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
                
                # Large symbol display - use Liberation Sans
                symbol_label = QLabel(symbol)
                symbol_font = QFont(FONT_FAMILY, 16)
                symbol_label.setFont(symbol_font)
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
                
                # Description - use Liberation Sans
                desc_label = QLabel(description)
                desc_font = QFont(FONT_FAMILY, 7)
                desc_label.setFont(desc_font)
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
            label_font = QFont(FONT_FAMILY, 11)
            label_display.setFont(label_font)
            label_display.setAlignment(Qt.AlignCenter)
            label_display.setStyleSheet("""
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 3px;
                padding: 4px 8px;
            """)
            example_widget_layout.addWidget(label_display)
            
            desc_label = QLabel(desc)
            desc_font = QFont(FONT_FAMILY, 7)
            desc_label.setFont(desc_font)
            desc_label.setStyleSheet("color: #666666;")
            desc_label.setAlignment(Qt.AlignCenter)
            example_widget_layout.addWidget(desc_label)
            
            example_grid.addWidget(example_widget, row, col)
        
        example_layout.addLayout(example_grid)
        layout.addWidget(example_group)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)


def main():
    app = QApplication(sys.argv)
    window = SymbolTestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

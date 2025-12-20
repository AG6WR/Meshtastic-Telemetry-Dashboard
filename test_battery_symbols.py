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
    "ASCII Only (Always Works)": [
        ("+", "Plus"),
        ("-", "Minus"),
        ("*", "Asterisk"),
        ("#", "Hash"),
        ("@", "At"),
        ("=", "Equals"),
        ("[+]", "Bracketed plus"),
        ("(+)", "Paren plus"),
    ],
    "Lightning/Power (for battery telemetry)": [
        ("⚡", "U+26A1 High voltage"),
        ("↯", "U+21AF Downwards zigzag"),
        ("϶", "U+03F6 Lunate epsilon"),
        ("ϟ", "U+03DF Greek koppa"),
        ("⌁", "U+2301 Electric arrow"),
        ("⏻", "U+23FB Power symbol"),
        ("⏼", "U+23FC Power on-off"),
        ("⏽", "U+23FD Power on"),
    ],
    "Mail/Envelope (for messaging)": [
        ("✉", "U+2709 Envelope"),
        ("✆", "U+2706 Telephone"),
        ("☎", "U+260E Black telephone"),
        ("☏", "U+260F White telephone"),
        ("✇", "U+2707 Tape drive"),
        ("⌨", "U+2328 Keyboard"),
        ("📧", "U+1F4E7 Email symbol"),
        ("📨", "U+1F4E8 Incoming envelope"),
    ],
    "Temperature/Thermometer": [
        ("℃", "U+2103 Celsius"),
        ("℉", "U+2109 Fahrenheit"),
        ("°", "U+00B0 Degree"),
        ("˚", "U+02DA Ring above"),
        ("⌂", "U+2302 House"),
        ("Θ", "U+0398 Theta"),
        ("θ", "U+03B8 Small theta"),
        ("⏱", "U+23F1 Stopwatch"),
    ],
    "WiFi/Antenna/Signal (for SNR)": [
        ("⚲", "U+26B2 Neuter"),
        ("⏃", "U+23C3 Dentistry symbol"),
        ("⌗", "U+2317 Viewdata square"),
        ("⌖", "U+2316 Position indicator"),
        ("⎍", "U+238D Monostable"),
        ("⎎", "U+238E Hysteresis"),
        ("⎓", "U+2393 Direct current"),
        ("⎌", "U+238C Benchmark"),
    ],
    "Water/Humidity": [
        ("∿", "U+223F Sine wave"),
        ("≈", "U+2248 Almost equal"),
        ("≋", "U+224B Triple tilde"),
        ("∼", "U+223C Tilde operator"),
        ("⌇", "U+2307 Wavy line"),
        ("⎰", "U+23B0 Upper left tortoise"),
        ("⎱", "U+23B1 Lower right tortoise"),
        ("〰", "U+3030 Wavy dash"),
    ],
    "Arrows (directional indicators)": [
        ("→", "U+2192 Right arrow"),
        ("←", "U+2190 Left arrow"),
        ("↑", "U+2191 Up arrow"),
        ("↓", "U+2193 Down arrow"),
        ("↔", "U+2194 Left right"),
        ("↕", "U+2195 Up down"),
        ("⇒", "U+21D2 Double right"),
        ("⇐", "U+21D0 Double left"),
    ],
    "Up/Down Arrows (for current measurement)": [
        ("↑", "U+2191 Up arrow"),
        ("↓", "U+2193 Down arrow"),
        ("⇑", "U+21D1 Double up"),
        ("⇓", "U+21D3 Double down"),
        ("⇡", "U+21E1 Dashed up"),
        ("⇣", "U+21E3 Dashed down"),
        ("↟", "U+219F Two headed up"),
        ("↡", "U+21A1 Two headed down"),
    ],
    "More Up/Down Arrows": [
        ("⬆", "U+2B06 Black up arrow"),
        ("⬇", "U+2B07 Black down arrow"),
        ("▲", "U+25B2 Black up tri"),
        ("▼", "U+25BC Black down tri"),
        ("△", "U+25B3 White up tri"),
        ("▽", "U+25BD White down tri"),
        ("⏶", "U+23F6 Black medium up tri"),
        ("⏷", "U+23F7 Black medium down tri"),
    ],
    "Arrow Variants": [
        ("↥", "U+21A5 Up from bar"),
        ("↧", "U+21A7 Down from bar"),
        ("⤊", "U+290A Up triple arrow"),
        ("⤋", "U+290B Down triple arrow"),
        ("⥉", "U+2949 Up with horiz"),
        ("⥌", "U+294C Up paired"),
        ("⥍", "U+294D Down paired"),
        ("⥏", "U+294F Up triangle-head"),
    ],
    "Location/GPS": [
        ("⌖", "U+2316 Position indicator"),
        ("⊕", "U+2295 Circled plus"),
        ("⊗", "U+2297 Circled times"),
        ("⊙", "U+2299 Circled dot"),
        ("◎", "U+25CE Bullseye"),
        ("◉", "U+25C9 Fisheye"),
        ("⌾", "U+233E APL circle"),
        ("⎊", "U+238A Circled triangle"),
    ],
    "Geometric Shapes": [
        ("■", "U+25A0 Black square"),
        ("□", "U+25A1 White square"),
        ("▪", "U+25AA Small black sq"),
        ("▫", "U+25AB Small white sq"),
        ("▬", "U+25AC Black rect"),
        ("▮", "U+25AE Black vert rect"),
        ("●", "U+25CF Black circle"),
        ("○", "U+25CB White circle"),
    ],
    "Triangles": [
        ("▲", "U+25B2 Black up tri"),
        ("△", "U+25B3 White up tri"),
        ("▶", "U+25B6 Black right tri"),
        ("▷", "U+25B7 White right tri"),
        ("▼", "U+25BC Black down tri"),
        ("◀", "U+25C0 Black left tri"),
        ("►", "U+25BA Black right ptr"),
        ("◄", "U+25C4 Black left ptr"),
    ],
    "Stars and Checks": [
        ("★", "U+2605 Black star"),
        ("☆", "U+2606 White star"),
        ("✓", "U+2713 Check mark"),
        ("✔", "U+2714 Heavy check"),
        ("✗", "U+2717 Ballot X"),
        ("✘", "U+2718 Heavy ballot X"),
        ("✦", "U+2726 Black 4-star"),
        ("✧", "U+2727 White 4-star"),
    ],
    "Misc Technical": [
        ("⚙", "U+2699 Gear"),
        ("⚠", "U+26A0 Warning"),
        ("⛔", "U+26D4 No entry"),
        ("☢", "U+2622 Radioactive"),
        ("☣", "U+2623 Biohazard"),
        ("⚛", "U+269B Atom symbol"),
        ("⚬", "U+26AC Medium circle"),
        ("⛭", "U+26ED Gear no hub"),
    ],
    "Weather/Nature": [
        ("☀", "U+2600 Black sun"),
        ("☁", "U+2601 Cloud"),
        ("☂", "U+2602 Umbrella"),
        ("☃", "U+2603 Snowman"),
        ("☄", "U+2604 Comet"),
        ("★", "U+2605 Star"),
        ("☇", "U+2607 Lightning"),
        ("☈", "U+2608 Thunderstorm"),
    ],
    "Block Elements": [
        ("▀", "U+2580 Upper half"),
        ("▄", "U+2584 Lower half"),
        ("█", "U+2588 Full block"),
        ("▌", "U+258C Left half"),
        ("▐", "U+2590 Right half"),
        ("░", "U+2591 Light shade"),
        ("▒", "U+2592 Medium shade"),
        ("▓", "U+2593 Dark shade"),
    ],
    "Greek Letters (common in tech)": [
        ("Ω", "U+03A9 Omega"),
        ("Δ", "U+0394 Delta"),
        ("Σ", "U+03A3 Sigma"),
        ("Π", "U+03A0 Pi"),
        ("μ", "U+03BC Mu (micro)"),
        ("α", "U+03B1 Alpha"),
        ("β", "U+03B2 Beta"),
        ("γ", "U+03B3 Gamma"),
    ],
    "Math Symbols": [
        ("±", "U+00B1 Plus-minus"),
        ("×", "U+00D7 Multiply"),
        ("÷", "U+00F7 Divide"),
        ("∞", "U+221E Infinity"),
        ("√", "U+221A Square root"),
        ("∑", "U+2211 Summation"),
        ("∏", "U+220F Product"),
        ("∂", "U+2202 Partial diff"),
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
        
        # Show available fonts for debugging (use static method to avoid deprecation)
        families = QFontDatabase.families()
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
        example_group = QGroupBox("Example Usage in Dashboard Labels")
        example_layout = QVBoxLayout(example_group)
        
        examples = [
            # Power/Battery items
            ("⚡ ICP", "ICP battery"),
            ("⚡ Node", "Node battery"),
            ("⚡ Ch0", "Channel power"),
            ("↯ Power", "Alt lightning"),
            # Temperature
            ("℃ Temp", "Celsius temp"),
            ("° Temp", "Degree temp"),
            # SNR/Signal
            ("⌖ SNR", "Position SNR"),
            ("⊕ SNR", "Circle+ SNR"),
            # Humidity
            ("≈ Humid", "Approx humidity"),
            ("∿ Humid", "Wave humidity"),
            # Messages
            ("✉ Msg", "Envelope msg"),
            ("☎ Call", "Phone"),
            # Location
            ("◎ GPS", "Bullseye GPS"),
            ("⊙ Loc", "Circled dot"),
            # Misc
            ("⚙ Set", "Gear settings"),
            ("⚠ Alert", "Warning alert"),
            ("★ Fav", "Star favorite"),
            ("✓ OK", "Check OK"),
            # Weather
            ("☀ Sun", "Sun weather"),
            ("☁ Cloud", "Cloud"),
        ]
        
        example_grid = QGridLayout()
        for i, (label, desc) in enumerate(examples):
            row = i // 6
            col = i % 6
            
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

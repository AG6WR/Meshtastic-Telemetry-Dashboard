#!/usr/bin/env python3
"""
Qt/PySide6 Matplotlib-based plotting for telemetry data with intelligent time axis formatting
"""

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QRadioButton, QCheckBox, QGroupBox, QButtonGroup,
    QPushButton, QScrollArea, QFrame, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QImage, QPixmap, QIcon

# Matplotlib imports for Qt integration
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from qt_styles import COLORS, FONTS, create_button, CHECKBOX_STYLE, RADIOBUTTON_STYLE, GROUPBOX_STYLE

logger = logging.getLogger(__name__)


class DarkNavigationToolbar(NavigationToolbar):
    """Custom NavigationToolbar that ensures light icons for dark theme backgrounds.
    
    On some platforms (like Raspberry Pi / Linux), matplotlib uses dark icons
    even when we want a dark-themed toolbar. This class inverts the icons
    if they appear to be dark (designed for light backgrounds).
    """
    
    def __init__(self, canvas, parent=None, coordinates=True):
        super().__init__(canvas, parent, coordinates)
        self._ensure_light_icons()
    
    def _ensure_light_icons(self):
        """Check if icons are dark and invert them if needed for dark backgrounds."""
        for action in self.actions():
            icon = action.icon()
            if icon.isNull():
                continue
            
            # Get all available sizes
            sizes = icon.availableSizes()
            if not sizes:
                continue
            
            # Check if this icon is "dark" (designed for light background)
            # by sampling the pixmap - if mostly dark, we need to invert
            pixmap = icon.pixmap(sizes[0])
            image = pixmap.toImage()
            
            if self._is_dark_icon(image):
                # Create a new icon with inverted colors
                new_icon = QIcon()
                for size in sizes:
                    pixmap = icon.pixmap(size)
                    image = pixmap.toImage()
                    image.invertPixels(QImage.InvertMode.InvertRgb)
                    new_pixmap = QPixmap.fromImage(image)
                    new_icon.addPixmap(new_pixmap)
                action.setIcon(new_icon)
    
    def _is_dark_icon(self, image: QImage) -> bool:
        """Determine if an icon is dark (designed for light background).
        
        Sample pixels and check if the average brightness is low.
        """
        if image.isNull():
            return False
        
        total_brightness = 0
        sample_count = 0
        
        # Sample a grid of pixels
        width = image.width()
        height = image.height()
        step = max(1, min(width, height) // 8)
        
        for x in range(0, width, step):
            for y in range(0, height, step):
                color = image.pixelColor(x, y)
                # Only count non-transparent pixels
                if color.alpha() > 128:
                    # Calculate brightness (0-255)
                    brightness = (color.red() + color.green() + color.blue()) / 3
                    total_brightness += brightness
                    sample_count += 1
        
        if sample_count == 0:
            return False
        
        avg_brightness = total_brightness / sample_count
        # If average brightness is below 128, it's a "dark" icon
        return avg_brightness < 128


class PlotConfigDialog(QDialog):
    """Configuration dialog for plot options"""
    
    def __init__(self, parent, available_nodes, preselect_node_id=None):
        super().__init__(parent)
        self.available_nodes = available_nodes
        self.preselect_node_id = preselect_node_id
        self.result = None
        self.node_checkboxes = {}
        
        self.setWindowTitle("Plot Configuration")
        self.setMinimumSize(500, 580)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_main']};
            }}
            QLabel {{
                color: {COLORS['fg_normal']};
                font-size: 12pt;
            }}
            {GROUPBOX_STYLE}
            {RADIOBUTTON_STYLE}
            {CHECKBOX_STYLE}
            QScrollArea {{
                background-color: {COLORS['bg_frame']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['bg_frame']};
                width: 16px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #555555;
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Title
        title = QLabel("Telemetry Plot Configuration")
        title.setStyleSheet(f"font-size: 14pt; font-weight: bold; color: {COLORS['fg_normal']};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Parameter selection
        param_group = QGroupBox("Parameter to Plot")
        param_layout = QGridLayout(param_group)
        param_layout.setSpacing(4)
        
        self.param_group = QButtonGroup(self)
        param_options = [
            ("Temperature (°C)", "temperature"),
            ("SNR (dB)", "snr"),
            ("Humidity (%)", "humidity"),
            ("Internal Battery Voltage (V)", "internal_voltage"),
            ("External Battery Voltage (V)", "external_voltage"),
            ("Internal Current (mA)", "internal_current"),
            ("External Current (scaled)", "external_current"),
            ("Channel Utilization (%)", "channel_utilization"),
        ]
        
        for i, (text, value) in enumerate(param_options):
            rb = QRadioButton(text)
            rb.setProperty("param_value", value)
            if value == "temperature":
                rb.setChecked(True)
            self.param_group.addButton(rb)
            row = i % 4
            col = i // 4
            param_layout.addWidget(rb, row, col)
        
        layout.addWidget(param_group)
        
        # Time window selection
        time_group = QGroupBox("Time Window")
        time_layout = QGridLayout(time_group)
        time_layout.setSpacing(4)
        
        self.time_group = QButtonGroup(self)
        time_options = [
            ("Last 24 hours", "1"),
            ("Last 3 days", "3"),
            ("Last week", "7"),
            ("Last 2 weeks", "14"),
            ("Last month", "30"),
            ("All available", "all"),
        ]
        
        for i, (text, value) in enumerate(time_options):
            rb = QRadioButton(text)
            rb.setProperty("time_value", value)
            if value == "7":
                rb.setChecked(True)
            self.time_group.addButton(rb)
            row = i % 3
            col = i // 3
            time_layout.addWidget(rb, row, col)
        
        layout.addWidget(time_group)
        
        # Node selection
        node_group = QGroupBox("Select Nodes")
        node_layout = QVBoxLayout(node_group)
        node_layout.setSpacing(4)
        
        # Select All checkbox
        select_all_default = (self.preselect_node_id is None)
        self.select_all_cb = QCheckBox("All Nodes")
        self.select_all_cb.setChecked(select_all_default)
        self.select_all_cb.stateChanged.connect(self._toggle_all_nodes)
        node_layout.addWidget(self.select_all_cb)
        
        # Scrollable area for nodes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(150)
        
        scroll_widget = QWidget()
        scroll_widget.setObjectName("nodeScrollContent")
        scroll_widget.setStyleSheet(f"QWidget#nodeScrollContent {{ background-color: {COLORS['bg_frame']}; }}")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(2)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        for node_id, node_info in self.available_nodes.items():
            should_select = (node_id == self.preselect_node_id) if self.preselect_node_id else True
            
            display_name = f"{node_info['long_name']} ({node_info['short_name']})"
            cb = QCheckBox(display_name)
            cb.setStyleSheet("background-color: transparent;")
            cb.setChecked(should_select)
            cb.setProperty("node_id", node_id)
            self.node_checkboxes[node_id] = cb
            scroll_layout.addWidget(cb)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        node_layout.addWidget(scroll)
        
        layout.addWidget(node_group)
        
        # Buttons - standard layout: stretch, then action buttons, Cancel on far right
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        plot_btn = create_button("Plot", "success")
        plot_btn.clicked.connect(self._on_plot)
        button_layout.addWidget(plot_btn)
        
        cancel_btn = create_button("✗ Cancel", "neutral")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _toggle_all_nodes(self, state):
        """Toggle all node checkboxes"""
        checked = state == Qt.CheckState.Checked.value
        for cb in self.node_checkboxes.values():
            cb.setChecked(checked)
    
    def _on_plot(self):
        """Handle plot button click"""
        selected_nodes = [
            node_id for node_id, cb in self.node_checkboxes.items()
            if cb.isChecked()
        ]
        
        if not selected_nodes:
            QMessageBox.warning(self, "No Selection", "Please select at least one node.")
            return
        
        # Get selected parameter
        param_value = "temperature"
        for btn in self.param_group.buttons():
            if btn.isChecked():
                param_value = btn.property("param_value")
                break
        
        # Get selected time window
        time_value = "7"
        for btn in self.time_group.buttons():
            if btn.isChecked():
                time_value = btn.property("time_value")
                break
        
        self.result = {
            'nodes': selected_nodes,
            'days': time_value if time_value == 'all' else int(time_value),
            'parameter': param_value
        }
        self.accept()


class PlotWindow(QDialog):
    """Window displaying the matplotlib plot"""
    
    def __init__(self, parent, data, config, param_info):
        super().__init__(parent)
        self.data = data
        self.config = config
        self.param_info = param_info
        
        # Window title
        time_desc = {
            1: "24 Hours", 3: "3 Days", 7: "7 Days", 14: "2 Weeks", 30: "30 Days"
        }
        param_name = param_info[config['parameter']]['name']
        days_text = time_desc.get(config['days'], "All Available" if config['days'] == 'all' else f"{config['days']} Days")
        self.setWindowTitle(f"{param_name} Plot - Last {days_text}")
        self.setMinimumSize(1000, 700)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_main']};
            }}
        """)
        
        self._setup_ui(days_text)
    
    def _setup_ui(self, days_text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        # Create matplotlib figure with dark theme
        self.figure = Figure(figsize=(10, 7), facecolor='#1e1e1e')
        self.ax = self.figure.add_subplot(111, facecolor='#2d2d2d')
        
        # Create canvas
        self.canvas = FigureCanvas(self.figure)
        
        # Create navigation toolbar with inverted icons for dark theme
        self.toolbar = DarkNavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {COLORS['bg_frame']};
                border: none;
                spacing: 5px;
                padding: 2px;
            }}
            QToolButton {{
                background-color: {COLORS['bg_frame']};
                color: {COLORS['fg_normal']};
                border: 1px solid #505050;
                border-radius: 3px;
                padding: 4px;
                margin: 1px;
            }}
            QToolButton:hover {{
                background-color: {COLORS['bg_input']};
                border: 1px solid #707070;
            }}
            QToolButton:pressed {{
                background-color: #404040;
            }}
            QLabel {{
                color: {COLORS['fg_normal']};
            }}
            QLineEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['fg_normal']};
                border: 1px solid #505050;
            }}
        """)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Create the plot
        self._create_plot(days_text)
    
    def _create_plot(self, days_text):
        """Create the matplotlib plot"""
        info = self.param_info[self.config['parameter']]
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF']
        
        # Plot each node's data
        plot_lines = []
        color_idx = 0
        
        for node_id, node_entry in self.data.items():
            node_data = node_entry['data']
            node_info = node_entry['info']
            
            if not node_data:
                continue
            
            timestamps = [point[0] for point in node_data]
            values = [point[1] for point in node_data]
            
            label = f"{node_info['long_name']} ({node_info['short_name']})"
            line, = self.ax.plot(timestamps, values, 'o-', label=label, 
                                markersize=4, linewidth=1.5, picker=5,
                                color=colors[color_idx % len(colors)])
            plot_lines.append((line, timestamps, values, label))
            color_idx += 1
        
        # Configure axes
        self.ax.set_xlabel('Time', color='white', fontsize=12)
        self.ax.set_ylabel(f"{info['name']} ({info['unit']})", color='white', fontsize=12)
        self.ax.set_title(f"{info['name']} vs Time (Last {days_text})",
                         color='white', fontsize=14, fontweight='bold', pad=20)
        
        # Set Y-axis range
        self.ax.set_ylim(info['min_val'], info['max_val'])
        
        # Calculate requested days for formatting
        requested_days = self.config['days']
        if requested_days == 'all':
            all_times = []
            for node_entry in self.data.values():
                all_times.extend([point[0] for point in node_entry['data']])
            if all_times:
                requested_days = (max(all_times) - min(all_times)).days + 1
            else:
                requested_days = 7
        
        # Format time axis based on time window
        self._format_time_axis(requested_days)
        
        # Set x-axis limits
        now = datetime.now()
        if self.config['days'] == 'all':
            all_times = []
            for node_entry in self.data.values():
                all_times.extend([point[0] for point in node_entry['data']])
            if all_times:
                self.ax.set_xlim(mdates.date2num(min(all_times)), mdates.date2num(max(all_times)))
        else:
            x_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            x_start = (now - timedelta(days=self.config['days'])).replace(hour=0, minute=0, second=0, microsecond=0)
            self.ax.set_xlim(mdates.date2num(x_start), mdates.date2num(x_end))
        
        # Rotate date labels
        self.figure.autofmt_xdate(rotation=45, ha='right')
        
        # Style axes
        self.ax.tick_params(axis='x', colors='white', labelsize=10, which='major', length=6)
        self.ax.tick_params(axis='x', colors='white', which='minor', length=3)
        self.ax.tick_params(axis='y', colors='white', labelsize=10)
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        
        # Add gridlines
        self.ax.grid(True, which='major', alpha=0.35, color='#888888', linestyle='-', linewidth=0.8)
        self.ax.grid(True, which='minor', alpha=0.35, color='#777777', linestyle=':', linewidth=0.7)
        
        # Legend
        legend = self.ax.legend(loc='upper left', framealpha=0.9, facecolor='#2d2d2d',
                               edgecolor='white', fontsize=10)
        for text in legend.get_texts():
            text.set_color('white')
        
        # Add hover annotation
        self.annot = self.ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                                      bbox=dict(boxstyle="round,pad=0.5", fc="#2d2d2d", ec="white", alpha=0.95),
                                      arrowprops=dict(arrowstyle="->", color="white"),
                                      color='white', fontsize=10, visible=False)
        
        self.plot_lines = plot_lines
        self.canvas.mpl_connect("motion_notify_event", self._on_hover)
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _format_time_axis(self, requested_days):
        """Format time axis based on requested time window"""
        if requested_days <= 1:
            major_locator = mdates.HourLocator(byhour=range(0, 24, 3))
            minor_locator = mdates.HourLocator()
            formatter = mdates.DateFormatter('%H:%M')
        elif requested_days <= 3:
            major_locator = mdates.DayLocator()
            minor_locator = mdates.HourLocator(byhour=[0, 6, 12, 18])
            formatter = mdates.DateFormatter('%m/%d\n%H:%M')
        elif requested_days <= 7:
            major_locator = mdates.DayLocator()
            minor_locator = mdates.HourLocator(byhour=[0, 6, 12, 18])
            formatter = mdates.DateFormatter('%m/%d\n%H:%M')
        elif requested_days <= 14:
            major_locator = mdates.DayLocator()
            minor_locator = mdates.HourLocator(byhour=[0, 12])
            formatter = mdates.DateFormatter('%m/%d')
        elif requested_days <= 30:
            major_locator = mdates.DayLocator(interval=2)
            minor_locator = mdates.DayLocator()
            formatter = mdates.DateFormatter('%m/%d')
        else:
            major_locator = mdates.WeekdayLocator()
            minor_locator = mdates.DayLocator(interval=2)
            formatter = mdates.DateFormatter('%m/%d')
        
        self.ax.xaxis.set_major_locator(major_locator)
        self.ax.xaxis.set_major_formatter(formatter)
        if minor_locator:
            self.ax.xaxis.set_minor_locator(minor_locator)
    
    def _on_hover(self, event):
        """Handle mouse hover events"""
        info = self.param_info[self.config['parameter']]
        
        if event.inaxes == self.ax:
            for line, timestamps, values, label in self.plot_lines:
                cont, ind = line.contains(event)
                if cont:
                    idx = ind["ind"][0]
                    x_val = mdates.date2num(timestamps[idx])
                    y_val = values[idx]
                    
                    self.annot.xy = (x_val, y_val)
                    time_str = mdates.num2date(x_val).strftime('%Y-%m-%d %H:%M')
                    text = f"{label}\n{time_str}\n{info['name']}: {y_val:.2f} {info['unit']}"
                    self.annot.set_text(text)
                    self.annot.set_visible(True)
                    self.canvas.draw_idle()
                    return
        
        self.annot.set_visible(False)
        self.canvas.draw_idle()


class TelemetryPlotterQt:
    """Qt-based telemetry plotter using matplotlib"""
    
    # Parameter info for axis labels and ranges
    PARAM_INFO = {
        'temperature': {'name': 'Temperature', 'unit': '°C', 'min_val': 0, 'max_val': 50},
        'snr': {'name': 'SNR', 'unit': 'dB', 'min_val': -15, 'max_val': 15},
        'humidity': {'name': 'Humidity', 'unit': '%', 'min_val': 0, 'max_val': 100},
        'internal_voltage': {'name': 'Internal Battery Voltage', 'unit': 'V', 'min_val': 3.0, 'max_val': 4.5},
        'external_voltage': {'name': 'External Battery Voltage', 'unit': 'V', 'min_val': 10, 'max_val': 15},
        'internal_current': {'name': 'Internal Current', 'unit': 'mA', 'min_val': 0, 'max_val': 200},
        'external_current': {'name': 'External Current (Scaled)', 'unit': 'mA', 'min_val': -5000, 'max_val': 5000},
        'channel_utilization': {'name': 'Channel Utilization', 'unit': '%', 'min_val': 0, 'max_val': 50}
    }
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
    
    def show_plot_dialog(self, preselect_node_id=None):
        """Show plot configuration dialog"""
        try:
            # Get available nodes
            available_nodes = self.get_available_nodes()
            if not available_nodes:
                QMessageBox.warning(self.parent, "No Data", "No nodes with historical data found.")
                return
            
            # Show configuration dialog
            dialog = PlotConfigDialog(self.parent, available_nodes, preselect_node_id)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            
            config = dialog.result
            if not config:
                return
            
            # Load data
            data = self.load_telemetry_data(config['nodes'], config['days'], config['parameter'])
            if not data:
                param_name = config['parameter'].replace('_', ' ').title()
                QMessageBox.warning(self.parent, "No Data", f"No {param_name} data found for selected criteria.")
                return
            
            # Create plot window
            plot_window = PlotWindow(self.parent, data, config, self.PARAM_INFO)
            plot_window.exec()
            
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            QMessageBox.critical(self.parent, "Plot Error", f"Failed to create plot: {e}")
    
    def get_available_nodes(self):
        """Get list of nodes that have log data"""
        log_dir = Path(self.config_manager.get('data.log_directory', 'logs'))
        available_nodes = {}
        
        if not log_dir.exists():
            return {}
        
        for node_dir in log_dir.iterdir():
            if not node_dir.is_dir():
                continue
            
            node_id = node_dir.name
            year_dir = node_dir / "2025"
            
            if year_dir.exists() and any(year_dir.glob("*.csv")):
                # Try to get node info from most recent CSV
                node_info = None
                for csv_file in sorted(year_dir.glob("*.csv"), reverse=True):
                    try:
                        with open(csv_file, 'r') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                long_name = row.get('long_name', '').strip()
                                short_name = row.get('short_name', '').strip()
                                if long_name and long_name != 'Unknown Node':
                                    node_info = {'long_name': long_name, 'short_name': short_name}
                                    break
                            if node_info:
                                break
                    except:
                        continue
                
                if not node_info:
                    node_info = {'long_name': 'Unknown', 'short_name': node_id[-4:]}
                
                available_nodes[node_id] = node_info
        
        return available_nodes
    
    def load_telemetry_data(self, selected_nodes, days, parameter):
        """Load telemetry data for selected nodes and time period"""
        log_dir = Path(self.config_manager.get('data.log_directory', 'logs'))
        
        # Calculate date range
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if days == 'all':
            start_date = datetime(2020, 1, 1)
        else:
            start_date = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        all_data = {}
        
        for node_id in selected_nodes:
            node_dir = log_dir / node_id
            if not node_dir.exists():
                continue
            
            node_data = []
            node_info = None
            
            year_dir = node_dir / "2025"
            if not year_dir.exists():
                continue
            
            # Read files for selected time period
            current_date = start_date
            while current_date <= end_date:
                csv_file = year_dir / f"{current_date.strftime('%Y%m%d')}.csv"
                if csv_file.exists():
                    data, info = self._read_telemetry_from_csv(csv_file, start_date, end_date, parameter)
                    node_data.extend(data)
                    if info and node_info is None:
                        node_info = info
                current_date += timedelta(days=1)
            
            if node_data:
                all_data[node_id] = {
                    'data': sorted(node_data, key=lambda x: x[0]),
                    'info': node_info or {'long_name': 'Unknown', 'short_name': node_id[-4:]}
                }
        
        return all_data
    
    def _read_telemetry_from_csv(self, csv_file, start_date, end_date, parameter):
        """Read telemetry data from a single CSV file"""
        data = []
        node_info = None
        
        param_map = {
            'temperature': 'temperature',
            'snr': 'snr',
            'humidity': 'humidity',
            'internal_voltage': 'voltage',
            'external_voltage': 'ch3_voltage',
            'internal_current': 'current',
            'external_current': 'ch3_current_scaled_ma',
            'channel_utilization': 'channel_utilization'
        }
        
        csv_column = param_map.get(parameter, parameter)
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        timestamp = datetime.fromisoformat(row['iso_time'].replace('Z', '+00:00'))
                        
                        if not (start_date <= timestamp <= end_date):
                            continue
                        
                        if node_info is None:
                            long_name = row.get('long_name', '').strip()
                            short_name = row.get('short_name', '').strip()
                            if long_name and long_name != 'Unknown Node':
                                node_info = {'long_name': long_name, 'short_name': short_name}
                        
                        value_str = row.get(csv_column, '').strip()
                        
                        if value_str and value_str != '':
                            value = float(value_str)
                            data.append((timestamp, value))
                            
                    except (ValueError, KeyError):
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading {csv_file}: {e}")
        
        return data, node_info


# Demo/test mode
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # Create a mock config manager for testing
    class MockConfigManager:
        def get(self, key, default=None):
            if key == 'data.log_directory':
                return 'logs'
            return default
    
    # Create a parent window
    parent = QWidget()
    parent.setWindowTitle("Plotter Test")
    parent.resize(200, 100)
    parent.show()
    
    # Create plotter and show dialog
    plotter = TelemetryPlotterQt(parent, MockConfigManager())
    plotter.show_plot_dialog()
    
    sys.exit(app.exec())

"""
formatters.py - Pure formatting and color-coding functions for Meshtastic Dashboard

This module contains stateless formatting functions extracted from dashboard.py
as part of Phase 1 modularization. These functions format values for display
and determine colors based on thresholds.

All functions are pure (no side effects) and can be reused by both Tkinter 
and Qt UI implementations.

Usage:
    from formatters import format_temperature, get_temperature_color
    
    temp_text = format_temperature(35.5, colors, config_manager)
    temp_color = get_temperature_color(35.5, colors, config_manager)
"""

from typing import Dict, Tuple, List, Optional


# =============================================================================
# Color Constants (default theme)
# =============================================================================

DEFAULT_COLORS = {
    'bg_main': '#1e1e1e',
    'bg_frame': '#2d2d2d',
    'bg_local_node': '#1e2d1e',
    'bg_stale': '#3d2d2d',
    'bg_selected': '#1a237e',
    'fg_normal': '#ffffff',
    'fg_secondary': '#b0b0b0',
    'button_bg': '#404040',
    'button_fg': '#ffffff',
    'fg_good': '#228B22',
    'fg_warning': '#FFA500',
    'fg_yellow': '#FFFF00',
    'fg_bad': '#FF6B9D',
    'accent': '#4a90d9'
}


# =============================================================================
# Temperature Functions
# =============================================================================

def convert_temperature(temp_c: float, config_manager=None, to_unit: Optional[str] = None) -> Tuple[float, str, Tuple[int, int]]:
    """Convert temperature from Celsius to the configured unit
    
    Args:
        temp_c: Temperature in Celsius
        config_manager: ConfigManager instance (optional, defaults to Celsius)
        to_unit: Override unit ('C' or 'F'), or None to use config setting
        
    Returns:
        tuple: (converted_value, unit_string, thresholds_tuple)
               thresholds_tuple = (red_threshold, yellow_threshold)
    """
    if to_unit is None:
        if config_manager:
            to_unit = config_manager.get('dashboard.temperature_unit', 'C')
        else:
            to_unit = 'C'
    
    if to_unit == 'F':
        # Convert to Fahrenheit: F = C * 9/5 + 32
        temp_f = temp_c * 9/5 + 32
        # Thresholds: 45°C = 113°F, 35°C = 95°F
        return (temp_f, '°F', (113, 95))
    else:
        # Keep in Celsius
        return (temp_c, '°C', (45, 35))


def format_temperature(temp_c: float, config_manager=None) -> str:
    """Format temperature value (number only, unit is separate label)"""
    temp_value, temp_unit_str, _ = convert_temperature(temp_c, config_manager)
    return f"{temp_value:.0f}"


def get_temperature_color(temp_c: float, colors: Dict[str, str], config_manager=None) -> str:
    """Get color based on temperature thresholds"""
    _, _, (red_threshold, yellow_threshold) = convert_temperature(temp_c, config_manager)
    if temp_c > red_threshold or temp_c < 0:
        return colors.get('fg_bad', DEFAULT_COLORS['fg_bad'])
    elif temp_c >= yellow_threshold:
        return colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])
    else:
        return colors.get('fg_good', DEFAULT_COLORS['fg_good'])


# =============================================================================
# Humidity Functions
# =============================================================================

def format_humidity(humidity: float) -> str:
    """Format humidity value"""
    return f"{humidity:.0f}%"


def get_humidity_color(humidity: float, colors: Dict[str, str]) -> str:
    """Get color based on humidity thresholds"""
    if humidity > 80 or humidity < 20:
        return colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])
    else:
        return colors.get('fg_good', DEFAULT_COLORS['fg_good'])


# =============================================================================
# Pressure Functions
# =============================================================================

def format_pressure(pressure: float) -> str:
    """Format pressure value (number only, unit is separate label)"""
    return f"{pressure:.1f}"


def get_pressure_color(pressure: float, colors: Dict[str, str]) -> str:
    """Get color based on pressure (always normal for now)"""
    return colors.get('fg_normal', DEFAULT_COLORS['fg_normal'])


# =============================================================================
# Channel/Air Utilization Functions
# =============================================================================

def format_channel_util(util: float) -> str:
    """Format channel utilization percentage"""
    return f"Ch: {util:.1f}%"


def get_channel_util_color(util: float, colors: Dict[str, str]) -> str:
    """Get color based on channel utilization thresholds"""
    if util > 25:
        return colors.get('fg_bad', DEFAULT_COLORS['fg_bad'])
    elif util > 10:
        return colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])
    else:
        return colors.get('fg_good', DEFAULT_COLORS['fg_good'])


def format_air_util(util: float) -> str:
    """Format air utilization percentage"""
    return f"Air: {util:.1f}%"


def get_air_util_color(util: float, colors: Dict[str, str]) -> str:
    """Get color based on air utilization thresholds"""
    if util > 10:
        return colors.get('fg_bad', DEFAULT_COLORS['fg_bad'])
    elif util > 5:
        return colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])
    else:
        return colors.get('fg_good', DEFAULT_COLORS['fg_good'])


# =============================================================================
# Time Formatting Functions
# =============================================================================

def format_duration(seconds: int, config_manager=None) -> str:
    """Format duration according to configured format"""
    if config_manager:
        time_format = config_manager.get('dashboard.time_format', 'DDd:HHh:MMm:SSs')
    else:
        time_format = 'DDd:HHh:MMm:SSs'
    
    if time_format in ['DD:HH:MM:SS', 'DDd:HHh:MMm:SSs']:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{days:02d}d:{hours:02d}h:{minutes:02d}m:{secs:02d}s"
    elif time_format == 'Minutes':
        return f"{seconds // 60}m"
    else:  # Seconds
        return f"{seconds}s"


def format_time_ago(seconds: float) -> str:
    """Format time difference as human readable string"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m"
    elif seconds < 86400:
        return f"{int(seconds // 3600)}h"
    else:
        return f"{int(seconds // 86400)}d"


# =============================================================================
# Voltage/Battery Functions
# =============================================================================

def get_voltage_display(voltage: Optional[float], colors: Dict[str, str]) -> Tuple[str, str]:
    """Get voltage display with appropriate color coding
    
    Returns:
        tuple: (text, color)
    """
    if voltage is not None:
        # Match table view: Red if <11V or >14.5V, Yellow if 11-12V or 14-14.5V, Green if 12-14V
        if voltage < 11.0 or voltage > 14.5:
            color = colors.get('fg_bad', DEFAULT_COLORS['fg_bad'])
        elif voltage < 12.0 or voltage > 14.0:
            color = colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])
        else:
            color = colors.get('fg_good', DEFAULT_COLORS['fg_good'])
        return f"{voltage:.1f}V", color
    else:
        return "No voltage", colors.get('fg_secondary', DEFAULT_COLORS['fg_secondary'])


def get_battery_percentage_display(node_data: dict, colors: Dict[str, str], 
                                    data_collector=None) -> Tuple[str, str]:
    """Get battery percentage display with appropriate color coding
    
    Determines battery % from either:
    - Ch3 Voltage (external LiFePO4) converted via interpolation
    - Battery Level (internal Li+ cell) from deviceMetrics
    
    Args:
        node_data: Dictionary containing node telemetry data
        colors: Color dictionary
        data_collector: DataCollector instance for voltage conversion (optional)
        
    Returns: 
        tuple: (text, color)
    """
    # Try external battery first (Ch3 Voltage)
    ch3_voltage = node_data.get('Ch3 Voltage')
    if ch3_voltage is not None and data_collector:
        battery_pct = data_collector.voltage_to_percentage(ch3_voltage)
        if battery_pct is not None:
            # Color coding: 0-25% red, 25-50% yellow, >50% green
            if battery_pct > 50:
                color = colors.get('fg_good', DEFAULT_COLORS['fg_good'])
            elif battery_pct >= 25:
                color = colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])
            else:
                color = colors.get('fg_bad', DEFAULT_COLORS['fg_bad'])
            return f"Bat:{battery_pct}%", color
    
    # Fall back to internal battery percentage
    internal_battery = node_data.get('Battery Level')
    if internal_battery is not None:
        # Color coding: 0-25% red, 25-50% yellow, >50% green
        if internal_battery > 50:
            color = colors.get('fg_good', DEFAULT_COLORS['fg_good'])
        elif internal_battery >= 25:
            color = colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])
        else:
            color = colors.get('fg_bad', DEFAULT_COLORS['fg_bad'])
        return f"Bat:{internal_battery}%", color
    
    # No battery data available
    return "no external battery sensor", colors.get('fg_secondary', DEFAULT_COLORS['fg_secondary'])


# =============================================================================
# Current Functions (External Current Sensor with Scaling)
# =============================================================================

# Default shunt resistor: 350mV / 3.5A = 100mOhm
DEFAULT_SHUNT_RESISTANCE_MOHM = 100.0

def get_current_scale_factor(config_manager=None, node_id: str = None) -> float:
    """Calculate current scaling factor from config settings
    
    The INA sensor measures voltage across a shunt resistor and the firmware
    assumes a standard 100mOhm shunt (350mV at 3.5A). If the user has a different
    shunt resistor, we need to scale the reported current.
    
    Scale factor = default_shunt / user_shunt
    Where shunt = full_scale_voltage_mv / full_scale_current_a
    
    Args:
        config_manager: ConfigManager instance
        node_id: Optional node ID for per-node settings (falls back to default)
        
    Returns:
        Scale factor to multiply raw current by (1.0 if disabled or not configured)
    """
    if not config_manager:
        return 1.0
    
    # Try node-specific settings first, then fall back to default
    if node_id:
        node_settings = config_manager.get(f'hardware.current_sensor.nodes.{node_id}')
        if node_settings:
            if not node_settings.get('enabled', False):
                return 1.0
            full_scale_mv = node_settings.get('full_scale_voltage_mv', 350)
            full_scale_a = node_settings.get('full_scale_current_a', 3.5)
        else:
            # Fall back to default settings
            if not config_manager.get('hardware.current_sensor.default.enabled', False):
                return 1.0
            full_scale_mv = config_manager.get('hardware.current_sensor.default.full_scale_voltage_mv', 350)
            full_scale_a = config_manager.get('hardware.current_sensor.default.full_scale_current_a', 3.5)
    else:
        # No node_id provided, use default
        if not config_manager.get('hardware.current_sensor.default.enabled', False):
            return 1.0
        full_scale_mv = config_manager.get('hardware.current_sensor.default.full_scale_voltage_mv', 350)
        full_scale_a = config_manager.get('hardware.current_sensor.default.full_scale_current_a', 3.5)
    
    # Avoid division by zero
    if full_scale_a == 0:
        return 1.0
    
    # Calculate user's shunt resistance in mOhm
    # R = V / I, so R(mOhm) = V(mV) / I(A)
    user_shunt_mohm = full_scale_mv / full_scale_a
    
    # Avoid division by zero
    if user_shunt_mohm == 0:
        return 1.0
    
    # Scale factor = default_shunt / user_shunt
    return DEFAULT_SHUNT_RESISTANCE_MOHM / user_shunt_mohm


def scale_current(current_ma: float, config_manager=None, node_id: str = None) -> float:
    """Apply current scaling factor to raw current value
    
    Args:
        current_ma: Raw current in milliamps from telemetry
        config_manager: ConfigManager instance
        node_id: Optional node ID for per-node settings
        
    Returns:
        Scaled current in milliamps
    """
    if current_ma is None:
        return None
    
    scale_factor = get_current_scale_factor(config_manager, node_id)
    return current_ma * scale_factor


def format_current(current_ma: float, config_manager=None, node_id: str = None, include_direction: bool = False) -> str:
    """Format current value with automatic unit selection (mA or A)
    
    Values < 1000mA display as "XXXmA"
    Values >= 1000mA display as "X.XXA"
    
    Args:
        current_ma: Current in milliamps (already scaled if needed)
        config_manager: ConfigManager instance (for scaling if raw value passed)
        include_direction: If True, include up/down arrow based on sign
        
    Returns:
        Formatted current string
    """
    if current_ma is None:
        return ""
    
    # Determine direction indicator
    direction = ""
    if include_direction:
        if current_ma > 0:
            direction = " ⬆"
        elif current_ma < 0:
            direction = " ⬇"
    
    abs_current = abs(current_ma)
    sign = "+" if current_ma > 0 and include_direction else ("-" if current_ma < 0 else "")
    
    if abs_current >= 1000:
        # Display in Amps
        amps = abs_current / 1000
        return f"{sign}{amps:.2f}A{direction}"
    else:
        # Display in milliamps
        return f"{sign}{abs_current:.0f}mA{direction}"


def get_current_color(current_ma: float, colors: Dict[str, str]) -> str:
    """Get color based on current direction (charging vs discharging)
    
    Args:
        current_ma: Current in milliamps (positive = charging, negative = discharging)
        colors: Color dictionary
        
    Returns:
        Color string
    """
    if current_ma is None:
        return colors.get('fg_secondary', DEFAULT_COLORS['fg_secondary'])
    
    if current_ma > 0:
        return colors.get('fg_good', DEFAULT_COLORS['fg_good'])  # Charging
    elif current_ma < 0:
        return colors.get('fg_warning', DEFAULT_COLORS['fg_warning'])  # Discharging
    else:
        return colors.get('fg_normal', DEFAULT_COLORS['fg_normal'])  # Zero


# =============================================================================
# Signal Functions
# =============================================================================

def get_signal_bar_colors(snr: float) -> List[str]:
    """Return list of colors for each of the 4 signal bars based on SNR
    White for 'on' bars, black for 'off' bars
    
    Args:
        snr: Signal-to-noise ratio value
        
    Returns:
        List of 4 color strings (white or black)
    """
    white = '#FFFFFF'
    black = '#000000'
    
    if snr >= 10:
        # All 4 bars on (white)
        return [white, white, white, white]
    elif snr >= 5:
        # 3 bars on, last one off
        return [white, white, white, black]
    elif snr >= 0:
        # 2 bars on, last two off
        return [white, white, black, black]
    elif snr >= -5:
        # 1 bar on, last three off
        return [white, black, black, black]
    else:
        # All bars off (black)
        return [black, black, black, black]

"""
Card Field Registry - Declarative telemetry field display configuration
Separates card layout from update logic for maintainability

This module provides a metadata-driven approach to updating telemetry card widgets.
Instead of hardcoding field positions and update logic in update_node_card(),
the registry maps field names to widget keys, formatting functions, and color rules.

Usage:
    registry = CardFieldRegistry(dashboard)
    field_def = registry.get_field_definition('Temperature')
    formatted_value = registry.format_field(dashboard, 'Temperature', 25.5)
    color = registry.get_field_color(dashboard, 'Temperature', 25.5, is_stale=False)
"""

from typing import Dict, Any, Optional, Callable


class CardFieldRegistry:
    """Registry mapping telemetry fields to display widgets and formatting rules"""
    
    # Layout version for future compatibility
    LAYOUT_VERSION = "1.0"
    
    # Field registry with display metadata
    # Maps telemetry field names to widget configuration
    FIELD_DEFINITIONS = {
        # =====================================================================
        # SIMPLE FIELDS (single label widgets)
        # =====================================================================
        
        'Temperature': {
            'widget_key': 'temp_label',
            'widget_type': 'simple',
            'format_func': 'format_temperature',
            'color_func': 'get_temperature_color',
            'use_stale_color': True
        },
        
        'Humidity': {
            'widget_key': 'humidity_label',
            'widget_type': 'simple',
            'format_func': 'format_humidity',
            'color_func': 'get_humidity_color',
            'use_stale_color': True
        },
        
        'Pressure': {
            'widget_key': 'pressure_label',
            'widget_type': 'simple',
            'format_func': 'format_pressure',
            'color_func': 'get_pressure_color',
            'use_stale_color': True
        },
        
        # =====================================================================
        # COMPOSITE FIELDS (multi-part widgets with nested labels)
        # =====================================================================
        
        'Channel Utilization': {
            'widget_key': 'util_label',
            'widget_type': 'composite',
            'update_func': 'update_channel_util_composite',
            'dependencies': ['Channel Utilization']
        },
        
        'Air Utilization (TX)': {
            'widget_key': 'air_util_label',
            'widget_type': 'composite',
            'update_func': 'update_air_util_composite',
            'dependencies': ['Air Utilization (TX)']
        },
        
        'SNR': {
            'widget_key': 'snr_label',
            'widget_type': 'composite',
            'update_func': 'update_snr_composite',
            'dependencies': ['SNR']
        },
        
        'Ch3 Voltage': {
            'widget_key': 'battery_label',
            'widget_type': 'composite',
            'update_func': 'update_external_battery_composite',
            'dependencies': ['Ch3 Voltage', 'Battery Level', 'Ch3 Current']
        },
        
        'Internal Battery Voltage': {
            'widget_key': 'int_battery_label',
            'widget_type': 'composite',
            'update_func': 'update_internal_battery_composite',
            'dependencies': ['Internal Battery Voltage', 'Battery Level']
        }
    }
    
    def __init__(self, dashboard):
        """Initialize registry with reference to dashboard instance
        
        Args:
            dashboard: EnhancedDashboard instance for accessing methods and colors
        """
        self.dashboard = dashboard
    
    def get_field_definition(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get field definition from registry
        
        Args:
            field_name: Name of telemetry field (e.g., 'Temperature')
            
        Returns:
            Field definition dict or None if not found
        """
        return self.FIELD_DEFINITIONS.get(field_name)
    
    def format_field(self, dashboard, field_name: str, value: Any) -> str:
        """Format field value using registered format function
        
        Args:
            dashboard: EnhancedDashboard instance
            field_name: Name of telemetry field
            value: Raw field value
            
        Returns:
            Formatted string for display
        """
        field_def = self.get_field_definition(field_name)
        if not field_def or field_def['widget_type'] != 'simple':
            return str(value)
        
        format_func_name = field_def.get('format_func')
        if format_func_name and hasattr(dashboard, format_func_name):
            format_func = getattr(dashboard, format_func_name)
            return format_func(value)
        
        return str(value)
    
    def get_field_color(self, dashboard, field_name: str, value: Any, is_stale: bool = False) -> str:
        """Get display color for field value
        
        Args:
            dashboard: EnhancedDashboard instance
            field_name: Name of telemetry field
            value: Raw field value
            is_stale: Whether telemetry data is stale (>16 min old)
            
        Returns:
            Color string from dashboard.colors
        """
        field_def = self.get_field_definition(field_name)
        if not field_def or field_def['widget_type'] != 'simple':
            return dashboard.colors['fg_normal']
        
        # Use stale color if configured and data is stale
        if is_stale and field_def.get('use_stale_color', False):
            return dashboard.colors['fg_secondary']
        
        # Otherwise use color function
        color_func_name = field_def.get('color_func')
        if color_func_name and hasattr(dashboard, color_func_name):
            color_func = getattr(dashboard, color_func_name)
            return color_func(value)
        
        return dashboard.colors['fg_normal']
    
    def get_all_simple_fields(self) -> list:
        """Get list of all simple field names
        
        Returns:
            List of field names with widget_type='simple'
        """
        return [
            name for name, defn in self.FIELD_DEFINITIONS.items()
            if defn.get('widget_type') == 'simple'
        ]
    
    def get_all_composite_fields(self) -> list:
        """Get list of all composite field names
        
        Returns:
            List of field names with widget_type='composite'
        """
        return [
            name for name, defn in self.FIELD_DEFINITIONS.items()
            if defn.get('widget_type') == 'composite'
        ]

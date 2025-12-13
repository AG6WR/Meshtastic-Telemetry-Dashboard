# Card Field Registry Architecture Design

**STATUS: 🚧 IN DEVELOPMENT - Do not merge to main docs yet**

**Created:** 2025-12-13  
**Target Version:** 1.1.0  
**Related Files:** `dashboard.py`, `card_field_registry.py` (to be created)

---

## Problem Statement

### Current Issues
The `update_node_card()` function in `dashboard.py` is tightly coupled to the card layout structure:
- **Hardcoded field positions**: Temperature on row 3, Humidity on row 3, etc.
- **Brittle updates**: Any layout change requires rewriting ~300 lines of update logic
- **No separation of concerns**: Display logic mixed with data update logic
- **Difficult to extend**: Adding new fields requires changes in multiple places
- **Not version-friendly**: Can't easily support multiple card layouts

### User Request
> "Is there any way to have the update node card function not be inherently tied to the format of the card, and instead use more generic access to card elements to update?"

The user wants a **data-driven architecture** where field metadata defines how updates happen, independent of the layout implementation.

---

## Architecture Overview

### Key Concepts

**1. Field Registry**
A declarative mapping of telemetry fields to display metadata:
```python
{
    'Temperature': {
        'widget_key': 'temp_label',
        'widget_type': 'simple',  # or 'composite'
        'format': lambda self, val: self.convert_temperature(val),
        'color_func': lambda self, val: self._temp_color_rule(val),
        'use_stale_color': True
    }
}
```

**2. Widget Types**
- **Simple**: Single label (e.g., "72°F")
- **Composite**: Container with multiple child labels (e.g., battery display, SNR bars)

**3. Update Flow**
```
Telemetry Data → Registry Lookup → Format Value → Calculate Color → Update Widget
```

---

## Module Structure

### New File: `card_field_registry.py`

```python
"""
Card Field Registry - Declarative telemetry field display configuration
Separates card layout from update logic for maintainability
"""

class CardFieldRegistry:
    """Registry mapping telemetry fields to display widgets and formatting rules"""
    
    def __init__(self, dashboard):
        self.dashboard = dashboard
        
    # Layout version for future compatibility
    LAYOUT_VERSION = "1.0"
    
    # Field registry with display metadata
    FIELD_DEFINITIONS = {
        # Simple fields (single label)
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
        
        'Channel Utilization': {
            'widget_key': 'util_label',
            'widget_type': 'simple',
            'format_func': 'format_channel_util',
            'color_func': 'get_channel_util_color',
            'use_stale_color': True
        },
        
        'Air Utilization (TX)': {
            'widget_key': 'air_util_label',
            'widget_type': 'simple',
            'format_func': 'format_air_util',
            'color_func': 'get_air_util_color',
            'use_stale_color': True
        },
        
        # Composite fields (multi-part widgets)
        'SNR': {
            'widget_key': 'snr_label',
            'widget_type': 'composite',
            'update_func': 'update_snr_bars',  # Custom update logic
            'children': [
                {'type': 'label', 'text': 'SNR: ', 'color': 'fg_secondary'},
                {'type': 'bar', 'index': 0},
                {'type': 'bar', 'index': 1},
                {'type': 'bar', 'index': 2},
                {'type': 'bar', 'index': 3}
            ]
        },
        
        'Ch3 Voltage': {
            'widget_key': 'battery_label',
            'widget_type': 'composite',
            'update_func': 'update_external_battery',  # Complex nested structure
            'dependencies': ['Ch3 Voltage', 'Battery Level', 'Ch3 Current']
        },
        
        'Internal Battery Voltage': {
            'widget_key': 'int_battery_label',
            'widget_type': 'composite',
            'update_func': 'update_internal_battery',
            'dependencies': ['Internal Battery Voltage', 'Battery Level']
        }
    }
```

---

## Data Structures

### Simple Field Example: Temperature

**Registry Entry:**
```python
'Temperature': {
    'widget_key': 'temp_label',
    'widget_type': 'simple',
    'format_func': 'format_temperature',
    'color_func': 'get_temperature_color',
    'use_stale_color': True
}
```

**Format Function:**
```python
def format_temperature(self, temp_c):
    """Format temperature value with unit conversion"""
    temp_value, temp_unit_str, _ = self.convert_temperature(temp_c)
    return f"{temp_value:.0f}{temp_unit_str}"
```

**Color Function:**
```python
def get_temperature_color(self, temp_c):
    """Get color based on temperature thresholds"""
    _, _, (red_threshold, yellow_threshold) = self.convert_temperature(temp_c)
    if temp_c > red_threshold or temp_c < 0:
        return self.colors['fg_bad']
    elif temp_c >= yellow_threshold:
        return self.colors['fg_warning']
    else:
        return self.colors['fg_good']
```

### Composite Field Example: SNR Bars

**Registry Entry:**
```python
'SNR': {
    'widget_key': 'snr_label',
    'widget_type': 'composite',
    'update_func': 'update_snr_bars',
    'children': [
        {'type': 'label', 'text': 'SNR: '},
        {'type': 'bar', 'index': 0},
        {'type': 'bar', 'index': 1},
        {'type': 'bar', 'index': 2},
        {'type': 'bar', 'index': 3}
    ]
}
```

**Update Function:**
```python
def update_snr_bars(self, widget, snr_value):
    """Update SNR bar colors without recreating widget"""
    bar_colors = self.get_signal_bar_colors(snr_value)
    children = widget.winfo_children()
    if len(children) >= 5:  # icon + 4 bars
        for i, color in enumerate(bar_colors):
            children[i + 1].config(fg=color)  # Skip label
```

---

## Implementation Plan

### Phase 1: Create Registry Module ✅ (Next Step)
1. Create `card_field_registry.py`
2. Define `CardFieldRegistry` class
3. Add simple field definitions (Temperature, Humidity, Pressure, etc.)
4. Add format/color helper methods

### Phase 2: Integrate with Dashboard
1. Import registry in `dashboard.py`
2. Initialize registry in `__init__`
3. Update `update_node_card()` to use registry lookup
4. Keep special cases (battery, SNR) as custom handlers initially

### Phase 3: Refactor Update Logic
1. Create generic `_update_simple_field()` method
2. Create generic `_update_composite_field()` method
3. Replace hardcoded updates with registry-driven loop

### Phase 4: Add Composite Handlers
1. Implement `update_snr_bars()` handler
2. Implement battery update handlers
3. Test all field types

### Phase 5: Testing & Validation
1. Verify all fields update correctly
2. Test flash behavior
3. Test stale color logic
4. Performance check (should be faster)

### Phase 6: Documentation
1. Merge key sections into `DESIGN.md`
2. Update `AI_CONTEXT.md` with new architecture
3. Remove WIP markers
4. Add migration notes for future layout changes

---

## Migration Strategy

### Backward Compatibility
- Keep `create_node_card()` unchanged (for now)
- Only refactor `update_node_card()`
- Existing card widgets work with new update system

### Testing Checkpoints
After each phase:
1. Run syntax check: `python -m py_compile dashboard.py`
2. Visual test: Launch dashboard, verify all fields display
3. Update test: Trigger telemetry update, verify flash works
4. Stale test: Wait 16+ min, verify grey color

### Rollback Plan
If issues arise:
- Registry module is separate, can be disabled
- Git revert to before integration
- Old `update_node_card()` logic preserved in comments

---

## Future Enhancements

### Version 2.0: Full Declarative Layout
Move card creation to registry:
```python
CARD_LAYOUT_V2 = {
    'version': '2.0',
    'rows': [
        {'type': 'header', 'widgets': ['name', 'status']},
        {'type': 'metrics', 'widgets': ['ext_battery', 'int_battery']},
        {'type': 'metrics', 'widgets': ['snr', 'ch_util', 'air_util']},
        {'type': 'metrics', 'widgets': ['temperature', 'humidity', 'pressure']}
    ]
}
```

### JSON Configuration
Load layout from config file for runtime customization:
```json
{
  "card_layout": {
    "version": "1.0",
    "field_overrides": {
      "Temperature": {"format": "celsius"}
    }
  }
}
```

---

## NEXT STEPS

**After successful implementation:**
1. ✅ Update `DESIGN.md` with "Card Registry Architecture" section
2. ✅ Update `AI_CONTEXT.md` - remove WIP, add registry details
3. ✅ Add performance notes (registry lookup vs hardcoded)
4. ✅ Document extensibility patterns for adding new fields

**Merge checklist:**
- [ ] All tests pass
- [ ] No visual regressions
- [ ] Performance acceptable
- [ ] Documentation complete
- [ ] Remove "IN DEVELOPMENT" marker from this file
- [ ] Merge to main branch

---

**Design Document Version:** 1.0  
**Last Updated:** 2025-12-13

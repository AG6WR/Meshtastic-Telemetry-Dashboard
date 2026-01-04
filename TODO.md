# TODO List - Meshtastic Telemetry Dashboard

## Current Work

### High Priority

#### Window Layout Improvements
- [ ] **Refine Alerts window** (Issue #e)
  - Current issues:
    - Functionality is confusing - needs better documentation/notes
    - Window size needs adjustment
  - Tasks:
    - Add inline help text or tooltips explaining alert configuration
    - Resize window for better readability
    - Document what each alert type does and when it triggers
    - Consider adding example values or placeholder hints
  - Location: `node_alert_config_qt.py`

---

## Completed Features

### Qt/PySide6 Port (v1.3.0 - Complete)
- [x] All windows and dialogs ported to PySide6
- [x] Touch-friendly UI optimized for Raspberry Pi touchscreens
- [x] Centralized styling system (`qt_styles.py`)
- [x] Button color scheme standardized across all windows

### Messaging System (v1.2.0+ - Complete)
- [x] Direct messaging between nodes
- [x] Message Center with full conversation history
- [x] Unread message indicators and badges
- [x] Message notifications with visual banners
- [x] Archive, delete, mark read/unread functionality

### ICP Status Broadcasting (v2.1.0a - Complete)

### ICP Status Broadcasting (v2.1.0a - Complete)
- [x] Automatic operational status reporting every 15 minutes
- [x] Status calculation based on battery, voltage, and temperature thresholds
- [x] Green/Yellow/Red status indicators on node cards
- [x] Send Help request functionality with blinking indicator
- [x] Status message filtering (excluded from Message Center)
- [x] Complete integration with card renderer and data collector

### Current Sensor Scaling (v2.0.2b+ - Complete)
- [x] Per-node current sensor scaling configuration
- [x] Support for different shunt resistor values
- [x] Hardware settings tab with node selector
- [x] Auto unit conversion (mA/A) with charge/discharge indicators
- [x] CSV logging with raw and scaled values

---

## Future Enhancements

### GPIO LED Control (Pending Firmware)

**Purpose**: Physical status indication via external LEDs connected to Meshtastic node GPIO pins.

**Status**: Waiting for Meshtastic firmware with Remote Hardware module enabled

**Implementation Plan**:
- [ ] **gpio_led_controller.py** - New module
  - `GPIOLEDController` class wrapping Meshtastic Python API
  - `set_status_leds(status)` - Set R/Y/G LEDs based on status
  - `set_buzzer(on)` - Control buzzer for alerts
  - Uses `RemoteHardwareClient.writeGPIOs()` for local node control

- [ ] **Config integration**
  - Add `led_control.enabled` boolean to app_config.json
  - Add `led_control.gpio_pins` mapping

- [ ] **DataCollector integration**
  - Initialize `GPIOLEDController` when connected
  - Call `set_status_leds()` when local ICP status changes

**GPIO Pin Mapping (WisMesh Pocket / RAK4631)**:

| Function | WisBlock IO | nRF GPIO | Arduino Pin |
|----------|-------------|----------|-------------|
| Red LED | IO3 | P0.21 | 21 |
| Yellow LED | IO4 | P0.04 | 4 |
| Green LED | IO6 | P0.10 | 10 |
| Buzzer | IO5 | P0.09 | 9 |

### Current Sense Enhancements
- [ ] **Direction Inversion Option**
  - Add per-node `invert_direction` boolean to current sensor config
  - Use case: Shunt resistor installed in opposite orientation
  - Location: Hardware tab in settings dialog

### Node Provisioner Tool

**Purpose**: Streamlined provisioning of new Meshtastic nodes for ICP network deployment.

**Status**: Core provisioning complete, additional menu options need testing

- [x] **Core provisioning flow** - Flash firmware, apply config, set node name (Windows + Linux)
- [x] **Linux/Raspberry Pi support** - Platform detection, UF2 drive paths, permission checks
- [x] **Verification step** - Confirms settings were applied correctly
- [x] **Unified device-ready waiting** - Probe-based readiness check

**Pending Testing**:
- [ ] Flash firmware only (Option 2)
- [ ] Apply config only (Option 3)
- [ ] Read node info (Option 4)
- [ ] Update inventory file (Option 5)
- [ ] Add admin keys to node (Option 6)
- [ ] Factory reset (Option 7)

**Edge Cases to Test**:
- [ ] Multiple devices connected
- [ ] Device disconnection mid-provisioning
- [ ] Invalid/missing config files
- [ ] Firmware file not found

---

## Design Principles

### Kiosk Mode Guidelines
- **Touch targets**: Minimum 48x48px (Apple/Android HIG standard)
- **Button consistency**: Same size, same color for same function
- **Standard conventions**: Close buttons upper right, positive actions right-aligned
- **Readability**: Use wider fonts where space permits
- **Visual hierarchy**: Larger fonts in spacious windows (detail view)

### Color Scheme (Standardized)
- **Gray #424242**: Close, Cancel, Quit (neutral dismiss)
- **Green #2e7d32**: Send, Compose, Reply, Mark Read, Plot (positive actions)
- **Blue #0d47a1**: View (informational)
- **Orange #f57c00**: Archive (moderate actions)
- **Red #c62828**: Delete, Forget, destructive actions

### Font Standards (Qt Version)
- **Primary UI**: Liberation Sans 11-12pt (readable on touchscreens)
- **Headers**: Liberation Sans 14-16pt Bold
- **Notes/timestamps**: Liberation Sans Narrow 11pt (intentionally compact)
- Pre-installed on Raspberry Pi OS with good Unicode coverage

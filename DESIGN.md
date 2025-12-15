# Meshtastic Telemetry Dashboard - Design Architecture

## Version History
- **v1.0.9** (2025-11-17): Documentation improvements, alert threshold UI enhancement, code comment clarification
- **v1.0.8** (2025-11-16): Offline threshold fix, preloaded packet handling, forget node feature, plotting improvements
- **v1.0.7a** (2025-11-15): Card view flash mechanism, table feature parity
- **v1.0.6** (2025-11-14): Grid layout implementation
- **v1.0.0** (2025-11-02): Initial release

---

## Current Design (as of v1.0.8)

### Timing Thresholds

#### Online/Offline Status
- **Threshold:** 16 minutes (960 seconds)
- **Rationale:** Nodes send telemetry on 15-minute intervals. A 5-minute threshold caused nodes to appear offline between telemetry updates.
- **Implementation:** `dashboard.py` (card create/update), `node_detail_window.py` (detail view)
- **Changed in:** v1.0.8 (2025-11-16)

#### Periodic Refresh
- **Interval:** 5 minutes (300 seconds)
- **Purpose:** Force recalculation of time-based status for all cards
- **Rationale:** Status is time-based (calculated from Last Heard), not data-based. Without periodic refresh, offline transitions wouldn't be detected until new data arrives.
- **Implementation:** `dashboard.py:start_periodic_refresh()` - clears `last_node_data` cache to force all cards to recalculate
- **Changed in:** v1.0.8 (2025-11-16)

#### Telemetry Data Staleness
- **Threshold:** 31 minutes (1860 seconds)
- **Purpose:** Gray out individual sensor values that haven't updated recently
- **Rationale:** Different from node offline status - a node can be online (receiving packets) but have stale environmental sensor data
- **Implementation:** Table view and card view apply gray text + italic font to stale values
- **Visual:** `fg_secondary` color (gray), italic font

#### Motion Display Duration
- **Default:** 15 minutes (900 seconds)
- **Configurable:** `motion_display_seconds` in app_config.json
- **Purpose:** Show "Motion detected X min ago" instead of "Last heard" when motion is recent
- **Rationale:** Motion events are significant and should be highlighted for a configurable duration

### Startup Behavior

#### Data Loading Sequence (v1.0.8)
1. **Load historical data** from `latest_data.json`
   - Restores all node data including `Last Heard` timestamps
   - Preserves online/offline state from previous session
   
2. **Connect to Meshtastic interface** (TCP or Serial)
   - Connection manager establishes link to mesh network
   
3. **Preload node information** from interface database
   - Connection manager sends synthetic NODEINFO packets
   - Packets marked with `_preloaded: True` flag
   - Updates node names (Long Name, Short Name) in cache
   - **Does NOT update Last Heard** (v1.0.8 fix)
   
4. **Display initial cards** with historical data
   - Nodes show correct online/offline status based on loaded Last Heard
   - Names populate from preloaded database

#### Preloaded Packet Handling (v1.0.8)
**Problem (prior to v1.0.8):** Preloaded synthetic NODEINFO packets were calling `_update_node_basic_info()`, which set `Last Heard = time.time()` (current time). This made all nodes appear online immediately after startup, ignoring historical data.

**Solution:** Skip `_update_node_basic_info()` for packets with `_preloaded=True`. Only real mesh packets update Last Heard.

**Code:** `data_collector.py:_on_packet_received()`

### Card View Update Strategy

#### Event-Driven Updates
- Cards update when **data changes** (new packet received)
- Efficient: only changed nodes are redrawn
- Flash effect: blue background for 2 seconds on update

#### Time-Driven Updates (v1.0.8)
- **Problem:** Status is calculated from `current_time - last_heard`, but status change isn't a "data change"
- **Solution:** Periodic refresh every 5 minutes clears `last_node_data` cache
- This forces all cards to recalculate as if data changed
- Catches offline transitions when no new packets arrive

### Flash Mechanism (v1.0.7a)

#### Purpose
Visual feedback when card data updates (new packet received)

#### Implementation
- **Flash color:** `bg_selected` (#1a237e - very dark blue) - same color as selected table row
- **Duration:** 2 seconds (2000ms) - set via `self.after(2000, restore_function)`
- **Applies to:** Both event-driven single card updates and periodic all-card refreshes
- **Widgets flashed:** All frames, labels, and container children
- **Container children:** Special handling for battery, current, temperature, SNR, util, humidity containers that have child labels

#### Known Issue (v1.0.7a)
Adding debug logging statements (even `logger.info()`) to card creation/update functions breaks the flash mechanism for unknown reasons. Flash color gets "stuck" on some widgets. Workaround: Avoid logging in flash-related code paths.

### Battery Display

#### Dual Battery Support
- **Internal battery:** Standard Meshtastic battery telemetry
- **External battery:** Ch3 Voltage (LiFePO4 chemistry)
- **Display:** Shows external battery if present, otherwise internal
- **Calculation:** `get_battery_percentage_display()` uses 19-point LiFePO4 voltage curve

#### Color Coding
- **Red:** 0-25%
- **Yellow:** 25-50%
- **Green:** >50%

### Motion Detection

#### Display Logic
- **Recent motion:** Show "Motion detected X min ago" if within threshold (default 15 min)
- **No recent motion:** Show "Last heard X min ago"
- **Transition:** Log when switching between motion and last-heard display

#### Data Source
- **Motion packets:** `DETECTION_SENSOR_APP` portnum
- **Storage:** `last_motion_by_node` dict in data_collector
- **Persistence:** Not persisted to JSON, rebuilt from packet stream

### Forget Node Feature (v1.0.8)

#### Purpose
Remove nodes from the dashboard that are no longer relevant (renamed, decommissioned, or incorrectly added).

#### Access Points
- **Card Context Menu:** Right-click on any card → "Forget Node '[name]'" (red text)
- **Detail Window:** "Forget Node" button (red background) in node detail window

#### Cleanup Operations
When a node is forgotten, the system performs comprehensive cleanup:
1. **Remove from nodes_data** - Main node data dictionary
2. **Remove from node_info_cache** - Cached long/short names
3. **Remove from last_motion_by_node** - Motion detection cache
4. **Clear alerts** - Remove all active alerts for the node
5. **Optional: Delete CSV logs** - User chooses whether to delete historical log files

#### User Flow
1. User selects "Forget Node" via context menu or detail window
2. Warning dialog explains what will be removed
3. User confirms or cancels
4. If confirmed, secondary dialog asks about CSV log deletion
5. System performs cleanup and saves `latest_data.json`
6. Dashboard refreshes to remove the card
7. Detail window closes (if open)

#### Implementation
- **Method:** `data_collector.forget_node(node_id, delete_logs=False)`
- **UI Handlers:** `dashboard._forget_node_from_card()`, `node_detail_window._forget_node()`
- **Thread Safety:** Uses `data_lock` to ensure safe removal

---

## Design Evolution

### v1.0.8 (2025-11-16): Status Calculation Fixes

#### Offline Threshold Change
**Changed:** 5 minutes → 16 minutes (960 seconds)

**Rationale:** 
- Nodes send telemetry every 15 minutes
- 5-minute threshold caused false "Offline" status between telemetry updates
- 16 minutes accommodates normal 15-minute intervals with 1-minute buffer

**Impact:**
- Nodes stay "Online" between telemetry packets
- True offline detection happens after 16 minutes of silence
- Alert system threshold may need adjustment (currently 10 minutes)

#### Preloaded Packet Fix
**Problem:** At startup, preloaded NODEINFO packets overwrote historical `Last Heard` with current time

**Root Cause:**
- `_load_existing_data()` loaded Last Heard from JSON
- `_preload_nodes()` sent synthetic NODEINFO packets (no rxTime)
- `_on_packet_received()` defaulted missing rxTime to `time.time()`
- `_update_node_basic_info()` set `Last Heard = rx_time`
- Result: All nodes appeared online at startup

**Solution:**
- Check `packet.get('_preloaded', False)` flag
- Skip `_update_node_basic_info()` for preloaded packets
- Historical Last Heard preserved from JSON
- Node names still update via `_process_nodeinfo_packet()`

#### Periodic Refresh Implementation
**Problem:** Card view was event-driven only. Status changes from time passing (offline transitions) weren't detected.

**Solution:**
- `start_periodic_refresh()` runs every 5 minutes
- Clears `last_node_data` cache before calling `refresh_display()`
- Forces all cards to be seen as "changed"
- Recalculates status with fresh `current_time`

**Tradeoff:** All cards flash blue every 5 minutes during refresh. Could be optimized to only flash cards with status changes.

#### Forget Node Feature
**Need:** Users needed a way to remove stale, renamed, or decommissioned nodes from the dashboard.

**Implementation:**
- Right-click context menu on cards
- "Forget Node" button in detail window (red styling for caution)
- Comprehensive cleanup: nodes_data, caches, alerts, optional CSV deletion
- Two-step confirmation prevents accidental deletion
- Thread-safe removal with immediate JSON save

**User Experience:**
- Discoverable via right-click (common UI pattern)
- Also accessible from detail window
- Clear warnings explain what will be deleted
- Separate choice for CSV log deletion (preserves historical data by default)

#### Plotting Improvements
**Channel Utilization:**
- Fixed y-axis scale from auto (0-1%) to fixed (0-50%)
- Rationale: Most values ~1%, auto-scale made graphs useless
- 50% is critical threshold per Meshtastic documentation

**Voltage Parameters:**
- Split "Voltage" into "Internal Battery Voltage" and "External Battery Voltage"
- Internal: 3.0-4.5V scale (LiPo/Li-ion cells)
- External: 10-15V scale (LiFePO4 12V systems)
- Explicit selection instead of automatic fallback
- Fixes empty plots for battery-powered nodes (no Ch3 voltage)

### v1.0.7a (2025-11-15): UI Polish

#### Card Typography
- Standardized fonts: 10pt labels (gray), 14pt values (bold, colored)
- Baseline alignment fixes for SNR bars and text
- Even vertical spacing: Line 2=18px, Line 3=25px (14pt font), Line 4=18px

#### Table View Feature Parity
- Added Motion column between Last Heard and SNR
- External battery support in table (`get_battery_percentage_display()`)
- Color coding for all metrics (SNR, Temp, Humidity, Voltage, Current, Battery%, Utilization%)

#### Flash Mechanism
- Blue flash on all widgets including container children
- 2-second duration with proper restore
- Fixed: container child labels now flash/restore correctly

---

## Configuration

### App Config (app_config.json)

```json
{
  "dashboard": {
    "motion_display_seconds": 900,  // 15 minutes - how long to show "Motion detected"
    "stale_row_seconds": 300,       // 5 minutes - unused (vestigial)
    "time_format": "DDd:HHh:MMm:SSs"  // Duration display format
  }
}
```

### Visual Feedback

**Color Coding:**
- **Status colors:** Green (online/good), orange (warning), coral pink (offline/bad)
- **Flash effect:** Blue background indicates card data updates
- **Stale data:** Gray text with italic font for outdated sensor values

**Implementation:** Color palette defined in `dashboard.py:__init__()` with inline comments documenting each color's purpose and usage.

---

## File Structure

### Core Files
- `dashboard.py` - Main application, card/table views, UI logic
- `data_collector.py` - Packet processing, node data management
- `connection_manager.py` - Meshtastic interface connection (TCP/Serial)
- `node_detail_window.py` - Detail popup window for individual nodes
- `alert_system.py` - Alert triggers and notifications
- `plotter.py` - Telemetry graphing from CSV logs
- `config_manager.py` - Configuration file handling

### Data Files
- `latest_data.json` - Persistent node data (Last Heard, telemetry values)
- `logs/meshtastic_monitor.log` - Application log
- `logs/<node_id>/` - Per-node CSV telemetry logs

---

## Known Issues

### Flash Mechanism Fragility (v1.0.7a)
Adding logging statements to card creation/update code breaks flash colors. Widgets get stuck with blue backgrounds. Root cause unknown. Workaround: Avoid debug logging in flash-related code.

### Alert vs Status Threshold Design (v1.0.8)
The alert threshold and offline status threshold can be set independently:
- **Offline status threshold:** 16 minutes (hardcoded) - when cards show "Offline"
- **Alert threshold:** Configurable (default 16 minutes) - when alerts fire

**Rationale:** Allows alerts to fire before status changes (early warning) or at the same time (aligned thresholds). Settings pane displays the offline status threshold for reference when configuring alert threshold.

---

## Virtual Keyboard System (v1.2.2b)

### Why a Custom Virtual Keyboard?

**Problem:** Raspberry Pi running Wayland compositor cannot use standard on-screen keyboards like `onboard` or `squeekboard` that work under X11. The Wayland security model prevents third-party input applications from injecting keystrokes into focused windows.

**Alternatives Considered:**
- `onboard` - X11 only, doesn't work on Wayland
- `squeekboard` - Designed for GNOME/Phosh, integration issues on Pi
- `wvkbd` - Wayland-native but requires compositor configuration
- PiOS built-in keyboard - Not available on all Pi configurations

**Solution:** Custom Tkinter-based virtual keyboard (`virtual_keyboard.py`) that:
1. Runs as a Toplevel window within the same Tk application
2. Directly inserts characters into the target Text widget via `widget.insert()`
3. Bypasses Wayland's input method restrictions entirely
4. Provides consistent behavior across X11 and Wayland

### Implementation Architecture

**Window Positioning:**
- Uses `overrideredirect(True)` to bypass window manager positioning
- Fixed position at bottom of screen (keyboard) or top of screen (compose dialog)
- Wayland window managers ignore geometry hints; overrideredirect forces exact placement

**Focus Management:**
- `bind_all('<FocusIn>')` detects when Text/Entry widgets receive focus
- Automatically shows keyboard when text input is focused
- `bind_all('<Button-1>')` on regular buttons hides keyboard
- Critical: Check if event widget is inside keyboard window to avoid hiding on key press

**Layout:**
- Two frames: lowercase and uppercase, toggled via Caps key
- No symbols layout (removed for simplicity - use phone for complex input)
- 5-color coding: dark letters, blue/indigo modifiers, green Caps, coral delete, gray space
- Touch-friendly key sizes: 48px tall, variable width

**Key Press Handling:**
```python
def _on_key_press(self, char, button=None):
    if char == 'Caps':
        self._caps_enabled = not self._caps_enabled
        (self.uppercase_frame if self._caps_enabled else self.lowercase_frame).tkraise()
    elif char == '⌫':  # Backspace
        self.target_widget.delete('insert-1c', 'insert')
    elif char == '↵':  # Enter
        self.target_widget.insert('insert', '\n')
    else:
        self.target_widget.insert('insert', char)
```

### Known Issues and Solutions

**Issue:** Whole keyboard window flashes on key press (not individual keys)
- **Cause:** Tkinter redraws can cascade when modifying Text widget content
- **Status:** Cosmetic issue, does not affect functionality
- **Workaround:** Disabled individual key flash animation

**Issue:** Cursor not visible in text areas
- **Solution:** Use high-contrast cursor color (white, not red), solid cursor (`insertofftime=0`)
- **Config:** `insertbackground='white', insertwidth=2, insertontime=1000, insertofftime=0`

---

## Global Font System (v1.2.2b)

### Why Global Font References?

**Problem:** Hardcoded font specifications scattered across 8+ files made font changes labor-intensive and error-prone. Changing the button font required editing every file individually.

**Discovery:** Testing on Raspberry Pi 7" touchscreen revealed Liberation Sans Narrow was too compressed for comfortable reading. Needed to switch to Liberation Sans (regular width).

### Font Architecture

**Central Definition (dashboard.py __init__):**
```python
self.font_ui_body = tkfont.Font(family="Liberation Sans", size=12)
self.font_ui_notes = tkfont.Font(family="Liberation Sans Narrow", size=11)  # Intentionally narrow
self.font_ui_tab = tkfont.Font(family="Liberation Sans", size=12)
self.font_ui_button = tkfont.Font(family="Liberation Sans", size=12)
self.font_ui_section_title = tkfont.Font(family="Liberation Sans", size=12, weight="bold")
self.font_ui_window_title = tkfont.Font(family="Liberation Sans", size=14, weight="bold")
```

**Child Window Pattern:**
```python
# In child window __init__:
self.font_ui_button = getattr(parent, 'font_ui_button', None)

# In widget creation:
font=self.font_ui_button if self.font_ui_button else ("Liberation Sans", 12)
```

**Rationale for Fallback Tuples:**
- TTK styles require tuples, not Font objects
- Some windows may be created without dashboard parent
- Fallback ensures graceful degradation

### Font Choices

| Font Variable | Family | Size | Weight | Purpose |
|--------------|--------|------|--------|---------|
| font_ui_body | Liberation Sans | 12 | normal | General text, labels |
| font_ui_notes | Liberation Sans Narrow | 11 | normal | Timestamps, secondary info |
| font_ui_tab | Liberation Sans | 12 | normal | Tab labels |
| font_ui_button | Liberation Sans | 12 | normal | Button text |
| font_ui_section_title | Liberation Sans | 12 | bold | Section headers |
| font_ui_window_title | Liberation Sans | 14 | bold | Window/dialog titles |

**Why Liberation Sans?**
- Pre-installed on Raspberry Pi OS
- Good Unicode coverage (including technical symbols)
- Clear letterforms at small sizes
- Regular width readable on 7" touchscreen (Narrow was too compressed)

**Why Keep Narrow for Notes?**
- Timestamps and secondary info benefit from compact display
- Less visual prominence than primary content
- 11pt Narrow still readable for non-critical info

---

## Future Considerations

### Configurable Thresholds
Move hardcoded thresholds to app_config.json:
- `offline_threshold_seconds`: 960
- `periodic_refresh_seconds`: 300
- `telemetry_stale_seconds`: 1860

### Optimized Periodic Refresh
Only flash cards that changed status, not all cards. Track previous status and compare.

### Motion Data Persistence
Consider saving `last_motion_by_node` to JSON to preserve motion display across restarts.

### Alert System Integration
Align alert thresholds with offline detection, or keep separate with clear rationale (early warning vs actual offline).

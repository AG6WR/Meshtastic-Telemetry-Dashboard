# Meshtastic Telemetry Dashboard - Design Architecture

## Version History
- **v1.0.8** (2025-11-16): Offline threshold fix, preloaded packet handling
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
- **Flash color:** `bg_selected` (blue background) - same color as selected table row
- **Duration:** 2 seconds
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

### Color Scheme

Defined in `dashboard.py:__init__()`:

- `bg_dark`: `#1e1e1e` - Main background
- `bg_frame`: `#2d2d2d` - Card/frame background (normal)
- `bg_selected`: `#0d3a5f` - Selected/flash background (blue)
- `fg_normal`: `#e0e0e0` - Normal text (white)
- `fg_secondary`: `#808080` - Secondary text (gray) - labels, stale data
- `fg_good`: `#90EE90` - Good status (light green) - Online, high battery
- `fg_warning`: `#FFD700` - Warning status (gold) - Medium battery
- `fg_bad`: `#DC143C` - Bad status (crimson) - Offline, low battery, errors

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

### Alert Threshold Mismatch (v1.0.8)
Alert system triggers after 10 minutes offline, but offline threshold is now 16 minutes. This means nodes can be "Online" when alerts trigger. Should align alert threshold with offline threshold or keep separate for early warning.

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

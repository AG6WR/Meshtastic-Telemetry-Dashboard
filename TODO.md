# TODO List - Meshtastic Telemetry Dashboard

## Current Sprint: Kiosk UI/UX Polish (2025-12-15)

### High Priority - Touch-Friendly UI

#### Icon & Font Issues
- [x] **Fix location pin emoji on Pi** (Issue #a - REMOVED)
  - Solution: Removed pin emoji entirely - green background already indicates local node
  - No longer renders empty box on Pi

- [x] **Research available glyphs in Liberation font family** - DONE
  - Removed emoji icons from UI, using text labels instead
  - Qt version avoids emoji rendering issues

#### Window Layout Improvements
- [x] **Node Detail window improvements** (Issue #d - DONE)
  - Button layout: Row 1: Logs, CSV, Close | Row 2: Plot, Forget Node
  - Buttons now fit properly with smaller width (8 chars vs 10)
  - Plot button now green (#2e7d32) to match positive action scheme
  - Text styling enlarged throughout:
    - Node name: 16pt bold (was 12pt)
    - Section titles: 13pt bold (was 11pt)
    - Body text/labels: 12pt (was 11pt)
    - Subsection headers: 12pt italic (was 11pt)

- [ ] **Refine Alerts window** (Issue #e)
  - Current issues:
    - Functionality is confusing - needs better documentation/notes
    - Window size needs adjustment
  - Tasks:
    - Add inline help text or tooltips explaining alert configuration
    - Resize window for better readability
    - Document what each alert type does and when it triggers
    - Consider adding example values or placeholder hints
  - Location: `node_alert_config.py`

- [x] **Scrub button colors for consistency** (Issue #c - DONE)
  - Standardized color scheme across all windows:
    - Gray #424242: Close, Cancel, Quit (neutral dismiss)
    - Green #2e7d32: Send, Compose, Reply, Mark Read, Plot (positive)
    - Blue #0d47a1: View (informational)
    - Orange #f57c00: Archive (moderate)
    - Red #c62828: Delete, Forget, small ✕ icons (destructive)

### Code Quality & Technical Debt

#### Qt Port (Complete)
- [x] `settings_dialog_qt.py` - Settings dialog ported to PySide6
- [x] `message_dialog_qt.py` - Message compose dialog ported to PySide6
- [x] `node_detail_window_qt.py` - Node detail window
- [x] `message_list_window_qt.py` - Message list window
- [x] `dashboard_qt.py` - Main dashboard window
- [x] `card_renderer_qt.py` - Card widget (new, cleaner architecture)
- [x] `plotter_qt.py` - Plot configuration and display
- [x] `node_alert_config_qt.py` - Per-node alert configuration
- [x] `qt_styles.py` - Centralized styling module
- [x] `run_monitor_qt.py` - Entry point

**Note:** Table view mode not ported (Cards view is preferred for touch/kiosk use)

#### Qt Virtual Keyboard
- [x] **Test Qt native virtual keyboard on Pi** - DONE
  - Qt handles virtual keyboard natively
  - May need `qt6-virtualkeyboard` package and `QT_IM_MODULE=qtvirtualkeyboard` on Pi if needed

#### Existing TODOs in Codebase
- [x] Implement external battery voltage-to-percentage mapping (LiFePO4 12V curve in data_collector.py)
- [x] Refactor card field registry system - N/A in Qt (Tkinter-only, not to be changed)

### Future Enhancements
- [x] Test fullscreen exit window state on Pi - DONE (Quit button works)
- [x] Verify message list click-to-open on Pi - DONE (View button works)

### ICP Status Broadcast System (v2.1.0a - In Progress)

**Purpose**: Give EOC management a view of operational state of each ICP with minimal staff interaction. Each ICP/EOC dashboard broadcasts its own determined status; other dashboards display what each node reports about itself.

#### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Status determination | Local ICP calculates own status | Prevents inconsistent status shown by different dashboards |
| Manual data (frequencies, etc.) | Excluded | Stale data worse than no data; staff won't maintain |
| Motion sensor | Informational only, not used for status | Staffed/unstaffed is contextual, not good/bad |
| Send Help flag | Only manual input included | Event-driven, high-value, self-clearing |

#### Status Calculation

Uses existing color thresholds from `node_detail_window_qt.py`:

| Parameter | Green | Yellow | Red |
|-----------|-------|--------|-----|
| Battery % | >50% | 25-50% | <25% |
| Voltage | ≥4.0V | 3.5-4.0V | <3.5V |
| Temperature | 0-35°C | 35-45°C or <0°C | >45°C |

**Aggregation**: Overall status = worst component status ("weakest link")

#### Message Format

New structured message type (same channel as regular messages, filtered by receiver):

```
Prefix: [ICP-STATUS]
Format: [ICP-STATUS]<status>|<reasons>|<help>|<version>|<timestamp>

Examples:
[ICP-STATUS]GREEN||NO|1.3.0|1735689600
[ICP-STATUS]YELLOW|Battery|NO|1.3.0|1735689600
[ICP-STATUS]RED|Battery,Temperature|NO|1.3.0|1735689600
[ICP-STATUS]RED||YES|1.3.0|1735689600  (help requested)
```

**Fields**:
- `status`: GREEN | YELLOW | RED
- `reasons`: Comma-separated (empty if GREEN): Battery, Voltage, Temperature
- `help`: YES | NO
- `version`: Dashboard version string
- `timestamp`: Unix epoch

**Message routing**: `[ICP-STATUS]` messages parsed and processed, NOT shown in Message Center.

#### Broadcast Timing

- **Heartbeat**: Every 15 minutes
- **On change**: Immediately when status changes

#### Card Display - Status Indicator

Replaces "Online/Offline" with button-style indicator:

| Condition | Background | Text | Animation |
|-----------|------------|------|-----------|
| Status GREEN | Green | "Online" | None |
| Status YELLOW | Yellow | Reason: "Battery" | None |
| Status RED | Red | Reason: "Temp" | None |
| Help Requested | Red | "Send Help" | Blink 1Hz |
| Node offline | Last status color | "Offline" | None |
| Offline + was Help | Red | "Offline" | Blink continues |

**Multiple reasons**: Show comma-separated: "Battery, Temp"

#### Send Help Button

**UI Flow**:
1. User clicks "Send Help" button
2. Confirmation dialog: "Request assistance from other ICPs/EOC?"
3. If confirmed: Set flag, broadcast immediately, button blinks
4. Local-only "Clear Help" button appears
5. Clear requires confirmation: "Clear help request?"

**Auto-clear**: After 1 hour with no action

**Remote dashboards**: Cannot clear another ICP's help flag

#### Implementation Components

- [x] **Status calculator** - Evaluate local telemetry → status + reasons
- [x] **Status broadcaster** - Send `[ICP-STATUS]` on interval/change (15-min heartbeat + on-change)
- [x] **Status receiver** - Parse incoming `[ICP-STATUS]`, update node data
- [x] **Card renderer update** - StatusIndicator widget with blink animation
- [x] **Help button UI** - "Send Help" / "Clear Help" button + confirmation dialogs
- [x] **Message filter** - Route `[ICP-STATUS]` away from Message Center

**Completed**: v2.1.0a (merged to main 2026-01-01)

#### GPIO LED Control (Pending Firmware)

**Purpose**: Physical status indication via external LEDs connected to Meshtastic node GPIO pins. Each dashboard controls LEDs on its locally-connected node.

**Hardware Requirements**:
- Meshtastic firmware compiled with Remote Hardware module enabled (remove `-DMESHTASTIC_EXCLUDE_REMOTEHARDWARE=1` build flag)
- LEDs connected via relay board to GPIO pins

**GPIO Pin Mapping (WisMesh Pocket / RAK4631)**:

| Function | WisBlock IO | nRF GPIO | Arduino Pin | Mask |
|----------|-------------|----------|-------------|------|
| Red LED | IO3 | P0.21 | 21 | 0x200000 |
| Yellow LED | IO4 | P0.04 | 4 | 0x10 |
| Green LED | IO6 | P0.10 | 10 | 0x400 |
| Buzzer | IO5 | P0.09 | 9 | 0x200 |

**Note**: IO7 (P0.28, Arduino 28) reserved for motion detector input.

**Implementation Plan**:

- [ ] **gpio_led_controller.py** - New module
  - `GPIOLEDController` class wrapping Meshtastic Python API
  - `set_status_leds(status)` - Set R/Y/G LEDs based on status
  - `set_buzzer(on)` - Control buzzer for alerts
  - `read_led_status()` - Read current GPIO state
  - Uses `RemoteHardwareClient.writeGPIOs()` for local node control
  - No `gpio` channel needed for local-only control

- [ ] **Config integration**
  - Add `led_control.enabled` boolean to app_config.json
  - Add `led_control.gpio_pins` mapping (hardcoded defaults, configurable later)
  - Hardware tab note showing current pin mapping

- [ ] **DataCollector integration**
  - Initialize `GPIOLEDController` when connected
  - Call `set_status_leds()` when local ICP status changes
  - Sync LED state with calculated status in `_send_icp_broadcast()`

- [ ] **Status-to-LED logic**
  - GREEN status: Green LED on, others off
  - YELLOW status: Yellow LED on, others off
  - RED status: Red LED on, others off
  - HELP requested: Red LED blink (or buzzer pulse)

**Testing**: Requires firmware recompilation - cannot test until hardware ready

---

### Hardware Integration Features
- [x] **Current Sense Scaling** (v2.0.2b - DONE)
  - Location: Ch3 Current telemetry display (ICP Main Batt current)
  - Implementation: Per-node configuration with default fallback
  - Settings dialog: Hardware tab with node selector dropdown
  - Config structure: `hardware.current_sensor.default` + `hardware.current_sensor.nodes.{node_id}`
  - Affects: Card display, node detail window, CSV logging (raw + scaled columns)
  - Auto units: Values <1000mA show as "XXXmA", ≥1000mA show as "X.XXA"
  - Direction arrows: ⬆ charging, ⬇ discharging

- [ ] **Current Sense Direction Inversion** (Enhancement)
  - Add option to invert current sense direction for each measurement
  - Use case: Shunt installed in opposite orientation
  - Location: Hardware tab in settings, per-node configuration
  - Implementation: Add `invert_direction` boolean to current sensor config

---

## Completed (Previous Sprint)
- [x] Direct messaging system implementation
- [x] Message display on node cards
- [x] Context menu dismissal fixes
- [x] MessageViewer white window fix (grab_set timing)
- [x] Tkinter cleanup errors fixed
- [x] Window sizing for Pi (1200x660)
- [x] Quit button added
- [x] CHANGELOG.md updated for v1.2.0/v1.2.0b

## Completed (v1.2.2b - 2025-12-14)
- [x] Virtual keyboard improvements for Wayland/Pi touchscreen
- [x] Font standardization - Liberation Sans 12pt for buttons/tabs (was Narrow)
- [x] Global font references instead of hardcoded fonts across codebase
- [x] Dashboard button cleanup (renamed Alerts, Logs; removed Debug Log, Today's CSV)
- [x] Message Center button cleanup (removed emoji icons)
- [x] overrideredirect for message windows (precise positioning on Wayland)
- [x] Documentation updates (DESIGN.md, AI_CONTEXT.md)
- [x] Context menu font sizes enlarged for touch
- [x] Message recipient selection with checkboxes
- [x] Button sizes and fonts unified across windows
- [x] Close button added to Message List window
- [x] Font family consolidation (Liberation Sans for UI)

---

## Notes

### Font Investigation - Current State
**Current Font Usage (CORRECTED):**

**Dashboard/Cards (dashboard.py):**
- Windows: `Consolas` (monospace/narrow)
- Pi/Linux: `Courier New` (monospace/narrow)
- Used for: All card text, headers, labels, values
- Location: `dashboard.py` line 752

**Message Windows & Dialogs:**
- `Segoe UI` (standard sans-serif) - ALL platforms
- Used in: node_detail_window.py, message_dialog.py, message_viewer.py, message_list_window.py
- Font sizes: 9pt-14pt depending on element
- This is ALREADY readable!

**The Real Problem:**
- Cards use monospace (Consolas/Courier) which is narrow and hard to read
- Message windows already use proper sans-serif (Segoe UI) ✅
- **We only need to fix the card/dashboard fonts**

**Available on Pi (Liberation family):**
- Liberation Sans (≈ Arial, standard sans-serif)
- Liberation Sans Narrow (condensed variant)
- Liberation Mono (≈ Courier, monospace)
- Each has: Regular, Bold, Italic, Bold Italic

**Proposed Change:**
- Dashboard cards: Switch from Courier New to **Liberation Sans**
- Buttons: Can use Liberation Sans Narrow if space is tight
- Message windows: Keep Segoe UI (already good, will fall back to Liberation Sans on Pi)
- Emojis: Test with Noto Color Emoji font if available

### Design Principles for Kiosk Mode
- Minimum touch target: 48x48px (Apple/Android HIG standard)
- Button consistency: Same size, same color for same function
- Standard conventions: Close buttons upper right
- Readability: Use wider fonts where space permits
- Visual hierarchy: Larger fonts in spacious windows (detail view)

# TODO List - Meshtastic Telemetry Dashboard

## Current Sprint: Kiosk UI/UX Polish (2025-12-15)

### High Priority - Touch-Friendly UI

#### Icon & Font Issues
- [x] **Fix location pin emoji on Pi** (Issue #a - REMOVED)
  - Solution: Removed pin emoji entirely - green background already indicates local node
  - No longer renders empty box on Pi

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

#### Existing TODOs in Codebase
- [ ] Implement external battery update (dashboard.py:2808)
- [ ] Refactor card field registry system (dashboard.py:3064) - See CARD_REGISTRY_DESIGN.md
- [ ] Add replied indicator to messages (message_list_window.py:319)

### Future Enhancements
- [ ] Test fullscreen exit window state on Pi (ongoing issue - has workaround with Quit button)
- [ ] Verify message list click-to-open on Pi (View button works as alternative)

### Hardware Integration Features
- [ ] **Current Sense Scaling** (New Feature)
  - Location: Ch3 Current telemetry display (ICP Main Batt current)
  - Use case: Modified current sense resistor for higher current measurement
  - Problem: INA sensor reports voltage, firmware assumes standard R to calculate I
  - If sense resistor reduced by 50x or 100x, reported current needs scaling
  - Implementation options:
    - Per-node configuration in app_config.json (scale factor)
    - Or global setting if all nodes use same modified hardware
  - Affects: Card display, node detail window, plotter, CSV logging
  - Consider: Store raw value + scaled value? Or just apply scaling at display?

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

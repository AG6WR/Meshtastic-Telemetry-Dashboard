# TODO List - Meshtastic Telemetry Dashboard

## Current Sprint: Kiosk UI/UX Polish (2025-12-15)

### High Priority - Touch-Friendly UI

#### Icon & Font Issues
- [ ] **Fix location pin emoji on Pi** (Issue #a)
  - Location: Node cards, local node indicator (📍)
  - Current: Renders as empty box on Raspberry Pi
  - Investigation needed: Test alternative emoji fonts or use ASCII alternative
  - Font options on Pi: Check `fc-list` for available emoji/symbol fonts
  - Consider: Switch to text "(LOCAL)" or test different pin emoji (📌)

#### Window Layout Improvements
- [ ] **Move Close button to upper right in Node Detail window** (Issue #d)
  - Current: Lower left
  - Change to: Upper right (standard convention)
  - Also move: "Forget Node" button to upper right, aligned with Close
  - Increase font sizes: Detail view has plenty of room, increase by 2 sizes

- [ ] **Scrub button colors for consistency** (Issue #c - partial)
  - Close buttons: Should match "Quit" button color (red/fg_bad)
  - Quick pass needed to ensure all close buttons are same color

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

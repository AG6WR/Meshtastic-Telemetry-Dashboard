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
  
- [ ] **Investigate font system and emoji support** (Issue #a)
  - Document current font family in use (appears to be Liberation Sans on Pi)
  - List available font variants (Regular, Bold, Condensed, etc.)
  - Test emoji rendering capabilities
  - Establish guidelines for mixing fonts/glyphs in UI

#### Touch Target Improvements
- [ ] **Enlarge context menu font sizes** (Issue #b)
  - Location: Card right-click menu (View Details, Show Logs, etc.)
  - Current: Too small for confident finger/touch selection at 1280x720
  - Action: Increase menu item font size and padding
  - Test: Verify minimum 48x48px touch targets

- [ ] **Standardize message recipient selection** (Issue #g)
  - Location: MessageDialog recipient picker
  - Current: Small text list, unclear multi-select, hard to tap
  - Proposal: Use card-based layout with checkboxes (similar to message list)
  - Design: Narrower cards showing just node name + checkbox
  - Benefit: Consistent with message inbox UX, larger touch targets

#### Button Standardization
- [ ] **Unify button sizes across all windows** (Issue #c)
  - Audit all buttons: dashboard, detail view, message windows
  - Target size: Match dashboard main buttons (current width is good)
  - Height: Slightly reduce from current (a little bigger than needed)
  - Apply consistently to: detail view, message viewer, message list, compose dialog
  
- [ ] **Standardize button colors** (Issue #c)
  - Close buttons: Match "Quit" button color (red/fg_bad)
  - Action buttons: Maintain current color scheme
  - Apply to: all close buttons across detail view, message windows

#### Window Layout Improvements
- [ ] **Move Close button to upper right in Node Detail window** (Issue #d)
  - Current: Lower left
  - Change to: Upper right (standard convention)
  - Also move: "Forget Node" button to upper right, aligned with Close
  - Increase font sizes: Detail view has plenty of room, increase by 2 sizes

- [ ] **Add Close button to Message List window** (Issue #f)
  - Location: Upper right corner
  - Current: Requires using tiny window X button
  - Style: Match standardized button appearance

#### Font Family Consolidation
- [ ] **Switch to standard sans-serif for readability** (Issue #e)
  - Current: Using narrow/condensed font family
  - Keep narrow font: For buttons only (saves space)
  - Change to wider sans-serif: All other UI text (labels, values, window content)
  - Research: Check Liberation Sans family on Pi for available weights
  - Rationale: Better readability in non-space-constrained areas

### Code Quality & Technical Debt

#### Existing TODOs in Codebase
- [ ] Implement external battery update (dashboard.py:2808)
- [ ] Refactor card field registry system (dashboard.py:3064) - See CARD_REGISTRY_DESIGN.md
- [ ] Add replied indicator to messages (message_list_window.py:319)

### Future Enhancements
- [ ] Test fullscreen exit window state on Pi (ongoing issue - has workaround with Quit button)
- [ ] Verify message list click-to-open on Pi (View button works as alternative)

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

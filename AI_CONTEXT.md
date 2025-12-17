# AI ChatBot Persistence - Active Design Work

## ⚠️ CRITICAL RULES FOR AI ASSISTANT

**ALWAYS ASK BEFORE MAKING CHANGES** - The user has repeatedly emphasized this:
- **DO NOT** make assumptions about what the user wants changed
- **DO NOT** "fix" things that aren't broken or weren't requested
- **ASK FIRST** before reverting, modifying, or "improving" existing code
- **Example**: User asked to make local node card standard size, NOT to change card width from 460px back to 280px
- **When in doubt**: Describe what you plan to change and ask for confirmation

This applies especially to:
- Size/dimension changes (card width, heights, spacing)
- Color scheme modifications
- Layout restructuring
- "Improvements" or "optimizations" not explicitly requested

**Remember:** The user knows their requirements better than the AI does. Always confirm before acting.

**ASK FOR VISUAL FEEDBACK** - The AI cannot see the UI:
- When user launches a dialog/window, **ASK what they see** before assuming success
- Don't assume "no crash" means "looks correct" - layout issues are common
- Ask about: sizing, alignment, readability, missing elements, visual glitches
- **Example**: After user tests `settings_dialog_qt.py`, ask "How does it look? Are all tabs visible? Any layout issues?"
- The user is the only source of truth for visual correctness

**LAUNCH GUI TESTS IN BACKGROUND** - Don't block the conversation:
- Always use `isBackground=true` when launching GUI applications for testing
- This allows continued conversation while user tests the UI
- User will close the window when done testing and report feedback
- Never use blocking (foreground) launches for GUI test windows

---

## Current Session Context
**Date Started:** 2025-11-17
**Current Version:** v1.2.2b
**Active Branch:** main (feature/messaging merged)
**Last Updated:** 2025-12-14

---

## 📝 CRITICAL LESSONS LEARNED (2025-12-14)

### Virtual Keyboard Implementation

**Context:** Dashboard runs on Raspberry Pi with 10" touchscreen (1280x720) running Wayland. Standard on-screen keyboards (onboard, squeekboard) don't work on Wayland.

**Solution:** Custom Tkinter virtual keyboard (`virtual_keyboard.py`) that inserts characters directly into Text widgets.

**Key Technical Decisions:**

1. **overrideredirect(True) for all message windows**
   - Wayland window managers ignore geometry hints
   - Only way to get exact window positioning is to bypass WM entirely
   - Compose dialog at top of screen (y=10) leaves room for keyboard below
   - Keyboard fixed at bottom of screen

2. **Focus management with bind_all**
   - `bind_all('<FocusIn>')` to auto-show keyboard when Text/Entry focused
   - `bind_all('<Button-1>')` to hide keyboard when clicking buttons
   - **CRITICAL:** Must check if event widget is inside keyboard window before hiding
   - Walk up parent chain: `parent = w.master` until reaching keyboard window or None

3. **Direct character insertion**
   - `target_widget.insert('insert', char)` - bypasses Wayland input restrictions
   - Backspace: `target_widget.delete('insert-1c', 'insert')`
   - No event_generate needed (avoids focus issues)

4. **Two-layout system (lowercase/uppercase)**
   - Simpler than three-layout (no symbols)
   - Use tkraise() to switch between frames
   - **BUG FIX:** Don't use conditional tkraise - always raise the target frame

### Global Font System

**Context:** User tested on Pi and found Liberation Sans Narrow "really narrow" - too compressed for touchscreen use.

**Solution:** Global font variables in dashboard.py, referenced by child windows via getattr().

**Pattern:**
```python
# In dashboard.py __init__:
self.font_ui_button = tkfont.Font(family="Liberation Sans", size=12)

# In child window __init__:
self.font_ui_button = getattr(parent, 'font_ui_button', None)

# In widget creation:
font=self.font_ui_button if self.font_ui_button else ("Liberation Sans", 12)
```

**Why fallback tuples?**
- TTK styles require tuples, not Font objects
- Graceful degradation if parent doesn't have fonts defined

**Font choices:**
- Liberation Sans 12pt for buttons, tabs, body text (readable on touchscreen)
- Liberation Sans Narrow 11pt ONLY for timestamps/notes (compact, less important)
- Liberation Sans Bold for section titles and window titles

### Files Modified in v1.2.2b Font/Keyboard Work

| File | Changes |
|------|---------|
| dashboard.py | Global font definitions, button bar cleanup |
| virtual_keyboard.py | Focus handling, layout positioning, key press logic |
| message_dialog.py | overrideredirect, fonts, keyboard integration |
| message_list_window.py | Removed emoji icons, font references |
| message_viewer.py | Font references |
| node_detail_window.py | Font references |
| plotter.py | Gets fonts from parent |
| node_alert_config.py | Gets fonts from parent, removed Arial |

### Common Pitfalls to Avoid

1. **Don't use conditional tkraise for Caps toggle** - causes flicker/stuck state
2. **Don't bind Map event to show keyboard** - interferes with window creation
3. **Check if click is inside keyboard before hiding** - prevents keyboard dismissal on key press
4. **Use white cursor, not red** - user is red/green colorblind
5. **TTK styles need tuples for fonts** - Font objects don't work

### Known Cosmetic Issues (Low Priority)

**Whole keyboard window flashes on key press:**
- Cosmetic issue, does not affect functionality
- Likely caused by Tkinter redraw when modifying Text widget
- Individual key flash code disabled as workaround
- Not worth fixing unless it becomes a user complaint

---

## 🎨 Qt/PySide6 Layout Standards (for consistency across windows)

**Target Display:** Raspberry Pi 10" touchscreen at 1280x720

### Standard Sizes

| Element | Size/Value |
|---------|------------|
| Window min-height | 650px (leaves room for taskbar) |
| Button min-width | 70px |
| Button min-height | 32px |
| Scrollbar width | 20px (touch-friendly) |
| Font (body/buttons) | Liberation Sans 12pt |
| Font (section titles) | 12pt bold |
| Font (node name header) | 16pt bold |

### Standard Spacing (tight layout for more data)

| Element | Margin/Padding |
|---------|----------------|
| Window margins | 10px |
| Window spacing | 5px |
| Button bar padding | 6px |
| Button bar spacing | 4px |
| Section frame padding | 4px |
| Section content margins | 8px horizontal, 4px vertical |
| Content row spacing | 2px |
| Scroll area content margins | 4px |
| Scroll area content spacing | 6px |

### Color Scheme (dark theme)

```python
colors = {
    'bg_main': '#1e1e1e',      # Main window background
    'bg_frame': '#2b2b2b',     # Section/frame background
    'fg_normal': '#e0e0e0',    # Normal text
    'fg_secondary': '#b0b0b0', # Labels, less important text
    'fg_good': '#228B22',      # Online/good status
    'fg_warning': '#FFA500',   # Warning status
    'fg_bad': '#FF6B9D',       # Offline/bad status (pink, colorblind-safe)
    'button_bg': '#0d47a1',    # Primary button (blue)
    'button_fg': '#ffffff'     # Button text
}
```

### Scrollbar Styling (touch-friendly)

```python
QScrollBar:vertical {
    background-color: #2b2b2b;
    width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #555555;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #777777;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
```

---

## 🚧 WORK IN PROGRESS: Card Field Registry Refactoring

### Status: Design Complete, Implementation Pending

**Design Document:** `CARD_REGISTRY_DESIGN.md` (do not merge to main docs yet)

**Problem:** `update_node_card()` is tightly coupled to card layout - any layout change requires rewriting ~300 lines

**Solution:** Metadata-driven field registry system with declarative update rules

**Key Files:**
- `CARD_REGISTRY_DESIGN.md` - Full architecture design (IN DEVELOPMENT marker)
- `dashboard.py` line 2285 - TODO comment points to registry design
- This file - WIP tracker (remove this section after implementation complete)

**Next Steps:**
1. Create `card_field_registry.py` module
2. Implement simple field handlers (Temperature, Humidity, Pressure, etc.)
3. Implement composite widget handlers (Battery, SNR)
4. Refactor `update_node_card()` to use registry
5. Test all field updates with live data
6. **AFTER SUCCESSFUL TESTING:**
   - Merge CARD_REGISTRY_DESIGN.md key sections into DESIGN.md
   - Update this file with final architecture
   - Remove WIP markers
   - Remove TODO comment from dashboard.py

**DO NOT FORGET:** This tracking section ensures design work gets integrated into main documentation!

---

## 📋 Recent Enhancements (v1.0.9)

### Enhanced Logging Format (2025-11-24)
**Motivation:** Improve log readability and enable filtering by message type

**Implementation:**
- Standardized format: `MSG_TYPE | short_name/long_name (node_id) | Details`
- Applied to all packet type logging in `data_collector.py`
- Removed debug flash logging from `dashboard.py` (no longer needed)

**Examples:**
```
NODEINFO | AG6W/AG6WR-Attic (!a1b2c3d4) | Names updated
TELEMETRY | Base/Base Station (!e5f6g7h8) | Fields: ['temperature', 'batteryLevel', 'voltage']
MOTION | Deck/Deck Sensor (!i9j0k1l2) | Motion detected
POSITION_APP | Node/Unknown Node (!m3n4o5p6) | Packet received
```

**Benefits:**
- Easy to grep/filter logs by message type
- Consistent format across all packet handlers
- Node identification (short/long names + ID) in every log entry
- Cleaner output without redundant timestamps

**Files Modified:**
- `data_collector.py`: Updated logging in `_process_nodeinfo_packet`, `_process_telemetry_packet`, `_process_motion_packet`, and unknown packet handler
- `dashboard.py`: Removed flash background debug logging

### Plotter Dialog Improvements (2025-11-23)
**Changes:**
- Time Window section: Changed to two-column layout (saves vertical space)
- Added "All available" option for viewing complete data history
- Restored Select Nodes section height to original (180px frame, 130px canvas)

**Files Modified:**
- `plotter.py`: Lines 164-223

---

## 🚀 Active Feature Development: Remote Messaging & Configuration

### Feature Overview
Implementing ability to send messages and configuration commands to remote Meshtastic nodes through the dashboard, using the connected admin node as a gateway.

### Implementation Plan

#### Phase 1: Simple Messaging (Current Focus)
**Goal:** Send text messages to individual nodes or broadcast to all nodes

**Requirements:**
- Message length limit: 200 characters (LoRa constraint after Meshtastic overhead)
- Always use ACK (wantAck=True) - assume no ACK = message not received
- Support broadcast and direct messaging
- Character counter in UI

**UI Design - Message Dialog:**
```
To: [Node Name] or [☑ Broadcast to all nodes]
Message: [text area with counter]
         "45/200 characters"
[Send with ACK] [Cancel]
```

**Access Points:**
- Context menu on node card → "Send Message..." (pre-fills destination)
- Main toolbar → "Send Message..." (allows broadcast option)

#### Phase 2: Admin Permission Detection
**Goal:** Determine if local node can admin remote nodes before showing admin options

**Method:** Check if local node's public key is in remote node's admin_nodes list

**Python API Research Needed:**
```python
# Get local node's public key
my_info = interface.getMyNodeInfo()
my_public_key = my_info.get('user', {}).get('publicKey')

# Get remote node's admin keys
remote_node = interface.getNode(remote_node_id)
admin_keys = remote_node.get('device', {}).get('admin_nodes', [])

# Check if we're authorized
can_admin = my_public_key in admin_keys
```

**Fallback:** Try harmless admin command and catch PermissionError

**UI Behavior:**
- Admin-only menu items should be dimmed/disabled if can't admin
- Show error message if admin command fails due to permissions

#### Phase 3: Remote Requests (No Admin Required)
**Features to implement:**
- Request telemetry update
- Request environment metrics
- Request position update
- Request traceroute to another node
- Request node info refresh

**UI Integration:**
- Node detail window: "Request Telemetry" button (always enabled)
- Context menu: "Request Update" option

#### Phase 4: Remote Configuration (Admin Required)
**Settings to configure:**
- Node name (long name, short name)
- Telemetry intervals
- Module enable/disable
- Other config options (TBD based on testing)

**UI Integration:**
- Context menu: "Remote Configuration..." (dimmed if can't admin)
- Node detail window: "Configure Node" button (dimmed if can't admin)

---

## Technical Architecture Notes

### Network Configuration
- **Admin node:** AG6WR-Attic
- **Connection type:** TCP/IP (eventually Bluetooth support)
- **Admin model:** Public key based (newer firmware, no admin channel)
  - All nodes have AG6WR-Attic's public key in their admin_nodes list
  - No manual configuration needed - verify programmatically

### Connection Manager Enhancements Needed
```python
# In connection_manager.py - methods to add:

def send_text_message(text: str, destination_id: str = "^all", want_ack: bool = True):
    """Send text message with ACK"""
    
def can_admin_node(remote_node_id: str) -> bool:
    """Check if we can admin remote node"""
    
def request_telemetry(node_id: str):
    """Request telemetry update from node"""
    
def request_position(node_id: str):
    """Request position update from node"""
    
def request_traceroute(source_id: str, dest_id: str):
    """Request traceroute between nodes"""
```

### ACK Behavior Research Required
**Questions to answer:**
1. Does `interface.sendText(..., wantAck=True)` work for all command types?
2. What's the response mechanism? Is there an onAck callback?
3. What's the timeout behavior?
4. How do we detect failed delivery vs. successful delivery?

**Testing approach:** Create simple test scripts in feature branch playground

---

## Current Menu Structure (Proposed)

### Card Context Menu (Right-click on node card)
```
Show Details
─────────────
Send Message...          (always enabled)
─────────────
Request Telemetry        (always enabled)
Request Environment      (always enabled)
Request Position         (always enabled)
─────────────
Remote Configuration...  (dimmed if can't admin)
─────────────
Forget Node 'Name'
```

### Node Detail Window Buttons
```
[Send Message] [Request Telemetry] [Configure...] [Logs] [CSV] [Plot] [Close]
     ↑               ↑                   ↑
  Always          Always             Enabled if
  enabled         enabled            can admin
```

---

## Development Workflow

### Immediate Next Steps
1. ✅ Create AI_CONTEXT.md file (this file)
2. ⏭️ Create feature branch: `feature/remote-messaging`
3. ⏭️ Research Python API for sendText and ACK handling
4. ⏭️ Create test scripts to experiment with:
   - Sending messages with ACK
   - Detecting ACK responses
   - Checking admin permissions
5. ⏭️ Document findings
6. ⏭️ Implement connection_manager enhancements
7. ⏭️ Create message dialog UI
8. ⏭️ Add to context menu
9. ⏭️ Test on live network

### Testing Strategy
- Use feature branch for all experiments
- Test with AG6WR-Attic as admin node via TCP/IP
- Verify ACK behavior before implementing UI
- Test permission detection before dimming/enabling features

---

## Design Decisions & Rationale

### Why Message Length Limit = 200 chars?
- LoRa default max payload: 237 bytes
- After Meshtastic overhead (headers, routing, encryption): ~200 bytes usable
- Conservative limit ensures reliability across network conditions

### Why Always Use ACK?
- Provides delivery confirmation
- LoRa is unreliable over distance
- User should know if message failed
- No downside to requesting ACK

### Why Not Manual Admin Node Configuration?
- Newer firmware uses public key lists (device.admin_nodes)
- Can query programmatically via Python API
- Cleaner UX - automatic detection
- Fallback: try admin command and handle failure gracefully

### Why Branch First?
- Experimental feature with network-facing commands
- Need to test ACK behavior before committing
- Can iterate on API usage without breaking main
- Safety: easy to abandon if approach doesn't work

---

## Open Questions / Research Needed

1. **ACK mechanism:** How to detect/handle ACKs in Python API?
2. **Admin key field names:** Firmware version differences (admin_nodes vs admin vs admin_public_keys)
3. **Request commands:** Python API equivalents for CLI commands like `--request-telemetry`
4. **Error handling:** What exceptions are raised for permission denied, timeout, etc.?
5. **Response detection:** How to know when remote node responds to requests?
6. **Message chunking:** Does Meshtastic auto-fragment >200 char messages? Should we prevent this?

---

## Related Files
- `connection_manager.py` - Will add messaging/admin methods here
- `dashboard.py` - Context menu and toolbar integration
- `node_detail_window.py` - Button bar additions
- `data_collector.py` - May need to handle ACK/response packets

---

## Session Notes
- User prefers TCP/IP connection (AG6WR-Attic node)
- Network has single channel currently
- All nodes have AG6WR-Attic as authorized admin
- User wants conservative approach: branch, research, test, then implement

---

**Last Updated:** 2025-11-24  
**Status:** Planning phase - feature branch created, waiting for implementation phase

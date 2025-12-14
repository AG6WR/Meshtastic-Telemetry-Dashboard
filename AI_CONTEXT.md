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

---

## Current Session Context
**Date Started:** 2025-11-17  
**Current Version:** v1.0.14  
**Active Branch:** feature/messaging  
**Last Updated:** 2025-12-14

---

## 🔥 CRITICAL VIRTUAL KEYBOARD BUGS (2025-12-14)

### Current State Summary
Virtual keyboard implementation has three critical issues that need investigation in fresh session:

**Issue 1: WHOLE KEYBOARD FLASHES (Not Individual Keys)**
- **Status:** NOT FIXED - Flash disabled but keyboard still flashes
- **Expected:** Only individual key should flash white briefly when pressed
- **Actual:** Entire keyboard window flashes on ANY key press
- **Attempted Fixes:**
  - Moved flash after tkraise (Caps key)
  - Changed `self.window.after()` to `button.after()`
  - **DISABLED flash entirely** - keyboard STILL flashes (proves flash code is NOT the cause)
- **Hypothesis:** Window redraw triggered by something else (not button color change)
- **Next Steps:** Investigate what's causing window-level redraw on key press
  - Check if `_insert_char()` triggers redraw
  - Check if event_generate causes redraw
  - May need double-buffering or different rendering approach

**Issue 2: NO CURSOR VISIBLE (User Colorblind)**
- **Status:** NOT FIXED despite correct configuration
- **User Accessibility:** Red/green colorblind - red invisible on dark grey (#1e1e1e)
- **Verified Working:** Simple test shows red cursor (5px, always-on)
  ```python
  python -c "import tkinter as tk; root = tk.Tk(); t = tk.Text(root, insertbackground='red', insertwidth=5, insertontime=1000, insertofftime=0); t.pack(); t.focus_set(); root.mainloop()"
  ```
- **Current Config:** `test_keyboard.py` text area
  ```python
  insertbackground='red',  # Same as working test
  insertwidth=5,           # Same as working test  
  insertontime=1000,       # Same as working test
  insertofftime=0          # Always on
  ```
- **Actual:** User sees NO cursor in test_keyboard.py window
- **Hypothesis:** Focus lost when keyboard window appears, or FocusIn event interferes
- **Next Steps:** 
  - Check if keyboard.show() steals focus from text area
  - Try focus_force() instead of focus_set()
  - Add focus event logging to debug
  - Check if bind_all FocusIn event causes issues

**Issue 3: Keyboard Flash Code Commented Out**
- **Location:** `virtual_keyboard.py` lines ~240-250
- **Current State:** Flash calls commented out for testing
- **Action Required:** Re-enable once whole-keyboard flash root cause found

### Working Features (DO NOT BREAK)
- ✅ Caps lock toggle (fixed - removed conditional tkraise)
- ✅ Text entry (fixed - removed Map binding, fixed elif/if bug)
- ✅ Auto-show/hide keyboard (bind_all FocusIn/Button-1)
- ✅ Layout positioning (space bar, gaps, staggers all correct)
- ✅ 2-layout system (lowercase/uppercase, symbols removed)
- ✅ Color scheme (5-color coding)

### Files Modified This Session
- `virtual_keyboard.py` - Caps toggle fix, flash disabled for testing
- `test_keyboard.py` - Cursor config changed to red (matching simple test)
- `message_dialog.py` - Cursor config attempts (currently yellow 6px)

### Critical Code References

**Caps Toggle (WORKING):**
```python
# virtual_keyboard.py line ~234
if key == 'Caps':
    if hasattr(self, '_caps_enabled') and self._caps_enabled:
        self._caps_enabled = False
        self.lowercase_frame.tkraise()  # No conditional - always raise
    else:
        self._caps_enabled = True
        self.uppercase_frame.tkraise()  # No conditional - always raise
    return
```

**Cursor Config (NOT WORKING):**
```python
# test_keyboard.py - SAME as simple test but doesn't show
insertbackground='red',
insertwidth=5,
insertontime=1000,
insertofftime=0
# text_area.focus_set() called after pack
```

**Flash Code (DISABLED):**
```python
# virtual_keyboard.py line ~248-251
# Flash AFTER tkraise - DISABLED for testing
#if button:
#    self._flash_key(button)
```

### Next Session Action Plan
1. **Investigate whole-keyboard flash** (highest priority)
   - Add print statements to track what triggers redraw
   - Check if it's event_generate, widget updates, or something else
   - Test without any text insertion to isolate cause
   
2. **Fix cursor visibility** 
   - Add focus debugging (print when focus changes)
   - Try different focus strategies
   - Check if multiple windows interfere
   
3. **Re-enable individual key flash** (only after fixing whole-keyboard flash)

4. **Commit working state** before conversation restart

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

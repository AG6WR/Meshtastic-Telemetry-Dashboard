# AI ChatBot Persistence - Active Design Work

## Current Session Context
**Date Started:** 2025-11-17  
**Current Version:** v1.0.9  
**Active Branch:** main  
**Last Updated:** 2025-11-24

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

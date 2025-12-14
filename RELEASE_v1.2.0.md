# Release v1.2.0 - Messaging System Implementation

**Release Date:** December 13, 2025  
**Branch:** feature/messaging  
**Status:** Ready for Testing

## Overview

This release implements a comprehensive messaging system for the Meshtastic Telemetry Dashboard, enabling users to send, receive, view, and manage text messages through the Meshtastic network.

## Major Features

### 1. Message Center Window
- **Three-tab interface** for organizing messages:
  - **Inbox**: Received messages (non-archived)
  - **Sent**: Sent messages (non-archived)  
  - **Archived**: All archived messages (sent and received)
- **Checkbox-based selection** for bulk operations
- **Message preview cards** showing:
  - Direction indicator (📤 Sent, 📥 Received, 🔔 Bulletin)
  - From/To information
  - Timestamp (with read timestamp for sent messages)
  - First 120 characters of message text
  - Status indicators (🔵 Unread, ✓ Read receipts, [Plain] tag)
- **Scrollable canvas** with automatic width adjustment
- **Window sizing**: 630x600 pixels (30% narrower than previous version)

### 2. Message Composition
- **Compose Dialog** for creating new messages:
  - Node selector for choosing recipient
  - Multi-line text area (3 lines visible, scrollable)
  - Character counter (max 180 chars)
  - Bell character option to alert recipient
  - Send/Cancel buttons with visual distinction
  - Window size: 630x240 pixels
- **Reply functionality** from message viewer or message list
- **Validation**: Prevents reply when multiple messages selected

### 3. Message Viewing
- **MessageViewer window** for full message display:
  - Complete message text
  - Full metadata (from/to, timestamp, direction)
  - Read receipts table (per-recipient delivery/read status)
  - Action buttons: Mark Read, Reply, Archive, Delete
  - Structured/unstructured message indicators
- **Auto-refresh** after actions to keep UI synchronized

### 4. Message Management
- **Archive**: Move messages to Archived tab (preserves for EmComm use)
- **Delete**: Permanent removal with confirmation dialog and warning
- **Mark as Read**: Manual read status control
- **Bulk operations**: Select multiple messages for archive/delete
- **Automatic cleanup**: Configurable retention period (default 30 days)

### 5. Message Storage
- **JSON-based persistence** in `config/messages.json`
- **Structured message format**:
  ```json
  {
    "message_id": "unique_id",
    "from_node_id": "!a20a0de0",
    "from_name": "Node Name",
    "to_node_ids": ["!a20a0fb0"],
    "text": "Message content",
    "timestamp": 1702483200.0,
    "direction": "sent|received",
    "is_bulletin": false,
    "read": false,
    "read_at": null,
    "archived": false,
    "delivery_status": "pending|delivered|failed",
    "delivered_at": null,
    "read_receipts": {},
    "structured": true
  }
  ```
- **MessageManager API**:
  - `save_message()`: Add new message
  - `load_messages()`: Get all messages
  - `get_message_by_id()`: Retrieve specific message
  - `mark_as_read()`: Update read status
  - `archive_message()`: Archive message
  - `delete_message()`: Remove message
  - `update_delivery_status()`: Track delivery
  - `add_read_receipt()`: Record read receipts

## UI/UX Improvements

### Window Sizing
- **Message Center**: 630x600 (optimized for readability)
- **Compose/Reply Dialog**: 630x240 (compact, focused)
- **Message Viewer**: 750x350 (adequate for full message display)
- All windows resizable for user preference

### Visual Design
- **Dark theme consistency** throughout messaging UI
- **Color coding**:
  - White: All message types (sent, received, bulletin)
  - Green: Reserved for confirmed read receipts
  - Blue: Unread indicator
  - Gray: Secondary text (timestamps, labels)
- **White checkmarks** on dark backgrounds (fixed visibility issue)
- **Scrollable frames** with proper width binding to canvas

### Accessibility
- **Clear visual hierarchy** with bold headers
- **Intuitive icons** (📤📥🔔🔵✓)
- **Confirmation dialogs** for destructive actions
- **Warning messages** for EmComm scenarios (prefer archive over delete)

## Technical Implementation

### Architecture
```
Dashboard (main window)
  ├─ Messages button → MessageListWindow
  │   ├─ Tabs (Inbox/Sent/Archived)
  │   │   └─ Canvas + Scrollable Frame
  │   │       └─ Message Row Cards (checkbox + content)
  │   └─ Action Buttons (View/Reply/Archive/Delete/Compose)
  │       ├─ View → MessageViewer
  │       ├─ Reply → MessageDialog
  │       └─ Compose → MessageDialog
  └─ MessageManager (backend)
      └─ messages.json
```

### Key Components

**message_list_window.py** (586 lines)
- Main message center interface
- Three-tab notebook layout
- Checkbox-based selection system
- Bulk operation handlers
- Canvas/scrollable frame pattern

**message_dialog.py** (215 lines)
- Compose and reply dialog
- Text area with scrollbar
- Character counter (180 char limit)
- Bell character option
- Node selector integration

**message_viewer.py** (280 lines)
- Full message display
- Read receipts table
- Action buttons
- Structured/plain message handling

**message_manager.py** (359 lines)
- Message persistence layer
- CRUD operations
- Read receipt tracking
- Delivery status management
- Automatic cleanup (30-day retention)

**dashboard.py** (3854 lines)
- Integration point for messaging
- Callback handlers
- Color scheme definition
- Messages button and unread count

### Bug Fixes in This Release

1. **Empty Message List** (Critical)
   - Issue: Duplicate `_refresh_tab()` methods (TreeView overriding checkbox version)
   - Fix: Removed old TreeView code (lines 386-518), kept checkbox implementation

2. **View Button Crash** (Critical)
   - Issue: Called `get_message()` instead of `get_message_by_id()`
   - Fix: Updated method calls in dashboard.py and message_list_window.py

3. **Invisible Checkmarks** (High)
   - Issue: Black checkmark on dark background
   - Fix: Added `fg='white'` and `activeforeground='white'` to checkboxes

4. **MessageDialog Not Showing** (Critical)
   - Issue: Dialog created but `.show()` never called
   - Fix: Added `dialog.show()` after instantiation in dashboard.py

5. **Message Cards Not Filling Width** (Medium)
   - Issue: Cards ended 2/3 across with dead space
   - Fix: Added canvas configure binding to match scrollable frame width to canvas

6. **Archive Not Working** (Critical)
   - Issue: Called `save_message()` which appends instead of updating
   - Fix: Created `archive_message()` method to properly update existing messages

7. **Color Key Mismatch** (Critical)
   - Issue: MessageDialog expected `bg_input`, `bg_button_send`, `bg_button_cancel` keys
   - Fix: Updated to use dashboard's actual color keys (`bg_main`, `button_bg`, `fg_good`)

## Configuration

### Message Settings (in config/app_config.json)
```json
{
  "message_retention_days": 30,
  "max_message_length": 180,
  "enable_read_receipts": true,
  "enable_delivery_status": true
}
```

### Files Modified
- `dashboard.py`: Added messaging callbacks and integration
- `message_list_window.py`: Complete rewrite with checkbox interface
- `message_dialog.py`: Fixed color scheme and window sizing
- `message_viewer.py`: Enhanced with read receipts table
- `message_manager.py`: Added `archive_message()` method
- `config/messages.json`: Message storage (auto-created)

## Known Limitations

1. **Read Receipts**: Requires bidirectional communication - needs testing with multiple dashboards
2. **Delivery Status**: Currently tracks local status only - network delivery pending Meshtastic protocol support
3. **Bulletin Messages**: UI support complete, network broadcast testing pending
4. **Reply Tracking**: Infrastructure ready but not yet tracking which messages are replies to others

## Testing Required

### Single Dashboard Testing (Completed)
- ✅ Message list display (Inbox/Sent/Archived tabs)
- ✅ Compose new message (UI only - send pending network)
- ✅ View message details
- ✅ Archive messages (moves to Archived tab)
- ✅ Delete messages (with confirmation)
- ✅ Mark as read
- ✅ Bulk operations (multiple selection)
- ✅ Window sizing and layout
- ✅ Checkbox visibility

### Multi-Dashboard Testing (Pending)
- ⏳ Send message between nodes
- ⏳ Receive message and display in Inbox
- ⏳ Read receipts tracking
- ⏳ Delivery status updates
- ⏳ Bulletin message broadcast
- ⏳ Reply threading
- ⏳ Network latency handling

## Future Enhancements

1. **Reply Threading**: Track which messages are replies and show thread view
2. **Message Search**: Filter/search messages by content, sender, date
3. **Export**: Export messages to CSV/text for record-keeping
4. **Templates**: Pre-defined message templates for common scenarios
5. **Attachments**: Support for position reports, waypoints as message attachments
6. **Encryption**: UI for encrypted message indicators
7. **Priority**: Visual indication for priority/emergency messages
8. **Groups**: Support for group messaging beyond bulletin

## Migration Notes

### From v1.1.0 to v1.2.0
- No breaking changes to existing functionality
- New `config/messages.json` file auto-created on first run
- Message retention cleanup runs automatically every 24 hours
- No user action required

### Rollback Instructions
If issues occur:
1. Stop dashboard
2. `git checkout main`
3. Delete `config/messages.json` (optional - preserves messages if you return to v1.2.0)
4. Restart dashboard

## Installation

```bash
# Already on feature/messaging branch
git pull origin feature/messaging

# Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run dashboard
python dashboard.py
```

## Usage

### Sending a Message
1. Click **Messages** button on main dashboard
2. Click **Compose** button
3. Select recipient node from dropdown
4. Type message (max 180 characters)
5. Optionally check "Send bell character" to alert recipient
6. Click **Send**

### Viewing Messages
1. Open Message Center (Messages button)
2. Navigate to **Inbox** (received) or **Sent** tab
3. Click on any message card to view full details
4. Use **Reply** button to respond

### Managing Messages
1. Select one or more messages using checkboxes
2. Click **Archive** to move to Archived tab (recommended for EmComm)
3. Click **Delete** to permanently remove (use with caution)

### Bulk Operations
1. Check multiple message checkboxes
2. Click **Archive** or **Delete** for bulk operation
3. Confirm action in dialog

## EmComm/Emergency Use Recommendations

1. **Archive, Don't Delete**: Keep all emergency-related messages archived for record-keeping
2. **Regular Exports**: Plan to export message logs regularly (feature coming in v1.3.0)
3. **Read Receipts**: Enable to confirm critical messages were received
4. **Bulletin for Alerts**: Use bulletin mode for emergency broadcasts to all nodes

## Credits

**Developer**: Brian (AG6WR)  
**AI Assistant**: GitHub Copilot (Claude Sonnet 4.5)  
**Framework**: Meshtastic Python API, Tkinter  
**License**: See LICENSE file

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/AG6WR/Meshtastic-Telemetry-Dashboard/issues
- Branch: feature/messaging
- Merge to main pending multi-dashboard testing

---

**End of Release Notes v1.2.0**

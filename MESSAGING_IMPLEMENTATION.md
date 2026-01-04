# Messaging Feature Implementation Plan

**NOTE: This document is historical. The messaging feature has been fully implemented as of v1.2.0 (December 2025) and enhanced in v2.0.1a with Qt support. See README.md and DESIGN.md for current documentation.**

## Overview
Add text messaging capability to the Meshtastic Telemetry Dashboard with the following features:
- Send messages to individual nodes via context menu
- Display incoming messages with 15-second notification
- Show message indicator for messages received in last 15 minutes
- Display last 5 messages per node in detail window
- Support bell character (\a) for alerts
- Character count with 200-byte limit (UTF-8)

## Technical Details

### Meshtastic API
- Maximum payload: 233 bytes (DATA_PAYLOAD_LEN)
- Conservative limit for text: 200 bytes
- Send via: `interface.sendText(text, destinationId, wantAck=True, channelIndex=0)`
- Receive via: PubSub topic `meshtastic.receive.text`
- Message packet structure includes: from, to, text, timestamp, rxSnr

### Components Created

#### 1. message_dialog.py (COMPLETED)
- Dialog for composing messages
- Character counter showing bytes/200
- Option to prepend bell character (\a)
- UTF-8 byte counting (not character count)
- Prevents exceeding 200 bytes
- Ctrl+Enter to send, Escape to cancel

### Components To Modify

#### 2. data_collector.py
Add message tracking:
```python
# Add to __init__:
self.messages_by_node = {}  # {node_id: [messages]}
self.message_notification_timeout = 15  # seconds
self.message_indicator_timeout = 900  # 15 minutes

# Add method:
def _on_text_message_received(self, packet):
    """Handle received text messages"""
    # Extract message info
    from_node = packet.get('fromId', 'Unknown')
    to_node = packet.get('toId', 'Unknown')
    text = packet['decoded'].get('text', '')
    timestamp = time.time()
    
    # Store message
    if from_node not in self.messages_by_node:
        self.messages_by_node[from_node] = []
    
    message_data = {
        'from': from_node,
        'to': to_node,
        'text': text,
        'timestamp': timestamp,
        'rxSnr': packet.get('rxSnr'),
        'hopLimit': packet.get('hopLimit')
    }
    
    self.messages_by_node[from_node].append(message_data)
    
    # Keep only last 10 messages per node
    if len(self.messages_by_node[from_node]) > 10:
        self.messages_by_node[from_node] = self.messages_by_node[from_node][-10:]
    
    # Notify dashboard for display
    if self.on_message_received:
        self.on_message_received(message_data)

# Subscribe in start():
from pubsub import pub
pub.subscribe(self._on_text_message_received, "meshtastic.receive.text")
```

#### 3. connection_manager.py
Add message sending:
```python
def send_message(self, destination_id: str, text: str) -> bool:
    """Send a text message to a node"""
    if not self.interface or not self.is_connected:
        logger.error("Cannot send message: not connected")
        return False
    
    try:
        logger.info(f"Sending message to {destination_id}: {repr(text)}")
        self.interface.sendText(
            text=text,
            destinationId=destination_id,
            wantAck=True,
            channelIndex=0  # Use primary channel
        )
        return True
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False
```

#### 4. dashboard.py
Add messaging integration:

##### A. Add imports:
```python
from message_dialog import MessageDialog
```

##### B. Add to __init__:
```python
# Message tracking
self.active_message_notifications = {}  # {node_id: notification_widget}
self.message_timers = {}  # {node_id: timer_id}
self.data_collector.on_message_received = self._on_message_received
```

##### C. Add context menu option:
```python
def _show_card_context_menu(self, event, node_id):
    """Show context menu for a card"""
    menu = tk.Menu(self, tearoff=0)
    menu.add_command(label="View Details",
                    command=lambda: self.show_node_detail(node_id))
    menu.add_separator()
    menu.add_command(label="Send Message To...",  # NEW
                    command=lambda: self._send_message_to_node(node_id))
    menu.add_separator()
    # ... rest of menu
```

##### D. Add message sending:
```python
def _send_message_to_node(self, node_id):
    """Open dialog to send message to a node"""
    node_data = self.data_collector.nodes_data.get(node_id)
    if not node_data:
        messagebox.showerror("Error", "Node data not available")
        return
    
    node_name = node_data.get('Node LongName', 'Unknown')
    
    def send_callback(node_id, message, has_bell):
        """Callback to actually send the message"""
        success = self.data_collector.connection_manager.send_message(node_id, message)
        if success:
            messagebox.showinfo("Success", 
                              f"Message sent to {node_name}",
                              parent=self)
        else:
            messagebox.showerror("Error",
                               f"Failed to send message to {node_name}",
                               parent=self)
    
    dialog = MessageDialog(self, node_id, node_name, send_callback)
    dialog.show()
```

##### E. Add message notification display:
```python
def _on_message_received(self, message_data):
    """Handle received message - show notification"""
    from_node = message_data['from']
    to_node = message_data['to']
    text = message_data['text']
    timestamp = message_data['timestamp']
    
    # Get node names
    from_name = self._get_node_name(from_node)
    to_name = self._get_node_name(to_node) if to_node != '^all' else 'ALL'
    
    # Show notification for 15 seconds
    self._show_message_notification(from_node, from_name, to_name, text)
    
    # Set indicator for 15 minutes
    self._set_message_indicator(from_node, timestamp)

def _show_message_notification(self, node_id, from_name, to_name, text):
    """Display message notification for 15 seconds"""
    # Create notification window (or update existing)
    if node_id in self.active_message_notifications:
        # Update existing notification
        notif = self.active_message_notifications[node_id]
        notif.config(text=f"Message From {from_name} To {to_name}: {text}")
    else:
        # Create new notification at top of window
        notif = tk.Label(self,
                        text=f"Message From {from_name} To {to_name}: {text}",
                        bg='#FFA500',  # Orange background
                        fg='black',
                        font=self.font_bold,
                        relief='raised',
                        bd=2,
                        padx=10,
                        pady=5)
        notif.pack(side='top', fill='x', before=self.title_frame)
        self.active_message_notifications[node_id] = notif
    
    # Cancel existing timer if any
    if node_id in self.message_timers:
        self.after_cancel(self.message_timers[node_id])
    
    # Schedule removal after 15 seconds
    timer_id = self.after(15000, lambda: self._remove_message_notification(node_id))
    self.message_timers[node_id] = timer_id

def _remove_message_notification(self, node_id):
    """Remove message notification"""
    if node_id in self.active_message_notifications:
        notif = self.active_message_notifications[node_id]
        notif.destroy()
        del self.active_message_notifications[node_id]
    if node_id in self.message_timers:
        del self.message_timers[node_id]

def _set_message_indicator(self, node_id, timestamp):
    """Set indicator that messages exist (for 15 minutes)"""
    # Store in node data
    with self.data_collector.data_lock:
        if node_id in self.data_collector.nodes_data:
            self.data_collector.nodes_data[node_id]['Last Message Time'] = timestamp
```

##### F. Update card display to show message indicator:
```python
# In create_node_card and update_node_card:
# After motion detection check, add message indicator check:

last_message_time = node_data.get('Last Message Time')
if last_message_time:
    time_since_message = current_time - last_message_time
    if time_since_message <= 900:  # 15 minutes
        # Show message indicator (📧 or "MSG")
        msg_indicator = tk.Label(header_frame, text="📧",
                                bg=bg_color, fg='#FFA500',
                                font=self.font_card_header)
        msg_indicator.pack(side="right", padx=(0, 5))
```

#### 5. node_detail_window.py
Add messages tab showing last 5 messages:
```python
# Add to create_tabs:
self.messages_tab = ttk.Frame(self.notebook)
self.notebook.add(self.messages_tab, text="Messages")
self._create_messages_tab()

def _create_messages_tab(self):
    """Create messages tab showing recent messages"""
    messages_frame = tk.Frame(self.messages_tab, bg='#1e1e1e')
    messages_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    tk.Label(messages_frame, text="Recent Messages (Last 5)",
            bg='#1e1e1e', fg='white',
            font=('Courier New', 12, 'bold')).pack(anchor='w', pady=(0, 10))
    
    # Get messages for this node
    messages = self.data_collector.messages_by_node.get(self.node_id, [])
    recent_messages = messages[-5:]  # Last 5
    
    if not recent_messages:
        tk.Label(messages_frame, text="No messages received yet",
                bg='#1e1e1e', fg='#b0b0b0',
                font=('Courier New', 10)).pack(anchor='w')
    else:
        for msg in reversed(recent_messages):  # Most recent first
            msg_frame = tk.Frame(messages_frame, bg='#2d2d2d', relief='raised', bd=1)
            msg_frame.pack(fill='x', pady=5)
            
            # Header: From and timestamp
            header = tk.Frame(msg_frame, bg='#2d2d2d')
            header.pack(fill='x', padx=5, pady=2)
            
            from_name = self._get_node_name(msg['from'])
            timestamp = datetime.fromtimestamp(msg['timestamp'])
            
            tk.Label(header, text=f"From: {from_name}",
                    bg='#2d2d2d', fg='white',
                    font=('Courier New', 9, 'bold')).pack(side='left')
            tk.Label(header, text=timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    bg='#2d2d2d', fg='#b0b0b0',
                    font=('Courier New', 9)).pack(side='right')
            
            # Message text
            tk.Label(msg_frame, text=msg['text'],
                    bg='#2d2d2d', fg='white',
                    font=('Courier New', 9),
                    wraplength=400,
                    justify='left').pack(fill='x', padx=5, pady=2)
```

## Testing Checklist
- [ ] Send message dialog opens from context menu
- [ ] Character counter shows bytes correctly
- [ ] Cannot exceed 200 bytes
- [ ] Bell character option works
- [ ] Message sends successfully
- [ ] Received messages show 15-second notification
- [ ] Notification shows correct from/to names
- [ ] Message indicator appears on card
- [ ] Indicator persists for 15 minutes
- [ ] Detail window shows last 5 messages
- [ ] Messages ordered newest first
- [ ] Timestamps display correctly

## Future Enhancements
- Message history export
- Search/filter messages
- Message templates
- Group messaging
- Read receipts tracking

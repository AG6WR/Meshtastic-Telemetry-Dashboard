"""
Quick test to inject an unread message for testing card display
"""

from message_manager import MessageManager
from config_manager import ConfigManager
import time

cm = ConfigManager()
mm = MessageManager(cm)

# Get local node ID from config
local_node_id = cm.get('meshtastic.local_node_id')
print(f"Local node ID: {local_node_id}")

# Generate unique message ID using current timestamp
timestamp_ms = int(time.time() * 1000)
message_id = f"test_{timestamp_ms}"

# Create test received message
test_msg = {
    'message_id': message_id,
    'from_node_id': '!a20c30c0',
    'from_name': 'Jesuit Center Hub',
    'to_node_ids': [local_node_id],
    'is_bulletin': False,
    'text': 'This is a test message to verify card display and flash animation!',
    'timestamp': time.time(),
    'direction': 'received',
    'read': False
}

mm.save_message(test_msg)
print(f"\n✓ Test message saved")
print(f"Message ID: {message_id}")
print(f"From: {test_msg['from_name']}")
print(f"Text: {test_msg['text']}")
print(f"\nDashboard should show message within 5 seconds:")
print("1. Message preview on local node card line 2")
print("2. Blue/grey flash animation (1 second cycle)")
print("3. 📧 icon and sender name")

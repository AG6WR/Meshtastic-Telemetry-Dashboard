"""
Manual Message Injection Script

This script simulates receiving messages by directly calling the dashboard's
message handler. Use this to test message reception without needing another
physical Meshtastic node.

Usage:
1. Start the dashboard in one terminal
2. Run this script in another terminal
3. The dashboard should receive and process the test message
"""

import sys
import time

def inject_test_message():
    """Inject a test message directly into the dashboard"""
    print("\n" + "="*60)
    print("MESSAGE INJECTION TOOL")
    print("="*60)
    
    # Create test message data
    test_messages = [
        {
            'from': '!a20a0fb0',
            'to': '!a20a0de0',
            'text': '[MSG:0fb0_1734112345678]Hello from test script!'
        },
        {
            'from': '!a20a1984',
            'to': '!a20a0de0',
            'text': 'Plain text message (no protocol)'
        },
        {
            'from': '!a20a0fb0',
            'to': None,  # Bulletin
            'text': '[MSG:0fb0_1734112345679]This is a bulletin to all nodes'
        }
    ]
    
    print("\nAvailable test messages:")
    for i, msg in enumerate(test_messages, 1):
        print(f"\n{i}. From: {msg['from']}")
        print(f"   To: {msg['to'] or 'ALL (bulletin)'}")
        print(f"   Text: {msg['text'][:50]}...")
    
    print("\n" + "-"*60)
    choice = input("Select message to inject (1-3) or 'c' for custom: ").strip()
    
    if choice.lower() == 'c':
        print("\nCustom message:")
        from_id = input("From node ID (e.g., !a20a0fb0): ").strip()
        to_id = input("To node ID (empty for bulletin): ").strip() or None
        msg_text = input("Message text: ").strip()
        
        # Auto-format if not already formatted
        if not msg_text.startswith('[MSG:'):
            short_id = from_id[1:] if from_id.startswith('!') else from_id
            timestamp_ms = int(time.time() * 1000)
            msg_id = f"{short_id}_{timestamp_ms}"
            msg_text = f"[MSG:{msg_id}]{msg_text}"
        
        message_data = {
            'from': from_id,
            'to': to_id,
            'text': msg_text
        }
    else:
        try:
            idx = int(choice) - 1
            message_data = test_messages[idx]
        except (ValueError, IndexError):
            print("Invalid selection")
            return
    
    print("\n" + "="*60)
    print("MESSAGE TO INJECT:")
    print("="*60)
    print(f"From: {message_data['from']}")
    print(f"To: {message_data['to'] or 'ALL'}")
    print(f"Text: {message_data['text']}")
    print("="*60)
    
    # Try to inject via pubsub (if dashboard is running)
    try:
        from pubsub import pub
        
        print("\nInjecting message via pubsub...")
        pub.sendMessage("meshtastic.receive.text", message_data=message_data)
        print("✓ Message injected successfully!")
        print("\nCheck the dashboard console for:")
        print("  - 'Received protocol message' (if formatted)")
        print("  - 'Received non-protocol message' (if plain text)")
        print("  - Message notification banner should appear")
        
    except ImportError:
        print("\n⚠ pubsub not available - cannot inject")
        print("This script needs to run in the same environment as dashboard.py")
    except Exception as e:
        print(f"\n❌ Injection failed: {e}")
        import traceback
        traceback.print_exc()


def show_stored_messages():
    """Display messages currently in storage"""
    from message_manager import MessageManager
    from config_manager import ConfigManager
    
    print("\n" + "="*60)
    print("STORED MESSAGES")
    print("="*60)
    
    cm = ConfigManager()
    mm = MessageManager(cm)
    
    messages = mm.load_messages()
    
    if not messages:
        print("\nNo messages in storage")
        return
    
    print(f"\nTotal messages: {len(messages)}")
    
    sent = mm.get_sent_messages()
    received = mm.get_received_messages()
    unread = mm.get_unread_messages()
    
    print(f"Sent: {len(sent)}")
    print(f"Received: {len(received)}")
    print(f"Unread: {len(unread)}")
    
    print("\n" + "-"*60)
    print("Recent messages:")
    print("-"*60)
    
    for i, msg in enumerate(messages[:10], 1):  # Show last 10
        direction = "→" if msg['direction'] == 'sent' else "←"
        read_status = "✓" if msg.get('read', True) else "📧"
        timestamp = time.strftime('%m/%d %H:%M', time.localtime(msg['timestamp']))
        
        print(f"\n{i}. {direction} {read_status} [{timestamp}] ID: {msg['message_id']}")
        print(f"   From: {msg['from_name']} ({msg['from_node_id']})")
        print(f"   Text: {msg['text'][:60]}...")
        
        if msg['direction'] == 'sent':
            print(f"   Status: {msg.get('delivery_status', 'unknown')}")


def clear_all_messages():
    """Clear all messages from storage"""
    from message_manager import MessageManager
    from config_manager import ConfigManager
    
    confirm = input("\n⚠ Clear ALL messages from storage? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled")
        return
    
    cm = ConfigManager()
    mm = MessageManager(cm)
    
    count = len(mm.messages)
    mm.messages = []
    mm._save_messages()
    
    print(f"✓ Deleted {count} message(s)")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("MESHTASTIC MESSAGING TOOLS")
    print("="*60)
    print("\n1. Inject test message into running dashboard")
    print("2. View stored messages")
    print("3. Clear all messages")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == '1':
        inject_test_message()
    elif choice == '2':
        show_stored_messages()
    elif choice == '3':
        clear_all_messages()
    else:
        print("Exiting")

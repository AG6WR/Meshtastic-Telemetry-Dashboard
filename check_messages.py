"""
Quick script to check if messages were received
"""
import json
from pathlib import Path

print("\n" + "="*60)
print("MESSAGE STATUS CHECK")
print("="*60)

# Check messages.json
msg_file = Path("config/messages.json")
if msg_file.exists():
    try:
        with open(msg_file, 'r') as f:
            messages = json.load(f)
        
        print(f"\n✓ Messages in storage: {len(messages)}")
        
        if messages:
            print("\nStored messages:")
            for i, msg in enumerate(messages[-5:], 1):  # Show last 5
                print(f"\n{i}. ID: {msg['message_id']}")
                print(f"   From: {msg['from_name']} ({msg['from_node_id']})")
                print(f"   Direction: {msg['direction']}")
                print(f"   Text: {msg['text'][:60]}...")
                print(f"   Read: {msg.get('read', True)}")
        else:
            print("\n⚠ No messages found in storage")
            print("\nPossible reasons:")
            print("1. Messages you sent were plain text (no [MSG:id] format)")
            print("2. Dashboard's _on_message_received not being called")
            print("3. Messages sent before dashboard was running")
            
    except Exception as e:
        print(f"\n❌ Error reading messages.json: {e}")
else:
    print("\n⚠ No messages.json file exists yet")

# Instructions
print("\n" + "="*60)
print("DEBUGGING STEPS:")
print("="*60)
print("\n1. Check the terminal where dashboard is running")
print("   Look for lines like:")
print("   - 'TEXT MESSAGE | From: ... | Text: ...'")
print("   - 'Received protocol message ...'")
print("   - 'Received non-protocol message ...'")
print("\n2. The notification banner appears at TOP of dashboard window")
print("   (yellow background, shows for 15 seconds)")
print("\n3. Messages need [MSG:id]text format to be saved")
print("   Plain text messages show notification but aren't saved")
print("\n4. To see terminal output on Windows:")
print("   - Look at the PowerShell/Command Prompt where you ran")
print("     'python dashboard.py'")
print("   - All log messages appear there in real-time")
print("="*60 + "\n")

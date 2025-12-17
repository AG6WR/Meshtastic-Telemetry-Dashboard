"""
Message Protocol Module

Pure functions for encoding, decoding, and parsing Meshtastic messages.
This module is framework-independent and handles the message protocol logic.

Protocol Format:
    - Messages: [MSG:<message_id>]<message_text>
    - Receipts: [RECEIPT:<message_id>]
    - Message ID format: <sender_short_id>_<timestamp_ms>
      Example: "0de0_1734112345678"
"""

import re
import time
from typing import Tuple, Optional, Dict, Any

# Protocol constants
MSG_PREFIX = "[MSG:"
RECEIPT_PREFIX = "[RECEIPT:"
SUFFIX = "]"

# Regex patterns for parsing
RECEIPT_PATTERN = re.compile(r'^\[RECEIPT:([^\]]+)\]')
MESSAGE_PATTERN = re.compile(r'^\[MSG:([^\]]+)\](.*)$', re.DOTALL)


def generate_message_id(local_node_id: Optional[str] = None) -> str:
    """Generate a unique message ID in format <sender_short>_<timestamp_ms>.
    
    Args:
        local_node_id: The local node's ID (e.g., '!a20a0de0')
        
    Returns:
        Message ID string (e.g., '0de0_1734112345678')
    """
    if local_node_id and local_node_id.startswith('!'):
        short_id = local_node_id[1:]  # Remove '!' prefix
    else:
        short_id = 'unknown'
    
    timestamp_ms = int(time.time() * 1000)
    return f"{short_id}_{timestamp_ms}"


def format_outgoing_message(text: str, message_id: str) -> str:
    """Format a message with protocol prefix for sending.
    
    Args:
        text: The message text to send
        message_id: The unique message ID
        
    Returns:
        Formatted message string: [MSG:<id>]<text>
    """
    return f"{MSG_PREFIX}{message_id}{SUFFIX}{text}"


def format_read_receipt(message_id: str) -> str:
    """Format a read receipt for sending.
    
    Args:
        message_id: The ID of the message being acknowledged
        
    Returns:
        Formatted receipt string: [RECEIPT:<id>]
    """
    return f"{RECEIPT_PREFIX}{message_id}{SUFFIX}"


def parse_receipt(text: str) -> Optional[str]:
    """Parse a read receipt message.
    
    Args:
        text: The raw message text
        
    Returns:
        The message ID if this is a valid receipt, None otherwise
    """
    match = RECEIPT_PATTERN.match(text)
    if match:
        return match.group(1)
    return None


def parse_protocol_message(text: str) -> Optional[Tuple[str, str]]:
    """Parse a protocol-formatted message.
    
    Args:
        text: The raw message text
        
    Returns:
        Tuple of (message_id, message_text) if valid protocol message, None otherwise
    """
    match = MESSAGE_PATTERN.match(text)
    if match:
        return (match.group(1), match.group(2))
    return None


def is_protocol_message(text: str) -> bool:
    """Check if text is a protocol-formatted message.
    
    Args:
        text: The raw message text
        
    Returns:
        True if text starts with [MSG: protocol prefix
    """
    return text.startswith(MSG_PREFIX)


def is_receipt_message(text: str) -> bool:
    """Check if text is a read receipt.
    
    Args:
        text: The raw message text
        
    Returns:
        True if text starts with [RECEIPT: protocol prefix
    """
    return text.startswith(RECEIPT_PREFIX)


def is_bulletin(to_id: Optional[str]) -> bool:
    """Check if a message is a bulletin (broadcast to all nodes).
    
    Args:
        to_id: The destination node ID
        
    Returns:
        True if message is a bulletin (no recipient or ^all)
    """
    return not to_id or to_id == '^all'


def clean_display_text(text: str) -> str:
    """Strip control characters (bell, tab, etc.) from text for display.
    
    Args:
        text: The raw message text
        
    Returns:
        Text with only printable characters and spaces
    """
    return ''.join(c for c in text if c.isprintable() or c == ' ')


def create_message_object(
    message_id: str,
    from_node_id: str,
    from_name: str,
    to_node_ids: list,
    text: str,
    direction: str = 'received',
    structured: bool = True
) -> Dict[str, Any]:
    """Create a standardized message object for storage.
    
    Args:
        message_id: Unique message identifier
        from_node_id: Sender's node ID
        from_name: Sender's display name
        to_node_ids: List of recipient node IDs
        text: Message text (without protocol prefix)
        direction: 'sent' or 'received'
        structured: True if message uses our protocol format
        
    Returns:
        Dictionary with standardized message structure
    """
    return {
        'message_id': message_id,
        'structured': structured,
        'from_node_id': from_node_id,
        'from_name': from_name,
        'to_node_ids': to_node_ids,
        'is_bulletin': is_bulletin(to_node_ids[0] if to_node_ids else None),
        'text': text,
        'timestamp': time.time(),
        'direction': direction,
        'read': False,
        'archived': False
    }


def generate_unstructured_message_id(from_node_id: str) -> str:
    """Generate a message ID for unstructured (external) messages.
    
    Used when receiving messages from external clients (like mobile app)
    that don't use our protocol format.
    
    Args:
        from_node_id: The sender's node ID
        
    Returns:
        Generated message ID string
    """
    clean_id = from_node_id.strip('!')
    timestamp_ms = int(time.time() * 1000)
    return f"{clean_id}_{timestamp_ms}"

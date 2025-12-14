"""
Message Manager Module

Handles storage, retrieval, and management of messages in the Meshtastic Telemetry Dashboard.
Messages are persisted to config/messages.json with automatic retention management.

Message Object Structure:
{
    'message_id': '<sender_short>_<timestamp_ms>',  # e.g., "0de0_1734112345678"
    'from_node_id': '!a20a0de0',
    'from_name': 'NodeName',
    'to_node_ids': ['!a20a0fb0'],  # Empty list for bulletins
    'is_bulletin': False,
    'text': 'Message content (max 150 chars)',
    'timestamp': 1734112345.678,
    'direction': 'sent' or 'received',
    'read': False,
    'read_at': None,
    'delivery_status': 'pending', 'delivered', or 'failed',
    'delivered_at': None,
    'read_receipts': {
        'node_id': {'read': False, 'read_at': None}
    }
}
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class MessageManager:
    """Manages message storage, retrieval, and retention."""
    
    MAX_MESSAGES = 500
    MAX_AGE_DAYS = 90
    
    def __init__(self, config_manager):
        """Initialize the message manager.
        
        Args:
            config_manager: ConfigManager instance for accessing config directory
        """
        self.config_manager = config_manager
        self.messages_file = Path(config_manager.config_dir) / "messages.json"
        self.messages: List[Dict[str, Any]] = []
        self._load_messages()
    
    def _load_messages(self):
        """Load messages from JSON file."""
        try:
            if self.messages_file.exists():
                with open(self.messages_file, 'r', encoding='utf-8') as f:
                    self.messages = json.load(f)
                logger.info(f"Loaded {len(self.messages)} messages from {self.messages_file}")
                
                # Clean up old messages on load
                self._cleanup_old_messages()
            else:
                logger.info(f"No existing messages file at {self.messages_file}, starting fresh")
                self.messages = []
        except Exception as e:
            logger.error(f"Error loading messages from {self.messages_file}: {e}")
            self.messages = []
    
    def _save_messages(self):
        """Save all messages to JSON file."""
        try:
            # Ensure config directory exists
            self.messages_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.messages_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(self.messages)} messages to {self.messages_file}")
        except Exception as e:
            logger.error(f"Error saving messages to {self.messages_file}: {e}")
    
    def _cleanup_old_messages(self):
        """Remove messages exceeding retention limits (500 messages or 90 days)."""
        original_count = len(self.messages)
        
        # Remove messages older than MAX_AGE_DAYS
        cutoff_time = time.time() - (self.MAX_AGE_DAYS * 24 * 60 * 60)
        self.messages = [msg for msg in self.messages if msg.get('timestamp', 0) > cutoff_time]
        
        # If still over MAX_MESSAGES, keep only the newest ones
        if len(self.messages) > self.MAX_MESSAGES:
            # Sort by timestamp descending, keep newest MAX_MESSAGES
            self.messages.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            self.messages = self.messages[:self.MAX_MESSAGES]
        
        removed_count = original_count - len(self.messages)
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old messages (retention: {self.MAX_MESSAGES} msgs or {self.MAX_AGE_DAYS} days)")
            self._save_messages()
    
    def save_message(self, message_dict: Dict[str, Any]) -> bool:
        """Save a new message to storage.
        
        Args:
            message_dict: Message object with all required fields
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Validate required fields
            required_fields = ['message_id', 'from_node_id', 'text', 'timestamp', 'direction']
            for field in required_fields:
                if field not in message_dict:
                    logger.error(f"Message missing required field: {field}")
                    return False
            
            # Add defaults for optional fields
            message_dict.setdefault('from_name', 'Unknown')
            message_dict.setdefault('to_node_ids', [])
            message_dict.setdefault('is_bulletin', False)
            message_dict.setdefault('read', False)
            message_dict.setdefault('read_at', None)
            message_dict.setdefault('delivery_status', 'pending')
            message_dict.setdefault('delivered_at', None)
            message_dict.setdefault('read_receipts', {})
            
            # Append and save
            self.messages.append(message_dict)
            self._save_messages()
            
            # Cleanup if needed
            self._cleanup_old_messages()
            
            logger.info(f"Saved message {message_dict['message_id']} ({message_dict['direction']}) from {message_dict['from_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False
    
    def load_messages(self) -> List[Dict[str, Any]]:
        """Get all messages.
        
        Returns:
            List of all message dictionaries
        """
        return self.messages.copy()
    
    def get_unread_messages(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get unread messages for a specific node (or all unread if node_id is None).
        
        Args:
            node_id: Node ID to filter for (e.g., '!a20a0de0'), or None for all unread
            
        Returns:
            List of unread message dictionaries, sorted by timestamp (newest first)
        """
        # Reload from disk to catch externally added messages
        self._load_messages()
        
        unread = []
        for msg in self.messages:
            # Only received messages can be unread
            if msg.get('direction') != 'received':
                continue
            
            # Check if already read
            if msg.get('read', False):
                continue
            
            # Filter by node if specified
            if node_id:
                # For bulletins, check if sent to all
                if msg.get('is_bulletin', False):
                    unread.append(msg)
                # For direct messages, check if sent to this node
                elif node_id in msg.get('to_node_ids', []):
                    unread.append(msg)
            else:
                unread.append(msg)
        
        # Sort by timestamp descending (newest first)
        unread.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return unread
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read.
        
        Args:
            message_id: ID of the message to mark as read
            
        Returns:
            True if message found and marked, False otherwise
        """
        try:
            for msg in self.messages:
                if msg.get('message_id') == message_id:
                    msg['read'] = True
                    msg['read_at'] = time.time()
                    self._save_messages()
                    logger.info(f"Marked message {message_id} as read")
                    return True
            
            logger.warning(f"Message {message_id} not found for mark_as_read")
            return False
            
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False
    
    def archive_message(self, message_id: str) -> bool:
        """Archive a message.
        
        Args:
            message_id: ID of the message to archive
            
        Returns:
            True if message found and archived, False otherwise
        """
        try:
            for msg in self.messages:
                if msg.get('message_id') == message_id:
                    msg['archived'] = True
                    self._save_messages()
                    logger.info(f"Archived message {message_id}")
                    return True
            
            logger.warning(f"Message {message_id} not found for archive")
            return False
            
        except Exception as e:
            logger.error(f"Error archiving message: {e}")
            return False
    
    def update_delivery_status(self, message_id: str, status: str, delivered_at: Optional[float] = None) -> bool:
        """Update delivery status of a sent message.
        
        Args:
            message_id: ID of the message to update
            status: New status ('pending', 'delivered', 'failed')
            delivered_at: Timestamp when delivered (optional)
            
        Returns:
            True if message found and updated, False otherwise
        """
        try:
            for msg in self.messages:
                if msg.get('message_id') == message_id:
                    msg['delivery_status'] = status
                    if delivered_at:
                        msg['delivered_at'] = delivered_at
                    elif status == 'delivered':
                        msg['delivered_at'] = time.time()
                    
                    self._save_messages()
                    logger.info(f"Updated message {message_id} delivery status to {status}")
                    return True
            
            logger.warning(f"Message {message_id} not found for delivery status update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating delivery status: {e}")
            return False
    
    def add_read_receipt(self, message_id: str, node_id: str, read_at: Optional[float] = None) -> bool:
        """Add a read receipt for a sent message.
        
        Args:
            message_id: ID of the message
            node_id: Node that read the message
            read_at: Timestamp when read (defaults to now)
            
        Returns:
            True if message found and updated, False otherwise
        """
        try:
            for msg in self.messages:
                if msg.get('message_id') == message_id:
                    if 'read_receipts' not in msg:
                        msg['read_receipts'] = {}
                    
                    msg['read_receipts'][node_id] = {
                        'read': True,
                        'read_at': read_at if read_at else time.time()
                    }
                    
                    self._save_messages()
                    logger.info(f"Added read receipt for message {message_id} from node {node_id}")
                    return True
            
            logger.warning(f"Message {message_id} not found for read receipt")
            return False
            
        except Exception as e:
            logger.error(f"Error adding read receipt: {e}")
            return False
    
    def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message by ID.
        
        Args:
            message_id: ID of the message to retrieve
            
        Returns:
            Message dictionary if found, None otherwise
        """
        for msg in self.messages:
            if msg.get('message_id') == message_id:
                return msg.copy()
        return None
    
    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages, sorted by timestamp (newest first).
        
        Returns:
            List of sent message dictionaries
        """
        sent = [msg for msg in self.messages if msg.get('direction') == 'sent']
        sent.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return sent
    
    def get_received_messages(self) -> List[Dict[str, Any]]:
        """Get all received messages, sorted by timestamp (newest first).
        
        Returns:
            List of received message dictionaries
        """
        received = [msg for msg in self.messages if msg.get('direction') == 'received']
        received.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return received
    
    def delete_message(self, message_id: str) -> bool:
        """Delete a message by ID.
        
        Args:
            message_id: ID of the message to delete
            
        Returns:
            True if message found and deleted, False otherwise
        """
        try:
            original_count = len(self.messages)
            self.messages = [msg for msg in self.messages if msg.get('message_id') != message_id]
            
            if len(self.messages) < original_count:
                self._save_messages()
                logger.info(f"Deleted message {message_id}")
                return True
            else:
                logger.warning(f"Message {message_id} not found for deletion")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False

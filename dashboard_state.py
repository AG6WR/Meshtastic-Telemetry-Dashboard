"""
Dashboard State Module

Contains dataclasses and state management for the Meshtastic Telemetry Dashboard.
This module is framework-independent and can be used by both Tkinter and Qt versions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class ViewMode(Enum):
    """Dashboard view modes"""
    CARDS = "cards"
    TABLE = "table"


@dataclass
class MessageState:
    """State for message notification handling"""
    recent_messages: List[Tuple[str, str, str]] = field(default_factory=list)  # (from_name, to_name, text)
    unread_messages: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # node_id -> messages
    message_flash_state: Dict[str, bool] = field(default_factory=dict)  # node_id -> flash on/off
    notification_index: int = 0  # Current message being displayed in rotation
    
    MAX_RECENT_MESSAGES = 3
    
    def add_recent_message(self, from_name: str, to_name: str, text: str):
        """Add a message to recent messages list, keeping only the last MAX_RECENT_MESSAGES"""
        self.recent_messages.append((from_name, to_name, text))
        if len(self.recent_messages) > self.MAX_RECENT_MESSAGES:
            self.recent_messages.pop(0)
    
    def add_unread_message(self, node_id: str, message: Dict[str, Any]):
        """Add an unread message for a node"""
        if node_id not in self.unread_messages:
            self.unread_messages[node_id] = []
        self.unread_messages[node_id].append(message)
    
    def get_unread_count(self, node_id: Optional[str] = None) -> int:
        """Get unread message count for a node or total"""
        if node_id:
            return len(self.unread_messages.get(node_id, []))
        return sum(len(msgs) for msgs in self.unread_messages.values())
    
    def clear_unread(self, node_id: str):
        """Clear unread messages for a node"""
        if node_id in self.unread_messages:
            self.unread_messages[node_id] = []
    
    def toggle_flash_state(self) -> None:
        """Toggle flash state for all nodes with unread messages"""
        for node_id in self.unread_messages:
            if self.unread_messages[node_id]:
                current = self.message_flash_state.get(node_id, False)
                self.message_flash_state[node_id] = not current
    
    def advance_notification_index(self) -> None:
        """Advance to next message in rotation"""
        if self.recent_messages:
            self.notification_index = (self.notification_index + 1) % len(self.recent_messages)
    
    def get_current_notification(self) -> Optional[Tuple[str, str, str]]:
        """Get the current notification message to display"""
        if not self.recent_messages:
            return None
        return self.recent_messages[self.notification_index]


@dataclass
class NodeDisplayState:
    """State for node card/table display"""
    nodes_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # node_id -> data
    last_node_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Previous state for change detection
    selected_node_id: Optional[str] = None
    view_mode: ViewMode = ViewMode.CARDS
    cards_per_row: int = 0  # Current column count for resize detection
    
    def set_view_mode(self, mode: str):
        """Set view mode from string"""
        self.view_mode = ViewMode(mode)
    
    def get_view_mode_str(self) -> str:
        """Get view mode as string"""
        return self.view_mode.value
    
    def has_node_changed(self, node_id: str, new_data: Dict[str, Any]) -> bool:
        """Check if node data has changed since last update"""
        if node_id not in self.nodes_data:
            return True
        old_data = self.nodes_data[node_id]
        
        # Compare key telemetry fields
        compare_keys = [
            'Node ShortName', 'Node LongName', 'Device Battery Level',
            'ICP Battery Level', 'ICP Ext Power', 'Temperature',
            'Uptime Seconds', 'SNR', 'Last Heard', 'Motion'
        ]
        
        for key in compare_keys:
            if old_data.get(key) != new_data.get(key):
                return True
        return False
    
    def update_node_data(self, node_id: str, data: Dict[str, Any]):
        """Update node data and track previous state for change detection"""
        # Store the previous data for rollback/comparison if needed
        if node_id in self.nodes_data:
            self.last_node_data[node_id] = self.nodes_data[node_id].copy()
        # Update current data
        self.nodes_data[node_id] = data


@dataclass 
class DashboardState:
    """Combined application state"""
    message_state: MessageState = field(default_factory=MessageState)
    node_state: NodeDisplayState = field(default_factory=NodeDisplayState)
    is_fullscreen: bool = True
    last_refresh_time: float = 0
    
    def reset(self):
        """Reset all state to defaults"""
        self.message_state = MessageState()
        self.node_state = NodeDisplayState()
        self.is_fullscreen = True
        self.last_refresh_time = 0


# Color scheme dataclass - defines the visual theme
@dataclass
class ColorScheme:
    """Dark theme color palette for the dashboard"""
    bg_main: str = '#1e1e1e'        # Main window background
    bg_frame: str = '#2d2d2d'       # Card/frame background (normal state)
    bg_local_node: str = '#1e2d1e'  # Local node card background (dark green tint)
    bg_stale: str = '#3d2d2d'       # Table rows with stale data (dark red tint)
    bg_selected: str = '#1a237e'    # Selected table rows and flash effect (very dark blue)
    fg_normal: str = '#ffffff'      # Primary text color (white)
    fg_secondary: str = '#b0b0b0'   # Labels and stale data text (light gray)
    button_bg: str = '#404040'      # Button backgrounds
    button_fg: str = '#ffffff'      # Button text
    fg_good: str = '#228B22'        # Positive values (forest green)
    fg_warning: str = '#FFA500'     # Warning values (orange)
    fg_yellow: str = '#FFFF00'      # Caution values (yellow)
    fg_bad: str = '#FF6B9D'         # Negative values (coral pink)
    accent: str = '#4a90d9'         # Accent color for interactive elements (blue)
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for backward compatibility"""
        return {
            'bg_main': self.bg_main,
            'bg_frame': self.bg_frame,
            'bg_local_node': self.bg_local_node,
            'bg_stale': self.bg_stale,
            'bg_selected': self.bg_selected,
            'fg_normal': self.fg_normal,
            'fg_secondary': self.fg_secondary,
            'button_bg': self.button_bg,
            'button_fg': self.button_fg,
            'fg_good': self.fg_good,
            'fg_warning': self.fg_warning,
            'fg_yellow': self.fg_yellow,
            'fg_bad': self.fg_bad,
            'accent': self.accent
        }


# Default color scheme instance
DEFAULT_COLORS = ColorScheme()

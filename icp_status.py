"""
ICP Status Broadcaster/Receiver Module

Handles broadcasting and receiving ICP status messages between Meshtastic nodes.
Each dashboard broadcasts its own calculated status; other dashboards display 
what each node reports about itself.

Message Format:
    [ICP-STATUS]<status>|<reasons>|<help>|<version>|<timestamp>
    
Examples:
    [ICP-STATUS]GREEN||NO|2.1.0|1735689600
    [ICP-STATUS]YELLOW|Battery|NO|2.1.0|1735689600
    [ICP-STATUS]RED|Battery,Temperature|YES|2.1.0|1735689600

Status Thresholds:
    Battery %: >50% green, 25-50% yellow, <25% red
    Voltage: ≥4.0V green, 3.5-4.0V yellow, <3.5V red
    Temperature: 0-35°C green, 35-45°C or <0°C yellow, >45°C red
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple, List, Callable
from threading import Timer, Lock

logger = logging.getLogger(__name__)

# Message prefix for ICP status broadcasts
ICP_STATUS_PREFIX = "[ICP-STATUS]"

# Broadcast interval in seconds (15 minutes)
BROADCAST_INTERVAL_SECONDS = 15 * 60

# Status constants
STATUS_GREEN = "GREEN"
STATUS_YELLOW = "YELLOW"
STATUS_RED = "RED"


class ICPStatusBroadcaster:
    """
    Broadcasts local ICP status to other nodes on the mesh.
    
    Features:
    - Periodic heartbeat broadcast (every 15 minutes)
    - Immediate broadcast on status change
    - SEND HELP flag support with auto-clear after 1 hour
    """
    
    # Auto-clear help flag after 1 hour
    HELP_AUTO_CLEAR_SECONDS = 60 * 60
    
    def __init__(self, 
                 get_local_node_data: Callable[[], Optional[Dict[str, Any]]],
                 send_broadcast: Callable[[str], bool],
                 version: str = "2.1.0"):
        """
        Initialize the ICP Status Broadcaster.
        
        Args:
            get_local_node_data: Callback to get local node's telemetry data dict
            send_broadcast: Callback to send a broadcast message (text) -> success
            version: Dashboard version string to include in broadcasts
        """
        self._get_local_node_data = get_local_node_data
        self._send_broadcast = send_broadcast
        self._version = version
        
        self._lock = Lock()
        self._last_status: Optional[str] = None
        self._last_reasons: List[str] = []
        self._help_requested = False
        self._help_requested_at: Optional[float] = None
        
        self._heartbeat_timer: Optional[Timer] = None
        self._help_clear_timer: Optional[Timer] = None
        self._running = False
        
    def start(self):
        """Start the broadcaster with periodic heartbeat."""
        with self._lock:
            if self._running:
                return
            self._running = True
            
        logger.info("ICP Status Broadcaster started")
        
        # Send initial broadcast after short delay (let connection stabilize)
        self._schedule_heartbeat(delay_seconds=30)
        
    def stop(self):
        """Stop the broadcaster and cancel timers."""
        with self._lock:
            self._running = False
            
            if self._heartbeat_timer:
                self._heartbeat_timer.cancel()
                self._heartbeat_timer = None
                
            if self._help_clear_timer:
                self._help_clear_timer.cancel()
                self._help_clear_timer = None
                
        logger.info("ICP Status Broadcaster stopped")
        
    def request_help(self) -> bool:
        """
        Set the SEND HELP flag and broadcast immediately.
        
        Returns:
            True if help request was set and broadcast sent
        """
        with self._lock:
            if self._help_requested:
                logger.info("Help already requested, ignoring duplicate request")
                return False
                
            self._help_requested = True
            self._help_requested_at = time.time()
            
            # Schedule auto-clear
            if self._help_clear_timer:
                self._help_clear_timer.cancel()
            self._help_clear_timer = Timer(
                self.HELP_AUTO_CLEAR_SECONDS, 
                self._auto_clear_help
            )
            self._help_clear_timer.daemon = True
            self._help_clear_timer.start()
            
        logger.warning("HELP REQUESTED - broadcasting immediately")
        self._broadcast_status(force=True)
        return True
        
    def clear_help(self) -> bool:
        """
        Clear the SEND HELP flag and broadcast immediately.
        
        Returns:
            True if help was cleared and broadcast sent
        """
        with self._lock:
            if not self._help_requested:
                return False
                
            self._help_requested = False
            self._help_requested_at = None
            
            if self._help_clear_timer:
                self._help_clear_timer.cancel()
                self._help_clear_timer = None
                
        logger.info("Help request cleared - broadcasting immediately")
        self._broadcast_status(force=True)
        return True
        
    def _auto_clear_help(self):
        """Auto-clear help flag after timeout."""
        logger.info("Auto-clearing help request after 1 hour timeout")
        self.clear_help()
        
    def is_help_requested(self) -> bool:
        """Check if SEND HELP is currently active."""
        with self._lock:
            return self._help_requested
            
    def check_and_broadcast_if_changed(self):
        """
        Check current status and broadcast if it changed.
        Call this after telemetry updates.
        """
        status, reasons = self._calculate_status()
        
        with self._lock:
            status_changed = (status != self._last_status or 
                            set(reasons) != set(self._last_reasons))
                            
        if status_changed:
            logger.info(f"Status changed: {self._last_status} -> {status}, reasons: {reasons}")
            self._broadcast_status(force=True)
            
    def _schedule_heartbeat(self, delay_seconds: float = BROADCAST_INTERVAL_SECONDS):
        """Schedule the next heartbeat broadcast."""
        with self._lock:
            if not self._running:
                return
                
            if self._heartbeat_timer:
                self._heartbeat_timer.cancel()
                
            self._heartbeat_timer = Timer(delay_seconds, self._on_heartbeat)
            self._heartbeat_timer.daemon = True
            self._heartbeat_timer.start()
            
    def _on_heartbeat(self):
        """Handle periodic heartbeat - broadcast status and reschedule."""
        if not self._running:
            return
            
        logger.debug("ICP Status heartbeat - broadcasting status")
        self._broadcast_status(force=False)
        self._schedule_heartbeat()
        
    def _calculate_status(self) -> Tuple[str, List[str]]:
        """
        Calculate ICP status from local telemetry data.
        
        Returns:
            Tuple of (status, reasons_list)
            - status: "GREEN", "YELLOW", or "RED"
            - reasons_list: List of reasons for non-green status
        """
        node_data = self._get_local_node_data()
        
        if not node_data:
            # No data available - report as GREEN with no issues
            return STATUS_GREEN, []
            
        warnings = []  # Yellow-level issues
        criticals = []  # Red-level issues
        
        # Check Battery % (from node's internal battery)
        battery = node_data.get('Battery Level')
        if battery is not None:
            if battery < 25:
                criticals.append("Node Battery")
            elif battery <= 50:
                warnings.append("Node Battery")
        
        # Check Voltage (Ch3 Voltage for ICP external battery)
        voltage = node_data.get('Ch3 Voltage')
        if voltage is not None:
            if voltage < 3.5:
                criticals.append("ICP Battery")
            elif voltage < 4.0:
                warnings.append("ICP Battery")
        
        # Check Temperature (in Celsius)
        temp = node_data.get('Temperature')
        if temp is not None:
            if temp > 45:
                criticals.append("Temperature")
            elif temp > 35 or temp < 0:
                warnings.append("Temperature")
        
        # Determine overall status (worst wins)
        if criticals:
            return STATUS_RED, criticals + warnings
        elif warnings:
            return STATUS_YELLOW, warnings
        else:
            return STATUS_GREEN, []
            
    def _build_status_message(self) -> str:
        """
        Build the ICP status message string.
        
        Format: [ICP-STATUS]<status>|<reasons>|<help>|<version>|<timestamp>
        """
        status, reasons = self._calculate_status()
        
        with self._lock:
            help_flag = "YES" if self._help_requested else "NO"
            self._last_status = status
            self._last_reasons = reasons
            
        reasons_str = ",".join(reasons) if reasons else ""
        timestamp = int(time.time())
        
        message = f"{ICP_STATUS_PREFIX}{status}|{reasons_str}|{help_flag}|{self._version}|{timestamp}"
        return message
        
    def _broadcast_status(self, force: bool = False):
        """
        Broadcast current ICP status.
        
        Args:
            force: If True, broadcast even if status hasn't changed
        """
        if not self._running and not force:
            return
            
        message = self._build_status_message()
        
        try:
            success = self._send_broadcast(message)
            if success:
                logger.info(f"ICP Status broadcast sent: {message}")
            else:
                logger.warning(f"ICP Status broadcast failed: {message}")
        except Exception as e:
            logger.error(f"Error broadcasting ICP status: {e}")


class ICPStatusReceiver:
    """
    Receives and parses ICP status messages from other nodes.
    
    Updates node data with received status information for display.
    """
    
    def __init__(self, update_node_status: Callable[[str, Dict[str, Any]], None]):
        """
        Initialize the ICP Status Receiver.
        
        Args:
            update_node_status: Callback to update a node's status data
                               (node_id, status_dict) -> None
        """
        self._update_node_status = update_node_status
        
    def is_status_message(self, text: str) -> bool:
        """Check if a message is an ICP status broadcast."""
        return text.startswith(ICP_STATUS_PREFIX)
        
    def parse_and_update(self, from_node_id: str, text: str) -> bool:
        """
        Parse an ICP status message and update the node's status.
        
        Args:
            from_node_id: Node ID that sent the message
            text: Full message text including prefix
            
        Returns:
            True if message was parsed successfully, False otherwise
        """
        if not self.is_status_message(text):
            return False
            
        try:
            # Remove prefix and parse
            payload = text[len(ICP_STATUS_PREFIX):]
            parts = payload.split("|")
            
            if len(parts) < 5:
                logger.warning(f"Invalid ICP status message format from {from_node_id}: {text}")
                return False
                
            status = parts[0]  # GREEN, YELLOW, RED
            reasons = parts[1].split(",") if parts[1] else []
            help_flag = parts[2] == "YES"
            version = parts[3]
            timestamp = int(parts[4])
            
            # Validate status
            if status not in (STATUS_GREEN, STATUS_YELLOW, STATUS_RED):
                logger.warning(f"Invalid status value from {from_node_id}: {status}")
                return False
                
            # Build status dict for node update
            status_data = {
                'icp_status': status,
                'icp_reasons': reasons,
                'icp_help_requested': help_flag,
                'icp_version': version,
                'icp_status_timestamp': timestamp,
                'icp_status_received_at': time.time()
            }
            
            logger.info(f"Received ICP status from {from_node_id}: {status} "
                       f"(reasons: {reasons}, help: {help_flag})")
            
            self._update_node_status(from_node_id, status_data)
            return True
            
        except Exception as e:
            logger.error(f"Error parsing ICP status from {from_node_id}: {e}")
            return False


def create_status_message(status: str, reasons: List[str], 
                         help_requested: bool, version: str) -> str:
    """
    Utility function to create an ICP status message.
    
    Args:
        status: "GREEN", "YELLOW", or "RED"
        reasons: List of reason strings
        help_requested: Whether SEND HELP is active
        version: Dashboard version string
        
    Returns:
        Formatted ICP status message string
    """
    reasons_str = ",".join(reasons) if reasons else ""
    help_flag = "YES" if help_requested else "NO"
    timestamp = int(time.time())
    
    return f"{ICP_STATUS_PREFIX}{status}|{reasons_str}|{help_flag}|{version}|{timestamp}"

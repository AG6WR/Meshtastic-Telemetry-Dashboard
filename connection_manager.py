"""
Enhanced Connection Manager for Meshtastic Monitoring
Handles TCP/Serial/BLE connections with auto-reconnection and failover
"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from threading import Thread, Event
import meshtastic
import meshtastic.tcp_interface
import meshtastic.serial_interface
from pubsub import pub

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages Meshtastic interface connections with auto-reconnection"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.interface = None
        self.is_connected = False
        self.connection_thread = None
        self.stop_event = Event()
        self.reconnect_interval = config.get('retry_interval', 60)
        self.connection_timeout = config.get('connection_timeout', 30)
        
        # Connection callbacks
        self.on_connected_callback = None
        self.on_disconnected_callback = None
        self.on_packet_callback = None
        
        # Current interface info
        self.current_interface_info = {}
        
    def set_callbacks(self, on_connected: Callable = None, on_disconnected: Callable = None, on_packet: Callable = None):
        """Set callback functions for connection events"""
        self.on_connected_callback = on_connected
        self.on_disconnected_callback = on_disconnected
        self.on_packet_callback = on_packet
    
    def start(self):
        """Start the connection manager"""
        if self.connection_thread and self.connection_thread.is_alive():
            logger.warning("Connection manager already running")
            return
            
        self.stop_event.clear()
        self.connection_thread = Thread(target=self._connection_loop, daemon=True)
        self.connection_thread.start()
        logger.info("Connection manager started")
    
    def stop(self):
        """Stop the connection manager"""
        logger.info("Stopping connection manager...")
        self.stop_event.set()
        
        if self.interface:
            try:
                self.interface.close()
            except Exception as e:
                logger.error(f"Error closing interface: {e}")
            self.interface = None
            
        if self.connection_thread:
            self.connection_thread.join(timeout=5)
            
        self.is_connected = False
        logger.info("Connection manager stopped")
    
    def _connection_loop(self):
        """Main connection loop with auto-reconnection"""
        while not self.stop_event.is_set():
            try:
                if not self.is_connected:
                    self._attempt_connection()
                
                # Check connection health
                if self.is_connected and not self._check_connection_health():
                    logger.warning("Connection health check failed")
                    self._disconnect()
                
                # Wait before next iteration
                self.stop_event.wait(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in connection loop: {e}")
                self._disconnect()
                self.stop_event.wait(self.reconnect_interval)
    
    def _attempt_connection(self):
        """Attempt to establish connection using configured interface"""
        interface_config = self.config.get('interface', {})
        interface_type = interface_config.get('type', 'tcp').lower()
        
        logger.info(f"Attempting {interface_type} connection...")
        
        try:
            if interface_type == 'tcp':
                self._connect_tcp(interface_config)
            elif interface_type == 'serial':
                self._connect_serial(interface_config)
            else:
                logger.error(f"Unsupported interface type: {interface_type}")
                return
                
        except Exception as e:
            logger.error(f"Connection attempt failed: {e}")
            self.stop_event.wait(self.reconnect_interval)
    
    def _connect_tcp(self, config: Dict[str, Any]):
        """Connect via TCP"""
        host = config.get('host', '192.168.1.91')
        port = config.get('port', 4403)
        
        logger.info(f"Connecting to TCP {host}:{port}")
        
        # Subscribe to packets before creating interface
        pub.subscribe(self._on_packet_received, "meshtastic.receive")
        pub.subscribe(self._on_connection_established, "meshtastic.connection.established")
        pub.subscribe(self._on_connection_lost, "meshtastic.connection.lost")
        
        # Create interface with automatic connection (like original script)
        self.interface = meshtastic.tcp_interface.TCPInterface(
            hostname=host,
            portNumber=port
        )
        
        # Wait a bit for connection to establish
        time.sleep(2)
        
        if self._verify_connection():
            self.is_connected = True
            self.current_interface_info = {
                'type': 'tcp',
                'host': host,
                'port': port,
                'connected_at': time.time()
            }
            
            # Preload node information from interface database
            self._preload_node_info()
            
            logger.info(f"TCP connection established to {host}:{port}")
            if self.on_connected_callback:
                self.on_connected_callback(self.current_interface_info)
        else:
            raise Exception("Failed to verify TCP connection")
    
    def _connect_serial(self, config: Dict[str, Any]):
        """Connect via Serial"""
        port = config.get('port', 'COM3')
        baud = config.get('baud', 115200)
        
        logger.info(f"Connecting to Serial {port} at {baud} baud")
        
        self.interface = meshtastic.serial_interface.SerialInterface(
            devPath=port,
            baudrate=baud,
            connectNow=False
        )
        
        # Subscribe to packets before creating interface
        pub.subscribe(self._on_packet_received, "meshtastic.receive")
        pub.subscribe(self._on_connection_established, "meshtastic.connection.established")
        pub.subscribe(self._on_connection_lost, "meshtastic.connection.lost")
        
        # Create interface with automatic connection
        self.interface = meshtastic.serial_interface.SerialInterface(
            devPath=port,
            baudrate=baud
        )
        time.sleep(2)
        
        if self._verify_connection():
            self.is_connected = True
            self.current_interface_info = {
                'type': 'serial',
                'port': port,
                'baud': baud,
                'connected_at': time.time()
            }
            logger.info(f"Serial connection established to {port}")
            if self.on_connected_callback:
                self.on_connected_callback(self.current_interface_info)
        else:
            raise Exception("Failed to verify Serial connection")
    
    def _verify_connection(self) -> bool:
        """Verify that the connection is working"""
        try:
            if not self.interface:
                return False
            
            # Try to get node info
            info = getattr(self.interface, 'myInfo', None)
            if info:
                return True
                
            # Wait a bit more and try again
            time.sleep(3)
            info = getattr(self.interface, 'myInfo', None)
            return info is not None
            
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return False
    
    def _check_connection_health(self) -> bool:
        """Check if connection is still healthy"""
        try:
            if not self.interface:
                return False
            
            # Basic health check - interface should have myInfo
            return hasattr(self.interface, 'myInfo') and self.interface.myInfo is not None
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False
    
    def _disconnect(self):
        """Disconnect from current interface"""
        if self.is_connected:
            logger.info("Disconnecting...")
            self.is_connected = False
            
            if self.on_disconnected_callback:
                self.on_disconnected_callback(self.current_interface_info)
            
            self.current_interface_info = {}
        
        if self.interface:
            try:
                # Unsubscribe from events
                pub.unsubscribe(self._on_packet_received, "meshtastic.receive")
                pub.unsubscribe(self._on_connection_established, "meshtastic.connection.established")  
                pub.unsubscribe(self._on_connection_lost, "meshtastic.connection.lost")
                
                self.interface.close()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.interface = None
    
    def _on_packet_received(self, packet, interface):
        """Handle received packets"""
        if self.on_packet_callback:
            self.on_packet_callback(packet, interface)
    
    def _on_connection_established(self, interface):
        """Handle connection established event"""
        logger.info("Meshtastic connection established event received")
    
    def _on_connection_lost(self, interface):
        """Handle connection lost event"""
        logger.warning("Meshtastic connection lost event received")
        self.is_connected = False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            'connected': self.is_connected,
            'interface_info': self.current_interface_info.copy(),
            'uptime': time.time() - self.current_interface_info.get('connected_at', time.time()) if self.is_connected else 0
        }
    
    def get_local_node_id(self):
        """Get the local node ID"""
        try:
            if self.interface and hasattr(self.interface, 'myInfo'):
                info = self.interface.myInfo
                if info:
                    # Try newer API field name first
                    node_id = None
                    if hasattr(info, 'my_node_num'):
                        node_id = info.my_node_num
                    elif hasattr(info, 'myNodeNum'):
                        node_id = info.myNodeNum
                    elif 'my_node_num' in info:
                        node_id = info['my_node_num']
                    elif 'myNodeNum' in info:
                        node_id = info['myNodeNum']
                    elif 'my_node_id' in info:
                        node_id = info['my_node_id']
                    
                    if node_id is not None:
                        if isinstance(node_id, int):
                            return f"!{node_id:08x}"
                        return str(node_id).lower()
            return None
        except Exception as e:
            logger.error(f"Error getting local node ID: {e}")
            return None
    
    def _preload_node_info(self):
        """Preload node information from interface database (like original script)"""
        try:
            if not self.interface:
                return
            
            # Access the interface's node database
            nodes_dict = getattr(self.interface, "nodes", {}) or {}
            preload_count = 0
            
            for key, info in nodes_dict.items():
                try:
                    # Normalize node ID (same as original script)
                    node_id = self._normalize_node_id(key)
                    if not node_id and isinstance(info, dict):
                        node_id = self._normalize_node_id(info.get("num") or info.get("id"))
                    
                    if not node_id:
                        continue
                    
                    # Extract user info
                    user = info.get("user", {}) if isinstance(info, dict) else {}
                    long_name = user.get("longName") or "Unknown Node"
                    short_name = user.get("shortName") or "Unknown"
                    
                    # Send to data collector via callback if available  
                    if self.on_packet_callback:
                        # Create a synthetic packet to populate the node data
                        # BUT: Don't set rxTime to avoid updating "Last Heard" during preload
                        synthetic_packet = {
                            'from': key,
                            'decoded': {
                                'portnum': 'NODEINFO_APP',
                                'user': {
                                    'longName': long_name,
                                    'shortName': short_name
                                }
                            },
                            # Don't set 'rxTime' - let data collector handle timestamps for real packets only
                            '_preloaded': True  # Mark as preloaded
                        }
                        self.on_packet_callback(synthetic_packet, self)
                    
                    preload_count += 1
                    
                except Exception as e:
                    logger.debug(f"Error preloading node {key}: {e}")
                    continue
            
            logger.info(f"Preloaded {preload_count} nodes from interface database")
            
        except Exception as e:
            logger.error(f"Node preload failed: {e}")
    
    def _normalize_node_id(self, node_id):
        """Normalize node ID to !xxxxxxxx format (same as original script)"""
        if node_id is None:
            return None
        
        if isinstance(node_id, int):
            return f"!{node_id:08x}"
        
        s = str(node_id).strip()
        if not s:
            return None
        
        if s.startswith('!'):
            return s.lower()
        
        try:
            int(s, 16)
            if len(s) <= 8:
                return f"!{s.zfill(8).lower()}"
        except Exception:
            pass
        
        return None
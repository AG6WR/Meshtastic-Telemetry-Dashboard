"""
Enhanced Data Collection Engine for Meshtastic Monitoring
Integrates with alert system, connection manager, and maintains data compatibility
"""

import time
import json
import os
import csv
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from threading import Thread, Event, Lock

from config_manager import ConfigManager
from connection_manager import ConnectionManager
from alert_system import AlertManager

logger = logging.getLogger(__name__)

class DataCollector:
    """Enhanced data collection with integrated alerting"""
    
    def __init__(self):
        # Load configuration
        self.config_manager = ConfigManager()
        
        # Data settings
        data_config = self.config_manager.get_section('data')
        self.data_file = data_config.get('data_file', 'latest_data.json')
        self.log_directory = data_config.get('log_directory', 'logs')
        self.retain_days = data_config.get('retain_days', 30)
        
        # Initialize components
        meshtastic_config = self.config_manager.get_section('meshtastic')
        self.connection_manager = ConnectionManager(meshtastic_config)
        
        alert_config = self.config_manager.get_section('alerts')
        self.alert_manager = AlertManager(alert_config)
        
        # Data storage
        self.nodes_data = {}
        self.data_lock = Lock()
        self.node_info_cache = {}
        self.last_motion_by_node = {}
        
        # Message tracking
        self.messages_by_node = {}  # {node_id: [message_dicts]}
        self.message_notification_timeout = 15  # seconds for notification display
        self.message_indicator_timeout = 900  # 15 minutes for indicator
        
        # Subscribe to local node detection
        pub.subscribe(self._on_local_node_detected, "meshtastic.local_node.detected")
        
        # Processing thread
        self.processing_thread = None
        self.stop_event = Event()
        
        # Data change callback
        self.on_data_changed = None
        self.on_message_received = None  # Callback for new messages
        
        # Telemetry field mapping
        self.FIELDS = [
            "Temperature", "Humidity", "Pressure", "Voltage", "Current",
            "Battery Level", "Internal Battery Voltage", "Channel Utilization", "Air Utilization (TX)",
            "Uptime", "Ch3 Voltage", "Ch3 Current"
        ]
        
        # External battery voltage-to-percentage mapping (LiFePO4 12V system)
        # Based on resting voltage values for lithium iron phosphate batteries
        self.external_battery_map = [
            (10.0, 0),     # 10.0V = 0%
            (11.0, 5),     # 11.0V = 5%
            (12.0, 10),    # 12.0V = 10%
            (12.4, 15),    # 12.4V = 15%
            (12.8, 20),    # 12.8V = 20%
            (12.85, 25),   # 12.85V = 25%
            (12.9, 30),    # 12.9V = 30%
            (12.95, 35),   # 12.95V = 35%
            (13.0, 40),    # 13.0V = 40-50% (plateau)
            (13.05, 55),   # 13.05V = 55%
            (13.1, 60),    # 13.1V = 60%
            (13.15, 65),   # 13.15V = 65%
            (13.2, 70),    # 13.2V = 70%
            (13.25, 75),   # 13.25V = 75%
            (13.3, 80),    # 13.3V = 80%
            (13.35, 85),   # 13.35V = 85%
            (13.4, 90),    # 13.4V = 90%
            (13.5, 95),    # 13.5V = 95%
            (13.6, 100),   # 13.6V = 100% (resting)
        ]
        
        # Set up callbacks
        self.connection_manager.set_callbacks(
            on_connected=self._on_connected,
            on_disconnected=self._on_disconnected,
            on_packet=self._on_packet_received
        )
        
        logger.info("Data collector initialized")
    
    def set_data_change_callback(self, callback):
        """Set callback to be called when data changes"""
        self.on_data_changed = callback
    
    def _notify_data_changed(self):
        """Notify dashboard that data has changed"""
        if self.on_data_changed:
            try:
                self.on_data_changed()
            except Exception as e:
                logger.error(f"Error in data change callback: {e}")
    
    def start(self):
        """Start data collection system"""
        logger.info("Starting data collection system...")
        
        # Load existing data
        self._load_data()
        
        # Subscribe to text messages
        from pubsub import pub
        pub.subscribe(self._on_text_message_received, "meshtastic.receive.text")
        logger.info("Subscribed to text message events")
        
        # Start connection manager
        self.connection_manager.start()
        
        # Start processing thread
        self.stop_event.clear()
        self.processing_thread = Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        logger.info("Data collection system started")
    
    def _on_local_node_detected(self, node_id, node_name):
        """Handle local node detection event - store in config"""
        logger.info(f"Storing local node info: {node_id} ({node_name})")
        self.config_manager.set('meshtastic.local_node_id', node_id)
        self.config_manager.set('meshtastic.local_node_name', node_name)
        self.config_manager.save_config()
    
    def stop(self):
        """Stop the data collection system"""
        logger.info("Stopping data collection system...")
        
        # Unsubscribe from events
        try:
            pub.unsubscribe(self._on_local_node_detected, "meshtastic.local_node.detected")
        except:
            pass
        
        self.stop_event.set()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        self.connection_manager.stop()
        
        # Save final data
        self._save_all_data()
        
        logger.info("Data collection system stopped")
    
    def _load_existing_data(self):
        """Load existing node data from disk"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.nodes_data = json.load(f)
                    if not isinstance(self.nodes_data, dict):
                        self.nodes_data = {}
                
                # v1.0.8 (2025-11-16): Populate node_info_cache from loaded data
                # This ensures node names are available immediately at startup,
                # before preloaded NODEINFO packets arrive from interface database
                cache_count = 0
                for node_id, node_data in self.nodes_data.items():
                    long_name = node_data.get('Node LongName')
                    short_name = node_data.get('Node ShortName')
                    if long_name and short_name:
                        self.node_info_cache[node_id] = (long_name, short_name)
                        cache_count += 1
                
                logger.info(f"Loaded data for {len(self.nodes_data)} nodes ({cache_count} names cached)")
            except Exception as e:
                logger.error(f"Failed to load existing data: {e}")
                self.nodes_data = {}
        else:
            self.nodes_data = {}
    
    def _save_all_data(self):
        """Save all node data to disk"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.data_file)), exist_ok=True)
            
            # Write to temporary file first
            temp_file = self.data_file + '.tmp'
            with self.data_lock:
                with open(temp_file, 'w') as f:
                    json.dump(self.nodes_data, f, indent=2, sort_keys=True)
            
            # Atomic replace
            os.replace(temp_file, self.data_file)
            logger.debug(f"Saved data for {len(self.nodes_data)} nodes")
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def _processing_loop(self):
        """Background processing loop for alerts and maintenance"""
        last_alert_check = 0
        last_data_save = 0
        last_cleanup = 0
        
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Check alerts periodically
                if current_time - last_alert_check > 60:  # Every minute
                    with self.data_lock:
                        triggered_alerts = self.alert_manager.check_alerts(self.nodes_data)
                        if triggered_alerts:
                            logger.info(f"Triggered {len(triggered_alerts)} alerts")
                    last_alert_check = current_time
                
                # Save data periodically  
                if current_time - last_data_save > 30:  # Every 30 seconds
                    self._save_all_data()
                    last_data_save = current_time
                
                # Cleanup old logs periodically
                if current_time - last_cleanup > 3600:  # Every hour
                    self._cleanup_old_logs()
                    last_cleanup = current_time
                
                # Wait before next iteration
                self.stop_event.wait(10)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                self.stop_event.wait(60)
    
    def _on_connected(self, interface_info):
        """Handle connection established"""
        logger.info(f"Connected to Meshtastic interface: {interface_info}")
    
    def _on_disconnected(self, interface_info):
        """Handle connection lost"""
        logger.warning(f"Disconnected from Meshtastic interface: {interface_info}")
    
    def _on_packet_received(self, packet, interface):
        """Process received Meshtastic packet"""
        try:
            # Extract basic packet info
            node_id = self._normalize_node_id(packet.get('from'))
            if not node_id:
                return
            
            # Extract packet details
            decoded = packet.get('decoded', {})
            portnum = decoded.get('portnum', 'UNKNOWN_APP')
            rx_time = int(packet.get('rxTime', time.time()))
            rx_snr = packet.get('rxSnr')
            hop_limit = packet.get('hopLimit')
            
            # v1.0.8 (2025-11-16): Skip preloaded packets - they shouldn't update Last Heard
            # Preloaded synthetic NODEINFO packets populate node names at startup
            # but should not overwrite historical Last Heard timestamps from JSON.
            is_preloaded = packet.get('_preloaded', False)
            
            # Get node names for logging
            long_name, short_name = self.node_info_cache.get(node_id, ('Unknown Node', 'Unknown'))
            
            # Log all packet arrivals (helps diagnose RF sensitivity issues)
            if not is_preloaded:
                logger.debug(f"PACKET | {short_name}/{long_name} ({node_id}) | Type: {portnum}, SNR: {rx_snr}")
            
            # Handle different packet types
            if portnum == 'NODEINFO_APP':
                self._process_nodeinfo_packet(packet, node_id, rx_time, rx_snr, hop_limit)
            elif portnum == 'TELEMETRY_APP':
                self._process_telemetry_packet(packet, node_id, rx_time, rx_snr, hop_limit)
            elif portnum == 'DETECTION_SENSOR_APP':
                self._process_motion_packet(node_id, rx_time)
            
            # Update basic node info for ALL packet types (including NODEINFO)
            # This allows nodes to show online even if only receiving NODEINFO packets
            # BUT: Skip preloaded synthetic packets - they shouldn't affect online/offline status
            if not is_preloaded:
                self._update_node_basic_info(node_id, rx_time, rx_snr, hop_limit, portnum)
            
            # Log if we see unknown packet types (not already logged above)
            if not is_preloaded and portnum not in ['NODEINFO_APP', 'TELEMETRY_APP', 'DETECTION_SENSOR_APP']:
                long_name, short_name = self.node_info_cache.get(node_id, ('Unknown Node', 'Unknown'))
                logger.debug(f"{portnum} | {short_name}/{long_name} ({node_id}) | Packet received")
            
        except Exception as e:
            logger.error(f"Error processing packet: {e}")
    
    def _process_nodeinfo_packet(self, packet, node_id, rx_time, rx_snr, hop_limit):
        """Process node information packet"""
        try:
            decoded = packet.get('decoded', {})
            
            # Handle preloaded synthetic packets (from connection manager)
            if packet.get('_preloaded'):
                user = decoded.get('user', {})
                long_name = user.get('longName', 'Unknown Node')
                short_name = user.get('shortName', 'Unknown')
            else:
                # Handle regular NODEINFO packets
                nodeinfo = decoded.get('nodeinfo', {})
                if nodeinfo:
                    long_name = nodeinfo.get('longName', 'Unknown Node')
                    short_name = nodeinfo.get('shortName', 'Unknown')
                else:
                    # Also check user field for some packet formats
                    user = decoded.get('user', {})
                    long_name = user.get('longName', 'Unknown Node')
                    short_name = user.get('shortName', 'Unknown')
            
            # Update cache
            old_info = self.node_info_cache.get(node_id, (None, None))
            self.node_info_cache[node_id] = (long_name, short_name)
            
            # Log if this is new or updated info
            if packet.get('_preloaded'):
                logger.debug(f"Preloaded node info for {node_id}: {long_name} ({short_name})")
            elif old_info != (long_name, short_name):
                logger.info(f"NODEINFO | {short_name}/{long_name} ({node_id}) | Names updated")
            
            # Ensure we have data record for this node
            with self.data_lock:
                if node_id not in self.nodes_data:
                    # Create record for new nodes
                    self.nodes_data[node_id] = self._default_node_record(long_name, short_name)
                else:
                    # Update existing record with new names
                    self.nodes_data[node_id]['Node LongName'] = long_name
                    self.nodes_data[node_id]['Node ShortName'] = short_name
                
        except Exception as e:
            logger.error(f"Error processing nodeinfo packet: {e}")
    
    def _process_telemetry_packet(self, packet, node_id, rx_time, rx_snr, hop_limit):
        """Process telemetry data packet"""
        try:
            # Extract telemetry metrics
            metrics, _ = self._extract_metrics(packet)
            if not metrics:
                return
            
            # Get node names
            long_name, short_name = self.node_info_cache.get(node_id, ('Unknown Node', 'Unknown'))
            
            # Log when telemetry data arrives
            logger.info(f"TELEMETRY | {short_name}/{long_name} ({node_id}) | Fields: {list(metrics.keys())}")
            
            
            # Update node data
            with self.data_lock:
                current_node = self.nodes_data.get(node_id, self._default_node_record(long_name, short_name))
                updated_node = self._merge_metrics(current_node, metrics, rx_time)
                
                # Update basic info
                updated_node['Node LongName'] = long_name
                updated_node['Node ShortName'] = short_name
                updated_node['Last Heard'] = rx_time
                updated_node['Last Packet Type'] = 'TELEMETRY_APP'
                
                if rx_snr is not None:
                    updated_node['SNR'] = rx_snr
                    updated_node.setdefault('Field Times', {})['SNR'] = rx_time
                
                if hop_limit is not None:
                    updated_node['Hop Limit'] = hop_limit
                
                # Track when we last received telemetry data
                updated_node['Last Telemetry Time'] = rx_time
                
                # Add motion data if available
                if node_id in self.last_motion_by_node:
                    updated_node['Last Motion'] = self.last_motion_by_node[node_id]
                
                self.nodes_data[node_id] = updated_node
            
            # Log to CSV with message type based on metrics content
            if 'Temperature' in metrics or 'Humidity' in metrics or 'Pressure' in metrics:
                msg_type = 'Environment'
            elif 'Voltage' in metrics or 'Current' in metrics or 'Battery Level' in metrics:
                msg_type = 'Power'
            elif 'Channel Utilization' in metrics or 'Air Utilization (TX)' in metrics:
                msg_type = 'Device'
            else:
                msg_type = 'Telemetry'
            
            self._log_to_csv(node_id, long_name, short_name, rx_time, rx_snr, hop_limit, metrics, msg_type, motion_detected=False)
            
            logger.debug(f"Updated telemetry for {node_id} ({long_name})")
            
        except Exception as e:
            logger.error(f"Error processing telemetry packet: {e}")
    
    def _process_motion_packet(self, node_id, rx_time):
        """Process motion detection packet"""
        self.last_motion_by_node[node_id] = rx_time
        
        # Get node names and log motion event
        long_name, short_name = self.node_info_cache.get(node_id, ('Unknown Node', 'Unknown'))
        logger.info(f"MOTION | {short_name}/{long_name} ({node_id}) | Motion detected")
        
        # Log motion event to CSV
        self._log_to_csv(node_id, long_name, short_name, rx_time, None, None, {}, 'Motion', motion_detected=True)
    
    def _update_node_basic_info(self, node_id, rx_time, rx_snr, hop_limit, portnum):
        """Update basic node information for any packet type"""
        try:
            with self.data_lock:
                if node_id not in self.nodes_data:
                    long_name, short_name = self.node_info_cache.get(node_id, ('Unknown Node', 'Unknown'))
                    self.nodes_data[node_id] = self._default_node_record(long_name, short_name)
                
                node_data = self.nodes_data[node_id]
                node_data['Last Heard'] = rx_time
                node_data['Last Packet Type'] = portnum
                
                # Update Last Motion if we have recent motion data
                if node_id in self.last_motion_by_node:
                    node_data['Last Motion'] = self.last_motion_by_node[node_id]
                
                field_times = node_data.setdefault('Field Times', {})
                field_times['lh'] = rx_time
                
            # Notify dashboard of data change
            self._notify_data_changed()
                
        except Exception as e:
            logger.error(f"Error updating basic node info: {e}")
    
    def _extract_metrics(self, packet: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Extract telemetry metrics from packet"""
        try:
            decoded = packet.get('decoded', {})
            portnum = decoded.get('portnum', 'UNKNOWN_APP')
            telemetry = decoded.get('telemetry', {})
            
            if not isinstance(telemetry, dict):
                return {}, portnum
            
            metrics = {}
            
            # Environment metrics
            env_metrics = telemetry.get('environmentMetrics', {})
            if env_metrics:
                if 'temperature' in env_metrics:
                    metrics['Temperature'] = env_metrics['temperature']
                if 'relativeHumidity' in env_metrics:
                    metrics['Humidity'] = env_metrics['relativeHumidity']
                if 'barometricPressure' in env_metrics:
                    metrics['Pressure'] = env_metrics['barometricPressure']
            
            # Power metrics
            power_metrics = telemetry.get('powerMetrics', {})
            if power_metrics:
                if 'batteryLevel' in power_metrics:
                    metrics['Battery Level'] = power_metrics['batteryLevel']
                if 'voltage' in power_metrics:
                    metrics['Voltage'] = power_metrics['voltage']
                if 'current' in power_metrics:
                    metrics['Current'] = power_metrics['current']
                if 'ch3Voltage' in power_metrics:
                    metrics['Ch3 Voltage'] = power_metrics['ch3Voltage']
                if 'ch3Current' in power_metrics:
                    metrics['Ch3 Current'] = power_metrics['ch3Current']
            
            # Device metrics
            device_metrics = telemetry.get('deviceMetrics', {})
            if device_metrics:
                if 'batteryLevel' in device_metrics:
                    metrics['Battery Level'] = device_metrics['batteryLevel']
                if 'voltage' in device_metrics:
                    # Store both as Voltage (backward compat) and Internal Battery Voltage (new)
                    metrics['Voltage'] = device_metrics['voltage']
                    metrics['Internal Battery Voltage'] = device_metrics['voltage']
                if 'channelUtilization' in device_metrics:
                    metrics['Channel Utilization'] = device_metrics['channelUtilization']
                if 'airUtilTx' in device_metrics:
                    metrics['Air Utilization (TX)'] = device_metrics['airUtilTx']
                if 'uptimeSeconds' in device_metrics:
                    metrics['Uptime'] = device_metrics['uptimeSeconds']
            
            return metrics, portnum
            
        except Exception as e:
            logger.error(f"Error extracting metrics: {e}")
            return {}, 'UNKNOWN_APP'
    
    def _merge_metrics(self, current_node: Dict[str, Any], new_metrics: Dict[str, Any], rx_time: int) -> Dict[str, Any]:
        """Merge new metrics into existing node data"""
        updated_node = current_node.copy()
        field_times = updated_node.setdefault('Field Times', {})
        
        for field, value in new_metrics.items():
            if value is not None:
                updated_node[field] = value
                field_times[field] = rx_time
        
        return updated_node
    
    def _default_node_record(self, long_name: str, short_name: str) -> Dict[str, Any]:
        """Create default node record structure"""
        record = {
            'Node LongName': long_name,
            'Node ShortName': short_name,
            'Last Heard': None,
            'Last Telemetry Time': None,
            'Last Packet Type': None,
            'SNR': None,
            'Hop Limit': None,
            'Last Motion': None,
            'Field Times': {}
        }
        
        # Initialize all telemetry fields
        for field in self.FIELDS:
            record[field] = None
        
        return record
    
    def voltage_to_percentage(self, voltage: float) -> int:
        """
        Convert external battery voltage to percentage using linear interpolation
        
        Args:
            voltage: Battery voltage in volts
            
        Returns:
            Battery percentage (0-100)
        """
        if voltage is None:
            return None
        
        # Sort map by voltage (should already be sorted)
        voltage_map = sorted(self.external_battery_map, key=lambda x: x[0])
        
        # Clamp to min/max values
        if voltage <= voltage_map[0][0]:
            return voltage_map[0][1]
        if voltage >= voltage_map[-1][0]:
            return voltage_map[-1][1]
        
        # Find bracketing points and interpolate
        for i in range(len(voltage_map) - 1):
            v1, p1 = voltage_map[i]
            v2, p2 = voltage_map[i + 1]
            
            if v1 <= voltage <= v2:
                # Linear interpolation
                ratio = (voltage - v1) / (v2 - v1)
                percentage = p1 + ratio * (p2 - p1)
                return int(round(percentage))
        
        return 0  # Fallback
    
    def _normalize_node_id(self, node_id) -> Optional[str]:
        """Normalize node ID to consistent format"""
        if node_id is None:
            return None
        
        if isinstance(node_id, int):
            return f"!{node_id:08x}"
        
        s = str(node_id).strip().lower()
        if not s:
            return None
        
        if s.startswith('!'):
            return s
        
        try:
            # Try to parse as hex
            int(s, 16)
            if len(s) <= 8:
                return f"!{s.zfill(8)}"
        except ValueError:
            pass
        
        return s
    
    def _log_to_csv(self, node_id: str, long_name: str, short_name: str, rx_time: int, snr, hop, metrics: Dict[str, Any], message_type: str = 'Telemetry', motion_detected: bool = False):
        """Log telemetry data to CSV file"""
        try:
            # Calculate file path
            when = datetime.fromtimestamp(rx_time)
            csv_path = self._get_csv_path(node_id, when)
            
            # Check if file is new
            is_new_file = not os.path.exists(csv_path)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Write to CSV
            with open(csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                
                # Write header for new files
                if is_new_file:
                    header = [
                        'iso_time', 'epoch', 'node_id', 'long_name', 'short_name', 'message_type', 'snr', 'hop',
                        'temperature', 'humidity', 'pressure', 'voltage', 'current',
                        'battery_level', 'channel_utilization', 'air_util_tx', 'uptime',
                        'ch3_voltage', 'ch3_current', 'motion_detected'
                    ]
                    writer.writerow(header)
                
                # Write data row
                row = [
                    when.isoformat(timespec='seconds'),
                    rx_time,
                    node_id,
                    long_name or '',
                    short_name or '',
                    message_type,
                    snr if snr is not None else '',
                    hop if hop is not None else '',
                    metrics.get('Temperature', ''),
                    metrics.get('Humidity', ''),
                    metrics.get('Pressure', ''),
                    metrics.get('Voltage', ''),
                    metrics.get('Current', ''),
                    metrics.get('Battery Level', ''),
                    metrics.get('Channel Utilization', ''),
                    metrics.get('Air Utilization (TX)', ''),
                    metrics.get('Uptime', ''),
                    metrics.get('Ch3 Voltage', ''),
                    metrics.get('Ch3 Current', ''),
                    1 if motion_detected else 0
                ]
                writer.writerow(row)
                
        except Exception as e:
            logger.error(f"Failed to log CSV data for {node_id}: {e}")
    
    def _get_csv_path(self, node_id: str, when: datetime) -> str:
        """Get CSV file path for node and date"""
        # Remove leading ! from node ID for directory name
        clean_id = node_id[1:] if node_id.startswith('!') else node_id
        
        # Build path: logs/node_id/year/YYYYMMDD.csv
        year_dir = os.path.join(self.log_directory, clean_id, when.strftime('%Y'))
        filename = when.strftime('%Y%m%d') + '.csv'
        
        return os.path.join(year_dir, filename)
    
    def _cleanup_old_logs(self):
        """Remove old log files based on retention policy"""
        try:
            cutoff_date = datetime.now().date() - timedelta(days=self.retain_days)
            
            if not os.path.exists(self.log_directory):
                return
            
            for node_dir in os.listdir(self.log_directory):
                node_path = os.path.join(self.log_directory, node_dir)
                if not os.path.isdir(node_path):
                    continue
                
                for year_dir in os.listdir(node_path):
                    year_path = os.path.join(node_path, year_dir)
                    if not os.path.isdir(year_path):
                        continue
                    
                    for filename in os.listdir(year_path):
                        if not filename.endswith('.csv'):
                            continue
                        
                        try:
                            # Parse date from filename (YYYYMMDD.csv)
                            date_str = filename[:-4]
                            file_date = datetime.strptime(date_str, '%Y%m%d').date()
                            
                            if file_date < cutoff_date:
                                file_path = os.path.join(year_path, filename)
                                os.remove(file_path)
                                logger.debug(f"Removed old log file: {file_path}")
                                
                        except ValueError:
                            # Skip files that don't match expected format
                            continue
                            
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    def forget_node(self, node_id: str, delete_logs: bool = False) -> bool:
        """
        Remove a node from the system
        
        Args:
            node_id: Node ID to forget (!xxxxxxxx format)
            delete_logs: If True, also delete CSV log directory for this node
            
        Returns:
            True if node was removed, False if node didn't exist or is local node
        """
        # Prevent forgetting the local node
        local_node_id = self.config_manager.get('meshtastic.local_node_id')
        if node_id == local_node_id:
            logger.error(f\"BLOCKED: Attempted to forget local node {node_id} - operation rejected for safety\")
            return False
        
        try:
            with self.data_lock:
                # Remove from nodes_data
                if node_id not in self.nodes_data:
                    logger.warning(f"Cannot forget {node_id}: node not found")
                    return False
                
                node_name = self.nodes_data[node_id].get('Node LongName', node_id)
                del self.nodes_data[node_id]
                
                # Remove from caches
                if node_id in self.node_info_cache:
                    del self.node_info_cache[node_id]
                
                if node_id in self.last_motion_by_node:
                    del self.last_motion_by_node[node_id]
            
            # Remove from alert manager
            if hasattr(self.alert_manager, 'clear_node_alerts'):
                self.alert_manager.clear_node_alerts(node_id)
            
            # Delete CSV logs if requested
            if delete_logs:
                log_dir = os.path.join(self.log_directory, node_id.replace('!', ''))
                if os.path.exists(log_dir):
                    import shutil
                    shutil.rmtree(log_dir)
                    logger.info(f"Deleted log directory for {node_id}")
            
            # Save updated data immediately
            self._save_all_data()
            
            logger.info(f"Forgot node {node_id} ({node_name})")
            return True
            
        except Exception as e:
            logger.error(f"Error forgetting node {node_id}: {e}")
            return False
    
    def get_nodes_data(self) -> Dict[str, Any]:
        """Get current nodes data (thread-safe)"""
        with self.data_lock:
            return self.nodes_data.copy()
    
    def get_node_messages(self, node_id: str, limit: int = 10) -> list:
        """Get recent messages for a node"""
        with self.data_lock:
            messages = self.messages_by_node.get(node_id, [])
            return messages[-limit:] if messages else []
    
    def _on_text_message_received(self, packet, interface=None):
        """Handle received text messages"""
        try:
            # Extract message info
            from_node = packet.get('fromId', 'Unknown')
            to_node = packet.get('toId', 'Unknown')
            decoded = packet.get('decoded', {})
            text = decoded.get('text', '')
            timestamp = time.time()
            
            logger.info(f"TEXT MESSAGE | From: {from_node} | To: {to_node} | Text: {repr(text)}")
            
            # Store message (keyed by sender)
            with self.data_lock:
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
                
                # Update node data with last message time
                if from_node in self.nodes_data:
                    self.nodes_data[from_node]['Last Message Time'] = timestamp
            
            # Notify dashboard
            if self.on_message_received:
                self.on_message_received(message_data)
                
        except Exception as e:
            logger.error(f"Error processing text message: {e}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get connection manager status"""
        return self.connection_manager.get_status()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        with self.data_lock:
            total_nodes = len(self.nodes_data)
            online_nodes = 0
            current_time = time.time()
            
            for node_data in self.nodes_data.values():
                last_heard = node_data.get('Last Heard', 0)
                if current_time - last_heard < 300:  # 5 minutes
                    online_nodes += 1
        
        return {
            'total_nodes': total_nodes,
            'online_nodes': online_nodes,
            'offline_nodes': total_nodes - online_nodes,
            'connection_status': self.get_connection_status()
        }
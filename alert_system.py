"""
Email Alert System for Meshtastic Monitor
Supports SMTP email notifications with configurable alert rules.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Any
import time
import json
import os

logger = logging.getLogger(__name__)

class AlertRule:
    """Represents a single alert rule with cooldown tracking"""
    
    def __init__(self, name: str, enabled: bool = True, threshold: Any = None, 
                 cooldown_minutes: int = 30):
        self.name = name
        self.enabled = enabled
        self.threshold = threshold
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered = {}  # node_id -> timestamp
    
    def can_trigger(self, node_id: str) -> bool:
        """Check if alert can trigger for this node (respects cooldown)"""
        if not self.enabled:
            return False
        
        last_time = self.last_triggered.get(node_id, 0)
        cooldown_seconds = self.cooldown_minutes * 60
        return time.time() - last_time > cooldown_seconds
    
    def trigger(self, node_id: str):
        """Mark alert as triggered for this node"""
        self.last_triggered[node_id] = time.time()

class EmailNotifier:
    """Handles SMTP email notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_server = config.get('smtp_server', 'smtp.mail.me.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.use_tls = config.get('use_tls', True)
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.from_address = config.get('from_address', '')
        self.to_addresses = config.get('to_addresses', [])
    
    def is_configured(self) -> bool:
        """Check if email is properly configured"""
        return bool(self.username and self.password and self.from_address and self.to_addresses)
    
    def send_alert(self, subject: str, message: str, node_data: Optional[Dict] = None, is_test: bool = False) -> bool:
        """Send an email alert
        
        Args:
            subject: Alert subject line
            message: Alert message body
            node_data: Optional dict with node information to include
            is_test: If True, adds a footer indicating this is a user-initiated test
        """
        if not self.is_configured():
            logger.warning("Email not configured, cannot send alert")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_address
            msg['To'] = ', '.join(self.to_addresses)
            msg['Subject'] = f"Meshtastic Alert: {subject}"
            
            # Create email body
            body = f"""
Meshtastic Network Alert
========================

Alert: {subject}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Details:
{message}
"""
            
            # Add node details if provided
            if node_data:
                body += f"""

Node Information:
- ID: {node_data.get('id', 'Unknown')}
- Name: {node_data.get('Node LongName', 'Unknown')}
- Last Heard: {datetime.fromtimestamp(node_data.get('Last Heard', 0)).strftime('%Y-%m-%d %H:%M:%S')}
- Battery: {node_data.get('Battery Level', 'Unknown')}%
- Temperature: {node_data.get('Temperature', 'Unknown')}°C
- Voltage: {node_data.get('Voltage', 'Unknown')}V
"""
            
            body += """

This is an automated alert from your Meshtastic monitoring system.
"""
            
            # Add test footer if this is a user-initiated test
            if is_test:
                body += """
*** This email was sent as a user-initiated test of the alert system ***
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.username, self.password)
                text = msg.as_string()
                server.sendmail(self.from_address, self.to_addresses, text)
            
            logger.info(f"Alert email sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test SMTP connection and credentials"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.username, self.password)
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

class AlertManager:
    """Manages alert rules and email notifications"""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', True)
        self.check_interval = config.get('check_interval_seconds', 60)
        self.last_check = 0
        
        # Startup grace period - don't trigger alerts immediately after launch
        self.startup_grace_minutes = config.get('startup_grace_minutes', 10)
        self.startup_time = time.time()
        
        # Load node-specific overrides
        self.node_overrides = self._load_node_profiles()
        
        # Initialize alert rules
        self.rules = {}
        rules_config = config.get('rules', {})
        
        # Node offline rule
        offline_config = rules_config.get('node_offline', {})
        self.rules['node_offline'] = AlertRule(
            'node_offline',
            offline_config.get('enabled', True),
            offline_config.get('threshold_seconds', 600),
            offline_config.get('cooldown_minutes', 30)
        )
        
        # Low battery rule
        battery_config = rules_config.get('low_battery', {})
        self.rules['low_battery'] = AlertRule(
            'low_battery',
            battery_config.get('enabled', True),
            battery_config.get('threshold_percent', 20),
            battery_config.get('cooldown_minutes', 60)
        )
        
        # High temperature rule
        temp_config = rules_config.get('high_temperature', {})
        self.rules['high_temperature'] = AlertRule(
            'high_temperature',
            temp_config.get('enabled', False),
            temp_config.get('threshold_celsius', 40),
            temp_config.get('cooldown_minutes', 15)
        )
        
        # Low voltage rule
        voltage_config = rules_config.get('low_voltage', {})
        self.rules['low_voltage'] = AlertRule(
            'low_voltage',
            voltage_config.get('enabled', False),
            voltage_config.get('threshold_volts', 3.2),
            voltage_config.get('cooldown_minutes', 30)
        )
        
        # Initialize email notifier
        email_enabled = config.get('email_enabled', False)
        email_config = config.get('email_config', {})
        self.email_notifier = EmailNotifier(email_config) if email_enabled else None
    
    def _load_node_profiles(self) -> Dict[str, Dict]:
        """Load node-specific configuration overrides"""
        try:
            profiles_path = os.path.join('config', 'node_profiles.json')
            if os.path.exists(profiles_path):
                with open(profiles_path, 'r') as f:
                    data = json.load(f)
                    return data.get('node_overrides', {})
        except Exception as e:
            logger.warning(f"Could not load node profiles: {e}")
        return {}
    
    def _get_node_threshold(self, node_id: str, rule_name: str, default_threshold: Any) -> Any:
        """Get threshold for a specific node, with override support"""
        node_profile = self.node_overrides.get(node_id, {})
        overrides = node_profile.get('alert_overrides', {})
        rule_override = overrides.get(rule_name, {})
        
        if rule_name == 'high_temperature':
            return rule_override.get('threshold_celsius', default_threshold)
        elif rule_name == 'low_voltage':
            return rule_override.get('threshold_volts', default_threshold)
        elif rule_name == 'low_battery':
            return rule_override.get('threshold_percent', default_threshold)
        elif rule_name == 'node_offline':
            return rule_override.get('threshold_seconds', default_threshold)
        
        return default_threshold
    
    def should_check(self) -> bool:
        """Check if it's time to run alert checks"""
        return time.time() - self.last_check > self.check_interval
    
    def check_alerts(self, nodes_data: Dict[str, Dict]) -> List[str]:
        """Check all nodes against alert rules, return list of triggered alerts"""
        if not self.enabled or not self.should_check():
            return []

        # Check if we're still in startup grace period
        current_time = time.time()
        if current_time - self.startup_time < (self.startup_grace_minutes * 60):
            # Still in grace period - log but don't email
            grace_remaining = int((self.startup_grace_minutes * 60) - (current_time - self.startup_time))
            logger.info(f"Startup grace period active - {grace_remaining}s remaining before alerts can trigger")
            return []

        self.last_check = time.time()
        triggered_alerts = []
        
        for node_id, node_data in nodes_data.items():
            # Check node offline
            if self.rules['node_offline'].can_trigger(node_id):
                last_heard = node_data.get('Last Heard', 0)
                # Skip if last_heard is None or 0 (node never heard)
                if last_heard and current_time - last_heard > self.rules['node_offline'].threshold:
                    alert_msg = f"Node {node_id} ({node_data.get('Node LongName', 'Unknown')}) has been offline for {int((current_time - last_heard) / 60)} minutes"
                    self._trigger_alert('node_offline', node_id, alert_msg, node_data)
                    triggered_alerts.append(alert_msg)
            
            # Check low battery
            if self.rules['low_battery'].can_trigger(node_id):
                battery_level = node_data.get('Battery Level')
                if battery_level is not None and battery_level < self.rules['low_battery'].threshold:
                    alert_msg = f"Node {node_id} ({node_data.get('Node LongName', 'Unknown')}) has low battery: {battery_level}%"
                    self._trigger_alert('low_battery', node_id, alert_msg, node_data)
                    triggered_alerts.append(alert_msg)
            
            # Check high temperature (with node-specific thresholds)
            if self.rules['high_temperature'].can_trigger(node_id):
                temperature = node_data.get('Temperature')
                temp_threshold = self._get_node_threshold(node_id, 'high_temperature', self.rules['high_temperature'].threshold)
                if temperature is not None and temperature > temp_threshold:
                    node_name = node_data.get('Node LongName', 'Unknown')
                    alert_msg = f"Node {node_id} ({node_name}) has high temperature: {temperature}°C (threshold: {temp_threshold}°C)"
                    self._trigger_alert('high_temperature', node_id, alert_msg, node_data)
                    triggered_alerts.append(alert_msg)
            
            # Check low voltage (with node-specific thresholds)
            if self.rules['low_voltage'].can_trigger(node_id):
                voltage = node_data.get('Voltage')
                voltage_threshold = self._get_node_threshold(node_id, 'low_voltage', self.rules['low_voltage'].threshold)
                if voltage is not None and voltage < voltage_threshold:
                    node_name = node_data.get('Node LongName', 'Unknown')
                    alert_msg = f"Node {node_id} ({node_name}) has low voltage: {voltage}V (threshold: {voltage_threshold}V)"
                    self._trigger_alert('low_voltage', node_id, alert_msg, node_data)
                    triggered_alerts.append(alert_msg)
        
        return triggered_alerts
    
    def _trigger_alert(self, rule_name: str, node_id: str, message: str, node_data: Dict):
        """Trigger an alert for a specific rule and node"""
        self.rules[rule_name].trigger(node_id)
        
        logger.warning(f"Alert triggered: {message}")
        
        # Send email if configured
        if self.email_notifier and self.email_notifier.is_configured():
            subject = f"{rule_name.replace('_', ' ').title()} - {node_data.get('Node LongName', node_id)}"
            self.email_notifier.send_alert(subject, message, node_data)
    
    def test_email(self) -> bool:
        """Test email configuration"""
        success, _ = self.test_email_with_error()
        return success
    
    def test_email_with_error(self) -> tuple:
        """Test email configuration, returning (success, error_message)"""
        if not self.email_notifier:
            return False, "Email notifier not initialized (email_enabled is False)"
        
        if not self.email_notifier.is_configured():
            missing = []
            if not self.email_notifier.username:
                missing.append("username")
            if not self.email_notifier.password:
                missing.append("password")
            if not self.email_notifier.from_address:
                missing.append("from_address")
            if not self.email_notifier.to_addresses:
                missing.append("to_addresses")
            return False, f"Email not properly configured. Missing: {', '.join(missing)}"
        
        # Test connection
        try:
            if not self.email_notifier.test_connection():
                return False, "SMTP connection test failed - check server/port/credentials"
        except Exception as e:
            return False, f"SMTP connection error: {e}"
        
        # Send test email
        try:
            success = self.email_notifier.send_alert(
                "Test Alert", 
                "This is a test alert from your Meshtastic monitoring system. If you receive this, email alerts are working correctly."
            )
            if success:
                return True, None
            else:
                return False, "Failed to send email (unknown error)"
        except Exception as e:
            return False, f"Send error: {e}"
    
    def send_test_alert(self, rule_name: str, node_id: str, node_data: Dict) -> bool:
        """Send a test alert for a specific rule and node (user-initiated)
        
        Args:
            rule_name: Alert rule type (e.g., 'low_battery', 'node_offline')
            node_id: Node ID string
            node_data: Dict containing node information
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.email_notifier or not self.email_notifier.is_configured():
            logger.error("Email not configured for test alert")
            return False
        
        node_name = node_data.get('Node LongName', node_id)
        
        # Build test message based on rule type
        if rule_name == 'node_offline':
            message = f"TEST: Node {node_id} ({node_name}) offline alert"
        elif rule_name == 'low_battery':
            battery = node_data.get('Battery Level', 'N/A')
            message = f"TEST: Node {node_id} ({node_name}) low battery alert (current: {battery}%)"
        elif rule_name == 'high_temperature' or rule_name == 'high_temp':
            temp = node_data.get('Temperature', 'N/A')
            message = f"TEST: Node {node_id} ({node_name}) high temperature alert (current: {temp}°C)"
        elif rule_name == 'low_temperature' or rule_name == 'low_temp':
            temp = node_data.get('Temperature', 'N/A')
            message = f"TEST: Node {node_id} ({node_name}) low temperature alert (current: {temp}°C)"
        elif rule_name == 'low_voltage':
            voltage = node_data.get('Voltage') or node_data.get('Ch3 Voltage', 'N/A')
            message = f"TEST: Node {node_id} ({node_name}) low voltage alert (current: {voltage}V)"
        elif rule_name == 'high_voltage':
            voltage = node_data.get('Voltage') or node_data.get('Ch3 Voltage', 'N/A')
            message = f"TEST: Node {node_id} ({node_name}) high voltage alert (current: {voltage}V)"
        elif rule_name == 'motion':
            message = f"TEST: Node {node_id} ({node_name}) motion detected alert"
        else:
            message = f"TEST: Node {node_id} ({node_name}) {rule_name} alert"
        
        subject = f"TEST - {rule_name.replace('_', ' ').title()} - {node_name}"
        
        return self.email_notifier.send_alert(subject, message, node_data, is_test=True)
    
    def get_recipient_addresses(self) -> List[str]:
        """Get the list of email recipient addresses"""
        if self.email_notifier:
            return self.email_notifier.to_addresses
        return []
"""
Configuration Management for Enhanced Meshtastic Monitor
"""

import json
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration with validation and defaults"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "app_config.json")
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file with fallback defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self.config = self._get_default_config()
        else:
            logger.info("No config file found, using defaults")
            self.config = self._get_default_config()
            self.save_config()
    
    def save_config(self):
        """Save current configuration to file"""
        os.makedirs(self.config_dir, exist_ok=True)
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'alerts.email_enabled')"""
        parts = path.split('.')
        value = self.config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value
    
    def set(self, path: str, value: Any):
        """Set configuration value using dot notation"""
        parts = path.split('.')
        config = self.config
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        config[parts[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.config.get(section, {})
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "meshtastic": {
                "interface": {
                    "type": "tcp",
                    "host": "192.168.1.91",
                    "port": 4403
                },
                "backup_interfaces": [],
                "connection_timeout": 30,
                "retry_interval": 60
            },
            "dashboard": {
                "refresh_rate_ms": 5000,
                "time_format": "DD:HH:MM:SS",
                "stale_row_seconds": 300,
                "recent_field_seconds": 300,
                "stale_field_seconds": 3600,
                "window_geometry": "1520x780"
            },
            "data": {
                "retain_days": 30,
                "data_file": "latest_data.json",
                "log_directory": "logs",
                "backup_enabled": True,
                "backup_interval_hours": 24
            },
            "alerts": {
                "enabled": True,
                "check_interval_seconds": 60,
                "email_enabled": False,
                "email_config": {
                    "smtp_server": "smtp.mail.me.com",
                    "smtp_port": 587,
                    "use_tls": True,
                    "username": "",
                    "password": "",
                    "from_address": "",
                    "to_addresses": []
                },
                "rules": {
                    "node_offline": {
                        "enabled": True,
                        "threshold_seconds": 600,
                        "cooldown_minutes": 30
                    },
                    "low_battery": {
                        "enabled": True,
                        "threshold_percent": 20,
                        "cooldown_minutes": 60
                    },
                    "high_temperature": {
                        "enabled": False,
                        "threshold_celsius": 40,
                        "cooldown_minutes": 15
                    },
                    "low_voltage": {
                        "enabled": False,
                        "threshold_volts": 3.2,
                        "cooldown_minutes": 30
                    }
                }
            }
        }
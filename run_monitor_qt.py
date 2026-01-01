#!/usr/bin/env python3
"""
Qt Meshtastic Monitor - Main Launcher
Launches the complete monitoring system with Qt/PySide6 GUI
"""

import sys
import os
import logging
import threading
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

# Add project directory to Python path
project_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_dir))

from config_manager import ConfigManager
from data_collector import DataCollector
from message_manager import MessageManager
from dashboard_qt import DashboardQt

logger = logging.getLogger(__name__)


def setup_logging():
    """Setup application logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Setup logging to file and console
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('logs/meshtastic_monitor_qt.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main application entry point"""
    setup_logging()
    logger.info("Starting Qt Meshtastic Monitor")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Use Fusion style for consistent cross-platform rendering
    # This avoids native widget variations that cause sizing issues on some Linux systems
    app.setStyle('Fusion')
    
    try:
        # Initialize configuration
        logger.info("Initializing configuration manager...")
        config_manager = ConfigManager()
        
        # Initialize message manager
        logger.info("Initializing message manager...")
        message_manager = MessageManager(config_manager)
        
        # Initialize data collector
        logger.info("Initializing data collector...")
        data_collector = DataCollector()
        
        # Create dashboard with all components
        logger.info("Creating Qt dashboard...")
        dashboard = DashboardQt(
            config_manager=config_manager,
            data_collector=data_collector,
            message_manager=message_manager
        )
        
        # Start data collection in background thread
        def start_collection():
            try:
                logger.info("Starting data collection...")
                data_collector.start()
            except Exception as e:
                logger.error(f"Data collection error: {e}")
        
        collection_thread = threading.Thread(target=start_collection, daemon=True)
        collection_thread.start()
        
        # Show dashboard
        dashboard.show()
        logger.info("Dashboard launched successfully")
        
        # Run application
        exit_code = app.exec()
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        QMessageBox.critical(None, "Startup Error", f"Failed to start application:\n{e}")
        exit_code = 1
    
    logger.info("Application shutdown complete")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

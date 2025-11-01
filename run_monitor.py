#!/usr/bin/env python3
"""
Enhanced Meshtastic Monitor - Main Launcher
Launches the complete monitoring system with GUI
"""

import sys
import os
import logging
from pathlib import Path

# Add Enhanced directory to Python path
enhanced_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(enhanced_dir))

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
            logging.FileHandler('logs/meshtastic_monitor.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger('main')
    
    try:
        logger.info("Starting Enhanced Meshtastic Monitor")
        
        # Import and run dashboard
        from dashboard import main as dashboard_main
        dashboard_main()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")

if __name__ == "__main__":
    main()
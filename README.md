# Enhanced Meshtastic Multi-Node Dashboard

A comprehensive Python-based monitoring system for Meshtastic mesh networks with real-time dashboard, telemetry plotting, and alert capabilities.

![Dashboard Screenshot](docs/dashboard-screenshot.png)

## 🌟 Features

- **Real-time Multi-Node Monitoring** - Track multiple Meshtastic nodes simultaneously
- **CERT ICP Ready** - Professional telemetry dashboard for emergency communications
- **Intelligent Voltage Display** - Handles both main voltage and Ch3 voltage readings
- **Per-Node Alert Configuration** - Customize alert settings for each node individually
- **Dark Theme Interface** - Easy on the eyes for 24/7 monitoring operations
- **Comprehensive Logging** - CSV data logging with daily rotation
- **Email Alerts** - Configurable notifications for offline nodes and critical readings
- **Raspberry Pi Optimized** - Perfect for distributed monitoring stations

## 🏥 Designed For

- **CERT Teams** - Emergency communication monitoring
- **Mesh Network Operators** - Multi-node oversight and management
- **Remote Monitoring** - Raspberry Pi deployment ready
- **24/7 Operations** - Reliable monitoring with professional interface

## 📋 Prerequisites

### System Requirements
- **Python 3.8+** (Python 3.9+ recommended)
- **Operating System**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Memory**: 512MB RAM minimum, 1GB+ recommended
- **Storage**: 100MB for application, additional space for logs

### Hardware Requirements
- **Meshtastic Device** - Any supported Meshtastic node
- **Connection Method**: USB, Bluetooth, or WiFi
- **Display** - Any size (optimized for 7" monitors on Pi)

### Required Software

#### 1. Python 3.8 or Higher
**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- ✅ Check "Add Python to PATH" during installation
- Verify: Open Command Prompt → `python --version`

**macOS:**
```bash
# Using Homebrew (recommended)
brew install python3

# Or download from python.org
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-tkinter
```

**Raspberry Pi:**
```bash
# Usually pre-installed, but update if needed
sudo apt update
sudo apt install python3 python3-pip python3-tkinter git
```

#### 2. Meshtastic Python CLI
```bash
# Install Meshtastic Python library
pip install meshtastic

# Verify installation
python -c "import meshtastic; print('Meshtastic installed successfully')"
```

## 🚀 Installation

### Method 1: Quick Install (Recommended)
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/enhanced-meshtastic-dashboard.git
cd enhanced-meshtastic-dashboard

# Install dependencies
pip install -r requirements.txt

# Copy config template
cp config/app_config_template.json config/app_config.json

# Edit configuration
nano config/app_config.json  # or use your preferred editor

# Run dashboard
python run_monitor.py
```

### Method 2: Raspberry Pi Auto-Install
```bash
git clone https://github.com/YOUR_USERNAME/enhanced-meshtastic-dashboard.git
cd enhanced-meshtastic-dashboard
chmod +x install_pi.sh
./install_pi.sh
```

## ⚙️ Configuration

### Connection Types

#### USB Connection (Most Reliable)
```json
{
  "meshtastic": {
    "interface": {
      "type": "serial",
      "port": "/dev/ttyUSB0"
    }
  }
}
```

#### TCP/WiFi Connection
```json
{
  "meshtastic": {
    "interface": {
      "type": "tcp", 
      "host": "192.168.1.100",
      "port": 4403
    }
  }
}
```

#### Bluetooth Connection
```json
{
  "meshtastic": {
    "interface": {
      "type": "ble",
      "address": "AA:BB:CC:DD:EE:FF"
    }
  }
}
```

### Email Alerts (Optional)
```json
{
  "alerts": {
    "enabled": true,
    "email_enabled": true,
    "email_config": {
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "use_tls": true,
      "username": "your_email@gmail.com", 
      "password": "your_app_password",
      "from_address": "your_email@gmail.com",
      "to_addresses": ["alerts@your_domain.com"]
    }
  }
}
```

## 🍓 Raspberry Pi Deployment

### Hardware Recommendations
- **Raspberry Pi 4B (4GB RAM)** - Best performance
- **7" HDMI Touch Display** - Perfect for monitoring stations
- **High-quality MicroSD (32GB+)** - Class 10 or better
- **Official Pi Power Supply** - Prevent undervoltage issues

### Auto-Start on Boot
```bash
# Install as system service
sudo ./install_service.sh

# Service management
sudo systemctl start meshtastic-dashboard
sudo systemctl status meshtastic-dashboard
sudo systemctl stop meshtastic-dashboard
```

### Multiple Pi Network
Deploy multiple Raspberry Pi monitoring stations:
- **Base Station** - Main operations center
- **Remote Stations** - Strategic monitoring points  
- **Mobile Units** - Vehicle-mounted for field operations
- **Backup Stations** - Redundant monitoring capability

## 📊 Usage

### Dashboard Interface
- **Node Status** - Real-time connection status with color coding
- **Telemetry Data** - Temperature, voltage, SNR, and more
- **Alert Configuration** - Per-node customizable alert settings
- **Data Logging** - Automatic CSV logging with daily rotation
- **Plotting** - Multi-parameter telemetry visualization

### Alert Management
1. Click **"Node Alerts"** button
2. Configure alerts per node:
   - ✅ **Voltage Alerts** - For nodes with voltage sensors
   - ✅ **Temperature Alerts** - Configurable thresholds
   - ✅ **Offline Alerts** - Custom timeout periods
3. Save configuration
4. Alerts automatically respect your settings

## 🔧 Troubleshooting

### Common Issues

**Connection Problems:**
- Verify Meshtastic device is connected and powered
- Check USB cable (data cable, not charge-only)
- Ensure correct port/IP in config file
- Try different connection methods (USB → WiFi → Bluetooth)

**Permission Issues (Linux/Pi):**
```bash
# Add user to dialout group for USB access
sudo usermod -a -G dialout $USER
# Logout and login again
```

**Display Issues (Pi):**
```bash
# Enable desktop auto-login
sudo raspi-config
# → Boot Options → Desktop / CLI → Desktop Autologin
```

### Getting Help
- Check logs in `logs/` directory
- Run with `python run_monitor.py --debug` for verbose output
- Review Meshtastic connection with `meshtastic --info`

## 📝 Development

### Project Structure
```
enhanced-meshtastic-dashboard/
├── run_monitor.py           # Main application launcher
├── dashboard.py             # GUI dashboard interface
├── config_manager.py        # Configuration management
├── connection_manager.py    # Meshtastic interface handling
├── data_collector.py        # Telemetry data collection
├── alert_system.py          # Alert processing and notifications
├── plotter.py              # Data visualization
├── node_alert_config.py     # Per-node alert configuration
├── config/                  # Configuration files
│   └── app_config_template.json
├── logs/                    # Data logging (created at runtime)
└── docs/                    # Documentation
```

### Contributing
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📜 License

MIT License - see LICENSE file for details.

## 🤝 Acknowledgments

- **Meshtastic Project** - For the incredible mesh networking platform
- **CERT Community** - For emergency communication dedication
- **Contributors** - Everyone who helps improve this project

## 📧 Contact

Created for CERT ICP telemetry monitoring operations.

For questions, issues, or contributions, please use GitHub Issues.

# Enhanced Meshtastic Multi-Node Dashboard

A comprehensive Python-based monitoring system for Meshtastic mesh networks with real-time dashboard, telemetry plotting, and alert capabilities.

![Dashboard Screenshot](docs/dashboard-screenshot.png)

## 🌟 Features

- **Real-time Multi-Node Monitoring** - Track multiple Meshtastic nodes simultaneously
- **CERT ICP Ready** - Professional telemetry dashboard for emergency communications
- **Direct Messaging System** - Send and receive text messages between nodes with message center
- **ICP Status Broadcasting** - Automatic status reporting between ICPs/EOCs with help request capability
- **Qt/PySide6 Interface** - Modern, touch-friendly UI optimized for Raspberry Pi touchscreens
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
sudo apt install python3 python3-pip
```

**Raspberry Pi:**
```bash
# Usually pre-installed, but update if needed
sudo apt update
sudo apt install python3 python3-pip git
# Qt6 libraries for PySide6
sudo apt install qt6-base-dev
```

#### 2. Required Python Libraries
```bash
# Install all dependencies from requirements file
pip install -r requirements.txt

# Or install individually:
pip install meshtastic
pip install PySide6>=6.5.0
pip install matplotlib>=3.7.0

# Verify installation
python -c "import meshtastic; print('Meshtastic installed successfully')"
python -c "import PySide6; print('PySide6 installed successfully')"
python -c "import matplotlib; print('Matplotlib installed successfully')"
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

# Run dashboard (Qt version - recommended)
python run_monitor_qt.py

# Or run Tkinter version (legacy)
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
- **Node Status** - Real-time connection status with color coding and ICP status broadcasting
- **Telemetry Data** - Temperature, voltage, SNR, current, humidity, and more
- **Message Center** - Send and receive direct messages between nodes with message history
- **Alert Configuration** - Per-node customizable alert settings
- **Data Logging** - Automatic CSV logging with daily rotation
- **Enhanced Plotting** - Professional telemetry visualization with Qt/matplotlib
- **Touch-Friendly** - Optimized for Raspberry Pi touchscreen operation

### Messaging Features
The dashboard includes a full-featured messaging system:
- **Direct Messages** - Send private messages to individual nodes or broadcast to all
- **Message Center** - View all conversations, mark as read/unread, archive or delete
- **Unread Indicators** - Badge showing unread message count on Messages button
- **Message Notifications** - Visual banner showing recent incoming messages
- **Reply Function** - Quick reply to received messages
- **Message History** - Persistent storage of sent and received messages
- **Recipient Selection** - Easy checkbox-based selection for multiple recipients

### ICP Status Broadcasting
For emergency operations coordination:
- **Automatic Status Reports** - Each ICP broadcasts its operational status every 15 minutes
- **Status Indicators** - Green/Yellow/Red status based on battery, voltage, and temperature
- **Send Help Request** - Manual help request broadcast with blinking indicator
- **Remote Monitoring** - View operational status of all ICPs from any location
- **Status Details** - Reason display shows which parameters are causing warnings
- **Version Tracking** - Dashboard version included in status broadcasts

### Telemetry Plotting Features
The dashboard includes professional Qt/matplotlib-based plotting with:
- **Intelligent Time Axis** - Automatically formats time labels based on data range:
  - < 24 hours: Shows times (00:00, 03:00, 06:00)
  - 1-7 days: Shows dates with times (12/06 00:00, 12/07 00:00)
  - > 7 days: Optimized formatting for longer periods
- **Full Time Range Display** - X-axis shows complete requested time window, making data gaps obvious
- **Major & Minor Gridlines** - Clear visual reference at midnight (major) and 6-hour intervals (minor)
- **Interactive Data Display** - Hover over any data point to see exact values and timestamps
- **Zoom & Pan Tools** - Interactive toolbar for detailed data exploration
- **Export Capability** - Save plots as PNG, PDF, or other formats
- **Dark Theme** - Matches dashboard aesthetics for 24/7 monitoring
- **Multi-Node Overlay** - Compare data from multiple nodes on the same plot

**Available Parameters:**
- Temperature (°C)
- SNR (dB)
- Humidity (%)
- Internal Battery Voltage (V)
- External Battery Voltage (V)
- Current (mA)
- Channel Utilization (%)

**Time Windows:**
- Last 24 hours
- Last 3 days
- Last week (7 days)
- Last 2 weeks (14 days)
- Last month (30 days)
- All available data

### Alert Management
1. Click **"Alerts"** button in main dashboard
2. Configure alerts per node:
   - ✅ **Voltage Alerts** - For nodes with voltage sensors
   - ✅ **Temperature Alerts** - Configurable thresholds
   - ✅ **Motion Alerts** - Detect motion events
   - ✅ **Offline Alerts** - Custom timeout periods
3. Save configuration
4. Alerts automatically respect your settings

### Sending Messages
1. Click **"Messages"** button to open Message Center
2. Click **"Compose"** to create a new message
3. Select recipient(s) using checkboxes or "All Nodes" for broadcast
4. Type your message (max 150 characters)
5. Click **"Send"** to transmit
6. Messages appear in recipient's message list

### Viewing Message History
1. Click **"Messages"** button (shows unread count badge)
2. View all conversations in chronological order
3. Click **"View"** to see message details
4. Use **"Reply"** to respond to a message
5. Mark messages as read/unread or archive them

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
- Run with `python run_monitor_qt.py --debug` for verbose output
- Review Meshtastic connection with `meshtastic --info`

## 📝 Development

### Project Structure
```
meshtastic-telemetry-dashboard/
├── run_monitor_qt.py        # Qt application launcher (recommended)
├── run_monitor.py           # Legacy Tkinter launcher
├── dashboard_qt.py          # Qt/PySide6 dashboard interface
├── card_renderer_qt.py      # Qt card widget renderer
├── message_dialog_qt.py     # Qt message composition dialog
├── message_list_window_qt.py # Qt message center window
├── node_detail_window_qt.py # Qt node detail window
├── plotter_qt.py            # Qt data visualization
├── settings_dialog_qt.py    # Qt settings dialog
├── node_alert_config_qt.py  # Qt per-node alert configuration
├── qt_styles.py             # Centralized Qt styling
├── config_manager.py        # Configuration management
├── connection_manager.py    # Meshtastic interface handling
├── data_collector.py        # Telemetry data collection
├── message_manager.py       # Message storage and retrieval
├── icp_status.py            # ICP status broadcasting/receiving
├── alert_system.py          # Alert processing and notifications
├── config/                  # Configuration files
│   ├── app_config_template.json
│   └── messages.json        # Message storage (created at runtime)
├── logs/                    # Data logging (created at runtime)
├── provisioner/             # Node provisioning tools
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

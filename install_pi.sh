#!/bin/bash
# Enhanced Meshtastic Dashboard - Raspberry Pi Installer

echo "🍓 Installing Enhanced Meshtastic Dashboard on Raspberry Pi"
echo "=================================================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "🔧 Installing dependencies..."
sudo apt install -y python3-pip python3-tkinter git

# Install Python packages
echo "🐍 Installing Python packages..."
pip3 install -r requirements.txt

# Create config from template
echo "⚙️  Setting up configuration..."
if [ ! -f config/app_config.json ]; then
    cp config/app_config_template.json config/app_config.json
    echo "✅ Created config/app_config.json from template"
else
    echo "ℹ️  config/app_config.json already exists"
fi

# Create logs directory
mkdir -p logs

# Set permissions
chmod +x run_monitor.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit config/app_config.json with your Meshtastic connection settings"
echo "2. Connect your Meshtastic device (USB/Bluetooth/WiFi)"  
echo "3. Run: python3 run_monitor.py"
echo ""
echo "🎯 For auto-start on boot, run: sudo ./install_service.sh"
echo ""
#!/bin/bash
# Install systemd service for auto-start on boot

SERVICE_NAME="meshtastic-dashboard"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WORKING_DIR=$(pwd)
USER=$(whoami)

echo "🔧 Installing systemd service for auto-start..."

# Create service file
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=CERT ICP Meshtastic Dashboard
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$WORKING_DIR
ExecStart=/usr/bin/python3 $WORKING_DIR/run_monitor.py
Restart=always
RestartSec=10
Environment=DISPLAY=:0
Environment=PYTHONPATH=$WORKING_DIR

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

echo "✅ Service installed successfully!"
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME" 
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    journalctl -u $SERVICE_NAME -f"
echo ""
echo "🚀 The dashboard will now start automatically on boot!"
echo "   (Reboot to test, or start manually with: sudo systemctl start $SERVICE_NAME)"
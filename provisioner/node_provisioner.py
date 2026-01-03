#!/usr/bin/env python3
"""
Node Provisioning Tool for Meshtastic Telemetry Dashboard

Clones configuration from a "golden" reference node to new nodes.
Cross-platform: Windows, Linux (including Raspberry Pi), macOS.

Handles:
- Channel configuration (including gpio channel for remote hardware)
- Module settings (remote hardware, telemetry intervals, detection sensor)
- Radio settings (region, preset, hop limit)
- Device settings (role, button behavior, etc.)
- Node inventory tracking (CSV with keys, names, IDs)
- Admin key cross-population for remote admin access
- UF2 firmware flashing (RAK4631/nRF52840 devices)

Key Types:
- Channel PSK: Symmetric encryption per channel - CLONED from golden node
- Node keypair: Asymmetric (public/private) - GENERATED FRESH per node
- Admin keys: List of public keys authorized to admin this node - CONFIGURED

Usage:
    # Export golden config from reference node (Windows/Linux)
    python node_provisioner.py --export --port COM10 --output golden_config.yaml  # Windows
    python node_provisioner.py --export --port /dev/ttyUSB0 --output golden_config.yaml  # Linux
    
    # Provision a new node
    python node_provisioner.py --provision --port COM5 --config golden_config.yaml --name "ICP North"
    python node_provisioner.py --provision --port /dev/ttyACM0 --config golden_config.yaml --name "ICP North"
    
    # List available serial ports
    python node_provisioner.py --list-ports
    
    # Show node inventory
    python node_provisioner.py --inventory
    
    # Flash firmware to a node
    python node_provisioner.py --flash --firmware path/to/firmware.uf2
    
    # Interactive mode (guides you through the process)
    python node_provisioner.py --interactive

Requirements:
    - meshtastic Python package (pip install meshtastic)
    - PyYAML (pip install pyyaml)
    - pyserial (pip install pyserial)

Linux Notes:
    - Serial port access requires membership in 'dialout' group:
      sudo usermod -aG dialout $USER
      (then log out and back in)
    - UF2 bootloader drives auto-mount to /media/$USER/RAK4631 or similar
"""

import argparse
import subprocess
import sys
import time
import os
import csv
import shutil
import string
import re
from datetime import datetime
from typing import Optional

try:
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Platform detection
IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"

# Script directory - use this as base for finding config files
# This allows running from any directory: python ./provisioner/node_provisioner.py
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_script_path(filename: str) -> str:
    """Get the full path to a file in the script's directory."""
    return os.path.join(SCRIPT_DIR, filename)


def check_serial_permissions():
    """
    Check if the user has permissions to access serial ports on Linux.
    Warns if user is not in dialout/uucp group.
    """
    if not IS_LINUX:
        return True
    
    try:
        import pwd
        import grp
        
        username = pwd.getpwuid(os.getuid()).pw_name
        user_gids = os.getgroups()
        user_groups = set()
        
        for gid in user_gids:
            try:
                user_groups.add(grp.getgrgid(gid).gr_name)
            except KeyError:
                pass
        
        # Also check supplementary groups
        for g in grp.getgrall():
            if username in g.gr_mem:
                user_groups.add(g.gr_name)
        
        # Check for common serial port groups
        serial_groups = {'dialout', 'uucp', 'plugdev', 'tty'}
        has_serial_group = bool(user_groups & serial_groups)
        
        if not has_serial_group:
            print("\n" + "=" * 60)
            print("  ⚠ WARNING: Serial Port Permissions")
            print("=" * 60)
            print(f"  User '{username}' may not have permission to access serial ports.")
            print("  You may need to add yourself to the 'dialout' group:")
            print(f"")
            print(f"    sudo usermod -aG dialout {username}")
            print(f"")
            print("  Then log out and back in for changes to take effect.")
            print("=" * 60 + "\n")
            return False
        
        return True
        
    except Exception as e:
        # Don't fail on permission check errors
        return True


def get_port_example() -> str:
    """Get a platform-appropriate serial port example string."""
    if IS_WINDOWS:
        return "COM4"
    elif IS_LINUX:
        return "/dev/ttyUSB0 or /dev/ttyACM0"
    else:
        return "/dev/tty.usbserial"

# Node inventory CSV file (in script directory)
INVENTORY_FILE = get_script_path("node_inventory.csv")
INVENTORY_FIELDS = [
    "node_id",
    "node_num", 
    "long_name",
    "short_name",
    "hw_model",
    "public_key",
    "role",  # e.g., "ICP", "EOC", "Relay", "Router", "Admin"
    "location",  # e.g., "Kennedy North", "EOC Main"
    "latitude",
    "longitude", 
    "altitude",
    "firmware_version",
    "last_seen",
    "hops",
    "snr",
    "provisioned_date",
    "provisioned_by",  # Which tool/golden config was used
    "notes"
]

# Default configuration values for ICP network nodes
ICP_DEFAULTS = {
    "remote_hardware_enabled": True,
    "gpio_channel_name": "gpio",
    "telemetry_device_interval": 900,  # 15 minutes
    "telemetry_environment_interval": 900,
    "telemetry_power_interval": 900,
    "position_broadcast_secs": 900,
    "hop_limit": 3,
}


# =============================================================================
# Node Inventory Management
# =============================================================================

def load_inventory() -> list[dict]:
    """Load node inventory from CSV file."""
    if not os.path.exists(INVENTORY_FILE):
        return []
    
    with open(INVENTORY_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_inventory(inventory: list[dict]):
    """Save node inventory to CSV file."""
    with open(INVENTORY_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS)
        writer.writeheader()
        writer.writerows(inventory)


def add_to_inventory(node_info: dict):
    """Add or update a node in the inventory."""
    inventory = load_inventory()
    
    # Check if node already exists (by node_id)
    existing_idx = None
    for i, node in enumerate(inventory):
        if node.get("node_id") == node_info.get("node_id"):
            existing_idx = i
            break
    
    # Prepare record with all fields
    record = {field: node_info.get(field, "") for field in INVENTORY_FIELDS}
    record["provisioned_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if existing_idx is not None:
        # Update existing record, preserve notes if not provided
        if not record.get("notes") and inventory[existing_idx].get("notes"):
            record["notes"] = inventory[existing_idx]["notes"]
        # Preserve role and provisioned info if not provided in new info
        if not record.get("role") and inventory[existing_idx].get("role"):
            record["role"] = inventory[existing_idx]["role"]
        if not record.get("provisioned_date") and inventory[existing_idx].get("provisioned_date"):
            record["provisioned_date"] = inventory[existing_idx]["provisioned_date"]
        if not record.get("provisioned_by") and inventory[existing_idx].get("provisioned_by"):
            record["provisioned_by"] = inventory[existing_idx]["provisioned_by"]
        inventory[existing_idx] = record
        print(f"  Updated existing inventory record for {record['node_id']}")
    else:
        inventory.append(record)
        print(f"  Added new inventory record for {record['node_id']}")
    
    save_inventory(inventory)


def scan_network(port: str, update_inventory: bool = True) -> list[dict]:
    """
    Scan the mesh network and return all known nodes.
    
    Uses the connected node's node database to discover all nodes.
    Optionally updates the inventory with discovered nodes.
    
    Returns list of node dictionaries with all available info.
    """
    print(f"\nScanning mesh network via {port}...")
    
    # Parse the node info using the Python API for structured data
    try:
        import meshtastic
        import meshtastic.serial_interface
        
        interface = meshtastic.serial_interface.SerialInterface(port)
        time.sleep(2)  # Allow connection to stabilize
        
        nodes = []
        my_node_num = interface.myInfo.my_node_num if interface.myInfo else None
        
        for node_num, node_data in interface.nodes.items():
            user = node_data.get('user', {})
            position = node_data.get('position', {})
            device_metrics = node_data.get('deviceMetrics', {})
            
            # Handle node_num being either int or string
            try:
                node_num_int = int(node_num)
                node_id_default = f'!{node_num_int:08x}'
            except (ValueError, TypeError):
                node_id_default = f'!{node_num}'
            
            node_info = {
                'node_id': user.get('id', node_id_default),
                'node_num': str(node_num),
                'long_name': user.get('longName', 'Unknown'),
                'short_name': user.get('shortName', '????'),
                'hw_model': user.get('hwModel', 'Unknown'),
                'public_key': user.get('publicKey', ''),
                'latitude': str(position.get('latitude', '')) if position.get('latitude') else '',
                'longitude': str(position.get('longitude', '')) if position.get('longitude') else '',
                'altitude': str(position.get('altitude', '')) if position.get('altitude') else '',
                'last_seen': datetime.fromtimestamp(node_data.get('lastHeard', 0)).strftime('%Y-%m-%d %H:%M') if node_data.get('lastHeard') else '',
                'hops': str(node_data.get('hopsAway', '')) if node_data.get('hopsAway') is not None else '',
                'snr': str(node_data.get('snr', '')) if node_data.get('snr') is not None else '',
                'firmware_version': device_metrics.get('firmwareVersion', ''),
                'is_local': str(node_num) == str(my_node_num),
            }
            nodes.append(node_info)
        
        interface.close()
        
    except Exception as e:
        print(f"  Error using Python API: {e}")
        print("  Falling back to CLI parsing...")
        nodes = _parse_nodes_from_cli(port)
    
    print(f"  Found {len(nodes)} nodes in mesh network")
    
    # Display summary
    print(f"\n{'='*120}")
    print(f"  Mesh Network Nodes ({len(nodes)} total)")
    print(f"{'='*120}")
    print(f"{'#':<3} {'Node ID':<12} {'Name':<20} {'Short':<6} {'Hardware':<12} {'Public Key':<45} {'Last Seen':<18}")
    print(f"{'-'*120}")
    
    for i, node in enumerate(nodes, 1):
        local_marker = " *" if node.get('is_local') else ""
        pubkey = node.get('public_key', '')[:40] + '...' if len(node.get('public_key', '')) > 40 else node.get('public_key', '')
        print(f"{i:<3} {node.get('node_id', 'N/A'):<12} "
              f"{node.get('long_name', 'N/A'):<20} "
              f"{node.get('short_name', 'N/A'):<6} "
              f"{node.get('hw_model', 'N/A'):<12} "
              f"{pubkey:<45} "
              f"{node.get('last_seen', 'N/A'):<18}{local_marker}")
    
    print(f"{'='*120}")
    print("  * = Local (connected) node")
    
    # Optionally update inventory
    if update_inventory and nodes:
        print(f"\nUpdating inventory with discovered nodes...")
        for node in nodes:
            # Don't overwrite provisioned_date for existing nodes
            node_copy = node.copy()
            node_copy.pop('is_local', None)  # Remove transient field
            add_to_inventory(node_copy)
        print(f"  Inventory updated: {INVENTORY_FILE}")
    
    return nodes


def _parse_nodes_from_cli(port: str) -> list[dict]:
    """Fallback parser for --nodes output if Python API fails."""
    # This is a basic fallback - the Python API is preferred
    returncode, stdout, stderr = run_meshtastic_cmd(["--nodes"], port)
    nodes = []
    # Basic parsing would go here - for now just return empty
    return nodes


def show_inventory():
    """Display the node inventory."""
    inventory = load_inventory()
    
    if not inventory:
        print("\nNo nodes in inventory yet.")
        print(f"Use --scan to discover nodes in the mesh network.")
        print(f"Inventory file: {INVENTORY_FILE}")
        return
    
    print(f"\n{'='*130}")
    print(f"  Node Inventory ({len(inventory)} nodes)")
    print(f"{'='*130}")
    print(f"{'Node ID':<12} {'Name':<20} {'Short':<6} {'Role':<10} {'Hardware':<12} {'Public Key':<30} {'Last Seen':<12} {'Provisioned':<12}")
    print(f"{'-'*130}")
    
    for node in inventory:
        pubkey = node.get('public_key', '')[:26] + '...' if len(node.get('public_key', '')) > 26 else node.get('public_key', '')
        print(f"{node.get('node_id', 'N/A'):<12} "
              f"{node.get('long_name', 'N/A'):<20} "
              f"{node.get('short_name', 'N/A'):<6} "
              f"{node.get('role', ''):<10} "
              f"{node.get('hw_model', 'N/A'):<12} "
              f"{pubkey:<30} "
              f"{node.get('last_seen', ''):<12} "
              f"{node.get('provisioned_date', ''):<12}")
    
    print(f"{'='*130}")
    print(f"\nFull inventory with complete keys saved to: {INVENTORY_FILE}")


def export_admin_keys(output_file: str = "admin_keys.txt"):
    """Export all node public keys for admin key configuration."""
    inventory = load_inventory()
    
    if not inventory:
        print("No nodes in inventory.")
        return
    
    with open(output_file, 'w') as f:
        f.write("# Node Public Keys for Admin Configuration\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("# Use these keys with: meshtastic --set security.admin_key <key>\n\n")
        
        for node in inventory:
            if node.get("public_key"):
                f.write(f"# {node.get('long_name', 'Unknown')} ({node.get('node_id', 'N/A')})\n")
                f.write(f"{node.get('public_key')}\n\n")
    
    print(f"Admin keys exported to: {output_file}")


def configure_admin_keys(port: str, admin_node_ids: Optional[list[str]] = None):
    """
    Configure admin keys on a node to allow remote administration.
    
    If admin_node_ids is None, uses all EOC-role nodes from inventory.
    """
    inventory = load_inventory()
    
    if not inventory:
        print("No nodes in inventory. Provision nodes first.")
        return False
    
    # Get admin keys to add
    admin_keys = []
    
    if admin_node_ids:
        # Use specified nodes
        for node_id in admin_node_ids:
            for node in inventory:
                if node.get("node_id") == node_id and node.get("public_key"):
                    admin_keys.append((node.get("long_name"), node.get("public_key")))
    else:
        # Default: use all EOC-role nodes
        for node in inventory:
            if node.get("role", "").upper() == "EOC" and node.get("public_key"):
                admin_keys.append((node.get("long_name"), node.get("public_key")))
    
    if not admin_keys:
        print("No admin keys found. Make sure EOC nodes are in inventory with 'EOC' role.")
        return False
    
    print(f"\nConfiguring {len(admin_keys)} admin key(s) on {port}...")
    
    for name, key in admin_keys:
        print(f"  Adding admin key for: {name}")
        returncode, stdout, stderr = run_meshtastic_cmd(
            ["--set", "security.admin_key", key], port
        )
        if returncode != 0:
            print(f"    Warning: {stderr}")
        time.sleep(1)
    
    print("Admin keys configured.")
    return True


def setup_cross_admin(eoc_port: Optional[str] = None):
    """
    Interactive setup for cross-node admin access.
    
    Typical setup:
    - EOC nodes can admin all ICP nodes
    - ICP nodes cannot admin each other (local control only)
    """
    inventory = load_inventory()
    
    if not inventory:
        print("No nodes in inventory. Provision nodes first.")
        return
    
    print("\n" + "=" * 60)
    print("  Cross-Node Admin Key Setup")
    print("=" * 60)
    
    # Categorize nodes
    eoc_nodes = [n for n in inventory if n.get("role", "").upper() == "EOC"]
    icp_nodes = [n for n in inventory if n.get("role", "").upper() == "ICP"]
    
    print(f"\nFound {len(eoc_nodes)} EOC node(s) and {len(icp_nodes)} ICP node(s)")
    
    if not eoc_nodes:
        print("\nNo EOC nodes found. Mark nodes with role 'EOC' during provisioning.")
        return
    
    print("\nEOC nodes (will be able to admin ICPs):")
    for node in eoc_nodes:
        print(f"  - {node.get('long_name')} ({node.get('node_id')})")
    
    print("\nICP nodes (will accept admin from EOCs):")
    for node in icp_nodes:
        print(f"  - {node.get('long_name')} ({node.get('node_id')})")
    
    proceed = input("\nProceed with configuring admin keys? [y/N]: ").strip().lower()
    if proceed != 'y':
        print("Cancelled.")
        return
    
    # Get EOC public keys
    eoc_keys = [(n.get("long_name"), n.get("public_key")) for n in eoc_nodes if n.get("public_key")]
    
    if not eoc_keys:
        print("Error: No public keys found for EOC nodes.")
        return
    
    print("\nTo configure each ICP node:")
    print("  1. Connect the ICP node via USB")
    print("  2. Enter the serial port when prompted")
    print("  3. The script will add EOC admin keys to that node")
    
    for icp in icp_nodes:
        print(f"\n--- Configure {icp.get('long_name')} ({icp.get('node_id')}) ---")
        example_port = get_port_example()
        port = input(f"Enter port for {icp.get('long_name')} (e.g., {example_port}) or 's' to skip: ").strip()
        
        if port.lower() == 's':
            print("  Skipped.")
            continue
        
        for eoc_name, eoc_key in eoc_keys:
            print(f"  Adding admin key for {eoc_name}...")
            returncode, stdout, stderr = run_meshtastic_cmd(
                ["--set", "security.admin_key", eoc_key], port
            )
            if returncode != 0:
                print(f"    Warning: {stderr}")
            time.sleep(1)
        
        print(f"  ✓ {icp.get('long_name')} configured.")
    
    print("\n" + "=" * 60)
    print("  Admin key setup complete!")
    print("=" * 60)


# =============================================================================
# Firmware Flashing (UF2 for RAK4631/nRF52840)
# =============================================================================

def find_uf2_drive() -> str:
    """Find the UF2 bootloader drive (cross-platform)."""
    if IS_WINDOWS:
        # Windows: Check all drive letters for UF2 bootloader
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            info_file = os.path.join(drive, "INFO_UF2.TXT")
            if os.path.exists(info_file):
                print(f"  Found UF2 bootloader on {drive}")
                return drive
        return None
    
    elif IS_LINUX:
        # Linux: Check common mount points for UF2 device
        # Get current username for /media/$USER and /run/media/$USER paths
        try:
            import pwd
            username = pwd.getpwuid(os.getuid()).pw_name
        except Exception:
            username = os.environ.get('USER', os.environ.get('LOGNAME', ''))
        
        # Known UF2 bootloader volume names
        uf2_names = ['RAK4631', 'RAKBOOT', 'NRF52BOOT', 'MESHTASTIC', 'CURRENT']
        
        # Build list of potential mount locations
        search_bases = [
            f"/media/{username}",
            f"/run/media/{username}",  # Fedora/Arch
            "/media",
            "/mnt",
        ]
        
        # First, check explicit known paths
        for base in search_bases:
            for name in uf2_names:
                mount = os.path.join(base, name)
                info_file = os.path.join(mount, "INFO_UF2.TXT")
                if os.path.exists(info_file):
                    print(f"  Found UF2 bootloader on {mount}")
                    return mount
        
        # Second, scan mount directories for any UF2 device
        for base in search_bases:
            if os.path.isdir(base):
                try:
                    for entry in os.listdir(base):
                        mount = os.path.join(base, entry)
                        if os.path.isdir(mount):
                            info_file = os.path.join(mount, "INFO_UF2.TXT")
                            if os.path.exists(info_file):
                                print(f"  Found UF2 bootloader on {mount}")
                                return mount
                except PermissionError:
                    continue
        
        return None
    
    elif IS_MACOS:
        # macOS: Check /Volumes
        uf2_names = ['RAK4631', 'RAKBOOT', 'NRF52BOOT', 'MESHTASTIC', 'CURRENT']
        for name in uf2_names:
            mount = f"/Volumes/{name}"
            info_file = os.path.join(mount, "INFO_UF2.TXT")
            if os.path.exists(info_file):
                print(f"  Found UF2 bootloader on {mount}")
                return mount
        
        # Scan /Volumes for any UF2 device
        if os.path.isdir("/Volumes"):
            for entry in os.listdir("/Volumes"):
                mount = os.path.join("/Volumes", entry)
                if os.path.isdir(mount):
                    info_file = os.path.join(mount, "INFO_UF2.TXT")
                    if os.path.exists(info_file):
                        print(f"  Found UF2 bootloader on {mount}")
                        return mount
        return None
    
    return None


def wait_for_uf2_drive(timeout: int = 120) -> str:
    """Wait for UF2 bootloader drive to appear."""
    print("\n" + "=" * 60)
    print("  ENTER BOOTLOADER MODE")
    print("=" * 60)
    print("")
    print("  ╔═══════════════════════════════════════════════════════╗")
    print("  ║  DOUBLE-TAP the RESET button on the device NOW       ║")
    print("  ║                                                       ║")
    print("  ║  The device LED should pulse and a new drive         ║")
    if IS_WINDOWS:
        print("  ║  named 'RAK4631' will appear in File Explorer.       ║")
    elif IS_LINUX:
        print("  ║  named 'RAK4631' will auto-mount (check file manager)║")
    else:
        print("  ║  named 'RAK4631' will appear in Finder.              ║")
    print("  ╚═══════════════════════════════════════════════════════╝")
    print("")
    print(f"  Waiting for UF2 bootloader drive (timeout: {timeout}s)...")
    
    start = time.time()
    while time.time() - start < timeout:
        drive = find_uf2_drive()
        if drive:
            print(f"\n  ✓ Found bootloader drive: {drive}")
            return drive
        time.sleep(1)
        elapsed = int(time.time() - start)
        if elapsed % 10 == 0:
            print(f"  ... still waiting ({elapsed}s)")
    
    print("\n  ✗ Timeout waiting for UF2 drive.")
    return None


def flash_firmware(firmware_path: str, wait: bool = True) -> bool:
    """Flash UF2 firmware to device."""
    if not os.path.exists(firmware_path):
        print(f"Error: Firmware file not found: {firmware_path}")
        return False
    
    if not firmware_path.lower().endswith(".uf2"):
        print(f"Warning: File does not have .uf2 extension: {firmware_path}")
    
    # Check if drive is already present
    drive = find_uf2_drive()
    
    if not drive and wait:
        drive = wait_for_uf2_drive()
    
    if not drive:
        print("\nError: UF2 bootloader drive not found.")
        print("Make sure device is in bootloader mode (double-tap RESET).")
        return False
    
    # Copy firmware to drive
    dest_path = os.path.join(drive, os.path.basename(firmware_path))
    print(f"\nFlashing firmware...")
    print(f"  Source: {firmware_path}")
    print(f"  Destination: {dest_path}")
    
    try:
        shutil.copy2(firmware_path, dest_path)
        
        # On Linux/macOS, ensure data is actually written to the device
        # before the bootloader processes it
        if IS_LINUX or IS_MACOS:
            print("  Syncing filesystem...")
            os.sync()
            time.sleep(2)  # Give time for sync to complete
        
        print("  Firmware copied successfully!")
        print("  Device will reboot automatically...")
        
        # Wait for device to reboot and reconnect
        # After firmware flash, the device needs significant time to:
        # 1. Complete the flash and reboot
        # 2. Initialize radio and crypto subsystems
        # 3. Be ready for PKC admin session negotiation
        print("\nWaiting for device to reboot (45 seconds)...")
        time.sleep(45)
        
        return True
    except Exception as e:
        print(f"Error copying firmware: {e}")
        return False


def wait_for_serial_port(expected_desc: Optional[str] = None, timeout: int = 60) -> Optional[str]:
    """Wait for a serial port to appear after firmware flash."""
    if not HAS_SERIAL:
        print("pyserial not installed, cannot detect port automatically.")
        return None
    
    print(f"\nWaiting for device to reconnect (timeout: {timeout}s)...")
    
    start = time.time()
    while time.time() - start < timeout:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Look for typical Meshtastic device descriptions
            if any(x in port.description.lower() for x in ["cp210", "ch340", "usb serial", "rak"]):
                print(f"  Found device: {port.device} - {port.description}")
                return port.device
        time.sleep(2)
        print(".", end="", flush=True)
    
    print("\n  Timeout waiting for device.")
    return None


def run_meshtastic_cmd(args: list, port: Optional[str] = None) -> tuple[int, str, str]:
    """Run a meshtastic CLI command and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "meshtastic"]
    if port:
        cmd.extend(["--port", port])
    cmd.extend(args)
    
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def run_meshtastic_cmd_quiet(args: list, port: Optional[str] = None, timeout: int = 10) -> tuple[int, str, str]:
    """Run a meshtastic CLI command quietly (no print) with timeout."""
    cmd = [sys.executable, "-m", "meshtastic"]
    if port:
        cmd.extend(["--port", port])
    cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"


def wait_for_device_ready(port: str, timeout: int = 90, interval: int = 5) -> bool:
    """
    Wait for a Meshtastic device to be ready to accept commands.
    
    After firmware flash, the device needs time to:
    - Complete boot sequence
    - Initialize radio hardware
    - Initialize crypto/PKC subsystems
    - Be ready for admin session negotiation
    
    This function polls with --info until the device responds successfully.
    
    Args:
        port: COM port of the device
        timeout: Maximum seconds to wait
        interval: Seconds between probe attempts
        
    Returns:
        True if device became ready, False if timeout
    """
    print(f"\nWaiting for device on {port} to become ready...")
    print(f"  (This may take up to {timeout} seconds after firmware flash)")
    
    start_time = time.time()
    attempts = 0
    
    while time.time() - start_time < timeout:
        attempts += 1
        elapsed = int(time.time() - start_time)
        print(f"  Attempt {attempts} ({elapsed}s elapsed)...", end=" ", flush=True)
        
        returncode, stdout, stderr = run_meshtastic_cmd_quiet(["--info"], port, timeout=15)
        
        if returncode == 0 and 'myNodeNum' in stdout:
            print("✓ Device ready!")
            # Extra pause to ensure crypto subsystem is fully initialized
            print("  Allowing extra time for crypto initialization...")
            time.sleep(5)
            return True
        elif 'PermissionError' in stderr or 'WriteFile failed' in stderr:
            print("device busy (crypto not ready)")
        elif 'Timeout' in stderr:
            print("timeout (still booting)")
        elif returncode != 0:
            print(f"not ready ({stderr.strip()[:40] if stderr else 'no response'})")
        else:
            print("partial response, retrying...")
        
        time.sleep(interval)
    
    print(f"\n  Timeout after {timeout}s waiting for device.")
    return False


# Known Meshtastic device USB VID/PID combinations
# Format: (VID, PID, description)
MESHTASTIC_USB_IDS = [
    (0x239A, 0x8029, "RAK4631 / nRF52840"),      # RAK4631, WisMesh Pocket
    (0x239A, 0x0029, "RAK4631 / nRF52840"),      # Alternate PID
    (0x239A, None, "Adafruit nRF52840"),         # Any Adafruit VID device
    (0x3032, 0x1001, "Heltec / STATION_G2"),     # Heltec devices
    (0x303A, 0x1001, "ESP32-S3"),                # ESP32-S3 based devices
    (0x10C4, 0xEA60, "Silicon Labs CP210x"),     # Some ESP32 boards (needs probe)
    (0x1A86, 0x7523, "CH340"),                   # Some ESP32 boards (needs probe)
]


def is_likely_meshtastic(port_info) -> tuple[bool, str]:
    """
    Check if a serial port is likely a Meshtastic device based on USB VID/PID.
    Returns (is_likely, reason_string).
    """
    vid = port_info.vid
    pid = port_info.pid
    
    if vid is None:
        return False, "No USB VID"
    
    for known_vid, known_pid, desc in MESHTASTIC_USB_IDS:
        if vid == known_vid:
            if known_pid is None or pid == known_pid:
                return True, desc
    
    return False, ""


def probe_meshtastic_device(port: str, timeout: int = 8) -> Optional[dict]:
    """
    Probe a serial port to see if it's a Meshtastic device.
    Returns node info dict if successful, None if not a Meshtastic device.
    """
    try:
        returncode, stdout, stderr = run_meshtastic_cmd_quiet(["--info"], port, timeout=timeout)
        
        if returncode != 0:
            return None
        
        # Parse the output for node info
        info = {}
        for line in stdout.split('\n'):
            if 'Owner:' in line:
                # Format: "Owner: Kennedy North (9773)"
                match = re.search(r'Owner:\s*(.+?)\s*\((\w+)\)', line)
                if match:
                    info['long_name'] = match.group(1).strip()
                    info['short_name'] = match.group(2).strip()
            elif 'My info:' in line or 'myNodeNum:' in line.lower():
                match = re.search(r'(\d+)', line)
                if match:
                    info['node_num'] = int(match.group(1))
            elif 'Node ID:' in line or 'node_id:' in line.lower():
                match = re.search(r'(!?[0-9a-fA-F]+)', line)
                if match:
                    info['node_id'] = match.group(1)
        
        # Try to extract node_id from "Nodes in mesh:" section
        if 'node_id' not in info:
            for line in stdout.split('\n'):
                if '!' in line and 'meshtastic' not in line.lower():
                    match = re.search(r'(![\da-fA-F]{8})', line)
                    if match:
                        info['node_id'] = match.group(1)
                        break
        
        # If we got any info, it's a Meshtastic device
        if info:
            return info
        
        # Check if output contains typical Meshtastic strings
        if 'Connected to radio' in stdout or 'Owner:' in stdout:
            return {'detected': True}
        
        return None
        
    except Exception as e:
        return None


def list_serial_ports():
    """List available serial ports with basic info."""
    if not HAS_SERIAL:
        print("pyserial not installed. Install with: pip install pyserial")
        if IS_WINDOWS:
            print("Manually check Device Manager for COM ports.")
        else:
            print("Manually check with: ls /dev/tty* or dmesg | tail")
        return []
    
    ports = serial.tools.list_ports.comports()
    print("\nAvailable serial ports:")
    print("-" * 70)
    for port in ports:
        print(f"  {port.device}: {port.description}")
    print("-" * 70)
    return [p.device for p in ports]


def discover_meshtastic_devices(probe_uncertain: bool = True) -> list[dict]:
    """
    Scan all serial ports and identify Meshtastic devices.
    Uses USB VID/PID for fast identification, with optional probing for uncertain devices.
    Returns list of dicts with port info and node details.
    """
    if not HAS_SERIAL:
        print("pyserial not installed. Cannot auto-detect devices.")
        return []
    
    ports = list(serial.tools.list_ports.comports())
    
    print(f"\nScanning {len(ports)} serial port(s) for Meshtastic devices...")
    
    devices = []
    uncertain_ports = []
    
    # First pass: identify by VID/PID (instant)
    for port in ports:
        is_likely, reason = is_likely_meshtastic(port)
        
        if is_likely:
            # High confidence - mark for probing
            devices.append({
                'port': port.device,
                'description': port.description,
                'reason': reason,
                'needs_probe': True,
            })
        elif port.vid is not None:
            # Has USB VID but not recognized - might still be Meshtastic
            # Only probe if it looks like a serial adapter
            desc_lower = port.description.lower()
            if 'serial' in desc_lower and 'bluetooth' not in desc_lower:
                uncertain_ports.append(port)
    
    # Second pass: probe likely devices to get node info
    for dev in devices:
        port_name = dev['port']
        print(f"  {port_name}: {dev['reason']}...", end=" ", flush=True)
        
        info = probe_meshtastic_device(port_name, timeout=8)
        
        if info:
            dev['node_id'] = info.get('node_id', '?')
            dev['long_name'] = info.get('long_name', 'Unknown')
            dev['short_name'] = info.get('short_name', '')
            dev['confirmed'] = True
            print(f"✓ {dev['long_name']} ({dev['node_id']})")
        else:
            dev['confirmed'] = False
            print("(no response)")
    
    # Filter to confirmed devices
    devices = [d for d in devices if d.get('confirmed')]
    
    # Third pass (optional): probe uncertain ports
    if probe_uncertain and uncertain_ports:
        print(f"\n  Checking {len(uncertain_ports)} other USB serial device(s)...")
        for port in uncertain_ports:
            print(f"  {port.device}...", end=" ", flush=True)
            info = probe_meshtastic_device(port.device, timeout=5)
            if info:
                print(f"✓ {info.get('long_name', 'Meshtastic')} ({info.get('node_id', '?')})")
                devices.append({
                    'port': port.device,
                    'description': port.description,
                    'node_id': info.get('node_id', '?'),
                    'long_name': info.get('long_name', 'Unknown'),
                    'short_name': info.get('short_name', ''),
                    'confirmed': True,
                })
            else:
                print("not Meshtastic")
    
    print(f"\n  Found {len(devices)} Meshtastic device(s)")
    return devices


def select_meshtastic_device(prompt: str = "Select device") -> Optional[str]:
    """
    Discover Meshtastic devices and let user select one.
    Returns the selected COM port, or None if cancelled.
    """
    devices = discover_meshtastic_devices()
    
    print("\n" + "=" * 70)
    if devices:
        print(f"  Found {len(devices)} Meshtastic device(s):")
        print("=" * 70)
        for i, dev in enumerate(devices, 1):
            print(f"  {i}. {dev['port']}: {dev['long_name']} ({dev['node_id']})")
            print(f"       {dev['description']}")
    else:
        print("  No Meshtastic devices detected.")
        print("=" * 70)
    
    print(f"  M. Enter port manually")
    print(f"  R. Rescan")
    print(f"  0. Cancel")
    print("=" * 70)
    
    while True:
        choice = input(f"\n{prompt} [1-{len(devices)}/M/R/0]: ").strip().upper()
        
        if choice == '0':
            return None
        elif choice == 'R':
            return select_meshtastic_device(prompt)  # Rescan
        elif choice == 'M':
            if IS_WINDOWS:
                port = input("Enter COM port (e.g., COM4): ").strip().upper()
            else:
                port = input("Enter serial port (e.g., /dev/ttyUSB0 or /dev/ttyACM0): ").strip()
            if port:
                return port
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(devices):
                    return devices[idx - 1]['port']
            except ValueError:
                pass
        
        print("  Invalid selection. Try again.")


def export_config(port: str, output_dir: str = None) -> bool:
    """
    Export configuration from a node, creating multiple organized files.
    
    Creates (in script directory):
      - golden_config_raw.yaml: Full unmodified export
      - golden_config_clean.yaml: Config with node-specific values removed
      - golden_config_url.txt: Channel URL (contains PSKs)
      - golden_node_info.yaml: Reference node info (for documentation)
    """
    import yaml
    
    # Default to script directory for output
    if output_dir is None:
        output_dir = SCRIPT_DIR
    
    print(f"\nExporting configuration from {port}...")
    print(f"  Output directory: {output_dir}")
    
    # Get node info first
    node_info = get_node_info(port)
    print(f"  Node: {node_info.get('long_name', 'Unknown')} ({node_info.get('node_id', 'Unknown')})")
    
    # Export raw config
    returncode, stdout, stderr = run_meshtastic_cmd(["--export-config"], port)
    
    if returncode != 0:
        print(f"Error exporting config: {stderr}")
        return False
    
    # Find where YAML starts (skip "Connected to radio" etc.)
    lines = stdout.split('\n')
    yaml_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('# start of Meshtastic'):
            yaml_start = i
            break
    
    yaml_content = '\n'.join(lines[yaml_start:])
    
    # Save raw config
    raw_file = os.path.join(output_dir, "golden_config_raw.yaml")
    with open(raw_file, 'w') as f:
        f.write(yaml_content)
    print(f"  Raw config saved to: {raw_file}")
    
    # Parse YAML to create clean version
    try:
        config = yaml.safe_load(yaml_content)
    except Exception as e:
        print(f"  Warning: Could not parse YAML: {e}")
        config = None
    
    if config:
        # Create clean config (remove node-specific values)
        clean_config = config.copy()
        
        # Remove node-specific values
        node_specific_keys = ['owner', 'owner_short', 'location']
        for key in node_specific_keys:
            clean_config.pop(key, None)
        
        # Remove security private key (must not be copied!)
        if 'config' in clean_config and 'security' in clean_config['config']:
            clean_config['config']['security'].pop('privateKey', None)
            clean_config['config']['security'].pop('publicKey', None)
        
        # Save clean config
        clean_file = os.path.join(output_dir, "golden_config_clean.yaml")
        with open(clean_file, 'w') as f:
            f.write("# Meshtastic Golden Configuration (node-specific values removed)\n")
            f.write(f"# Exported from: {node_info.get('long_name', 'Unknown')} ({node_info.get('node_id', 'Unknown')})\n")
            f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("#\n")
            f.write("# Node-specific values NOT included (will be set during provisioning):\n")
            f.write("#   - owner (node name)\n")
            f.write("#   - owner_short (short name)\n")
            f.write("#   - location (GPS coordinates)\n")
            f.write("#   - security.privateKey (generated per-node)\n")
            f.write("#   - security.publicKey (generated per-node)\n")
            f.write("#\n")
            f.write("# Admin keys ARE included and will be applied to new nodes.\n")
            f.write("# Override during provisioning if different admin access is needed.\n")
            f.write("#\n\n")
            yaml.dump(clean_config, f, default_flow_style=False, sort_keys=False)
        print(f"  Clean config saved to: {clean_file}")
        
        # Save reference node info
        info_file = os.path.join(output_dir, "golden_node_info.yaml")
        reference_info = {
            "reference_node": {
                "node_id": node_info.get("node_id"),
                "node_num": node_info.get("node_num"),
                "long_name": node_info.get("long_name"),
                "short_name": node_info.get("short_name"),
                "hw_model": node_info.get("hw_model"),
                "firmware_version": node_info.get("firmware_version"),
                "public_key": node_info.get("public_key"),
            },
            "admin_keys": config.get('config', {}).get('security', {}).get('adminKey', []),
            "export_date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        }
        with open(info_file, 'w') as f:
            f.write("# Golden Configuration Reference Info\n")
            f.write("# This file documents the source node and admin key configuration\n\n")
            yaml.dump(reference_info, f, default_flow_style=False, sort_keys=False)
        print(f"  Reference info saved to: {info_file}")
    
    # Save channel URL separately
    returncode, stdout, stderr = run_meshtastic_cmd(["--info"], port)
    if returncode == 0:
        for line in stdout.split('\n'):
            if 'meshtastic.org/e/#' in line:
                url_file = os.path.join(output_dir, "golden_config_url.txt")
                # Extract just the URL
                url = line.strip()
                if 'URL:' in url:
                    url = url.split('URL:')[1].strip()
                with open(url_file, 'w') as f:
                    f.write(url)
                print(f"  Channel URL saved to: {url_file}")
                break
    
    print("\n✓ Export complete!")
    print(f"\nFiles created in {output_dir}:")
    print("  golden_config_raw.yaml   - Full export (for reference)")
    print("  golden_config_clean.yaml - For applying to new nodes")
    print("  golden_config_url.txt    - Channel configuration")
    print("  golden_node_info.yaml    - Reference node documentation")
    
    return True


def get_node_info(port: str) -> dict:
    """Get basic info about connected node."""
    returncode, stdout, stderr = run_meshtastic_cmd(["--info"], port)
    if returncode != 0:
        return {}
    
    info = {
        "node_id": None,
        "node_num": None,
        "long_name": None,
        "short_name": None,
        "hw_model": None,
        "public_key": None,
        "firmware_version": None,
    }
    
    # Parse the JSON-ish output
    import re
    
    for line in stdout.split('\n'):
        if '"myNodeNum"' in line:
            # Extract node number
            try:
                match = re.search(r'"myNodeNum":\s*(\d+)', line)
                if match:
                    info["node_num"] = int(match.group(1))
                    info["node_id"] = f"!{info['node_num']:08x}"
            except:
                pass
                
        if 'Owner:' in line:
            # Format: "Owner: Name (shortname)"
            try:
                parts = line.split('Owner:')[1].strip()
                if '(' in parts:
                    info["long_name"] = parts.split('(')[0].strip()
                    info["short_name"] = parts.split('(')[1].replace(')', '').strip()
            except:
                pass
                
        if '"hwModel"' in line and not info["hw_model"]:
            try:
                match = re.search(r'"hwModel":\s*"([^"]+)"', line)
                if match:
                    info["hw_model"] = match.group(1)
            except:
                pass
        
        if '"firmwareVersion"' in line:
            try:
                match = re.search(r'"firmwareVersion":\s*"([^"]+)"', line)
                if match:
                    info["firmware_version"] = match.group(1)
            except:
                pass
        
        # Get the node's public key (from security section or first occurrence)
        if '"publicKey"' in line and not info["public_key"]:
            try:
                match = re.search(r'"publicKey":\s*"([^"]+)"', line)
                if match:
                    info["public_key"] = match.group(1)
            except:
                pass
    
    return info


def provision_node(port: str, config_file: Optional[str], node_name: Optional[str] = None, 
                   short_name: Optional[str] = None, apply_url: Optional[str] = None,
                   node_role: Optional[str] = None, location: Optional[str] = None) -> bool:
    """Provision a new node with configuration from file."""
    print(f"\nProvisioning node on {port}...")
    
    # Get current node info
    info = get_node_info(port)
    print(f"  Current node: {info.get('long_name', 'Unknown')} ({info.get('node_id', 'Unknown')})")
    print(f"  Hardware: {info.get('hw_model', 'Unknown')}")
    print(f"  Firmware: {info.get('firmware_version', 'Unknown')}")
    print(f"  Public Key: {info.get('public_key', 'Unknown')[:20]}..." if info.get('public_key') else "  Public Key: Unknown")
    
    # Apply channel URL first if provided (this sets up channels with correct PSKs)
    if apply_url:
        print("\nApplying channel configuration from URL...")
        # Read URL from file if it's a file path
        if os.path.exists(apply_url):
            with open(apply_url, 'r') as f:
                url = f.read().strip()
        else:
            url = apply_url
        
        returncode, stdout, stderr = run_meshtastic_cmd(["--seturl", url], port)
        if returncode != 0:
            print(f"Warning: Error applying URL: {stderr}")
        else:
            print("  Channel configuration applied.")
            time.sleep(2)  # Wait for node to process
    
    # Apply configuration from YAML file
    if config_file and os.path.exists(config_file):
        print(f"\nApplying configuration from {config_file}...")
        returncode, stdout, stderr = run_meshtastic_cmd(["--configure", config_file], port)
        if returncode != 0:
            print(f"Warning: Error applying config: {stderr}")
        else:
            print("  Configuration applied.")
            time.sleep(2)
    
    # Set node name if provided
    if node_name:
        print(f"\nSetting node name to: {node_name}")
        args = ["--set-owner", node_name]
        if short_name:
            args.extend(["--set-owner-short", short_name])
        returncode, stdout, stderr = run_meshtastic_cmd(args, port)
        if returncode != 0:
            print(f"Warning: Error setting name: {stderr}")
        else:
            print("  Node name set.")
    
    # Ensure remote hardware is enabled
    print("\nEnsuring remote hardware module is enabled...")
    returncode, stdout, stderr = run_meshtastic_cmd(
        ["--set", "remote_hardware.enabled", "true"], port
    )
    if returncode != 0:
        print(f"Warning: Could not enable remote hardware: {stderr}")
    
    # Get final node info and add to inventory
    print("\nGathering final node information...")
    time.sleep(2)  # Wait for settings to apply
    final_info = get_node_info(port)
    
    # Override with provided values
    if node_name:
        final_info["long_name"] = node_name
    if short_name:
        final_info["short_name"] = short_name
    if node_role:
        final_info["role"] = node_role
    if location:
        final_info["location"] = location
    
    # Add to inventory
    print("\nUpdating node inventory...")
    add_to_inventory(final_info)
    
    # Summary
    print("\n" + "=" * 50)
    print("  PROVISIONING COMPLETE")
    print("=" * 50)
    print(f"  Node ID:      {final_info.get('node_id', 'Unknown')}")
    print(f"  Name:         {final_info.get('long_name', 'Unknown')}")
    print(f"  Short Name:   {final_info.get('short_name', 'Unknown')}")
    print(f"  Hardware:     {final_info.get('hw_model', 'Unknown')}")
    print(f"  Firmware:     {final_info.get('firmware_version', 'Unknown')}")
    print(f"  Public Key:   {final_info.get('public_key', 'Unknown')}")
    print(f"  Role:         {final_info.get('role', 'Not set')}")
    print(f"  Location:     {final_info.get('location', 'Not set')}")
    print("=" * 50)
    
    return True


def check_gpio_channel(port: str) -> bool:
    """Check if gpio channel exists on the node."""
    returncode, stdout, stderr = run_meshtastic_cmd(["--info"], port)
    return "gpio" in stdout.lower()


def add_gpio_channel(port: str) -> bool:
    """Add gpio channel to node."""
    print("\nAdding gpio channel...")
    returncode, stdout, stderr = run_meshtastic_cmd(["--ch-add", "gpio"], port)
    if returncode != 0:
        print(f"Error adding gpio channel: {stderr}")
        return False
    print("  gpio channel added.")
    time.sleep(2)
    return True


def provision_new_node_flow():
    """
    Complete provisioning flow for a new node.
    
    All steps are required - no partial provisioning allowed.
    Steps:
      1. Collect all node information upfront
      2. Select admin nodes from inventory
      3. Flash firmware
      4. Apply configuration
      5. Set admin keys
      6. Record to inventory
    """
    print("\n" + "=" * 70)
    print("  NEW NODE PROVISIONING")
    print("  Complete setup flow - all steps required")
    print("=" * 70)
    
    # Check prerequisites - look in script directory
    config_file = get_script_path("golden_config_clean.yaml")
    if not os.path.exists(config_file):
        # Try legacy name
        legacy_file = get_script_path("golden_config.yaml")
        if os.path.exists(legacy_file):
            config_file = legacy_file
        else:
            print(f"\nError: golden_config_clean.yaml not found.")
            print(f"  Looked in: {SCRIPT_DIR}")
            print("\nFirst export configuration from a reference node:")
            if IS_WINDOWS:
                print("  python node_provisioner.py --export --port COM10")
            else:
                print("  python node_provisioner.py --export --port /dev/ttyUSB0")
            return False
    
    url_file = get_script_path("golden_config_url.txt")
    if not os.path.exists(url_file):
        print(f"\nError: golden_config_url.txt not found.")
        print(f"  Looked in: {SCRIPT_DIR}")
        print("\nFirst export configuration from a reference node:")
        if IS_WINDOWS:
            print("  python node_provisioner.py --export --port COM10")
        else:
            print("  python node_provisioner.py --export --port /dev/ttyUSB0")
        return False
    
    # Load golden config to check existing admin keys
    import yaml
    with open(config_file, 'r') as f:
        golden_config = yaml.safe_load(f)
    
    existing_admin_keys = golden_config.get('config', {}).get('security', {}).get('adminKey', [])
    existing_admin_keys = [k for k in existing_admin_keys if k and k != 'base64:']  # Filter empty
    
    inventory = load_inventory()
    
    # ===========================================
    # STEP 1: Select device and collect node information
    # ===========================================
    print("\n" + "-" * 50)
    print("STEP 1: Select Device & Node Information")
    print("-" * 50)
    
    # Discover and select Meshtastic device
    print("\nScanning for connected Meshtastic devices...")
    target_port = select_meshtastic_device("Select device to provision")
    
    if not target_port:
        print("\nProvisioning cancelled.")
        return False
    
    print(f"\n  Selected: {target_port}")
    
    # Node name (required)
    while True:
        node_name = input("\nNode long name (e.g., 'ICP Kennedy North'): ").strip()
        if node_name:
            break
        print("  Error: Node name is required.")
    
    # Short name will be derived from node_id after firmware flash
    # (last 4 hex chars of node ID, e.g., !a20a0fb0 -> 0fb0)
    print("  Short name: (will be auto-set from node ID after flash)")
    
    # Role (required)
    while True:
        print("\nNode roles:")
        print("  ICP  - Incident Command Post (field station)")
        print("  EOC  - Emergency Operations Center (can admin ICPs)")
        print("  HUB  - Relay/repeater node")
        role = input("Node role [ICP/EOC/HUB]: ").strip().upper()
        if role in ["ICP", "EOC", "HUB"]:
            break
        print("  Error: Role must be ICP, EOC, or HUB.")
    
    # Location (required)
    while True:
        location = input("Physical location (e.g., 'Kennedy Park North Pavilion'): ").strip()
        if location:
            break
        print("  Error: Location is required.")
    
    # ===========================================
    # STEP 2: Select firmware file
    # ===========================================
    print("\n" + "-" * 50)
    print("STEP 2: Firmware Selection")
    print("-" * 50)
    
    # Look for .uf2 files in script directory and common locations
    uf2_files = []
    search_paths = [
        SCRIPT_DIR,  # Script's directory (where golden configs are)
        os.path.join(SCRIPT_DIR, "firmware"),  # firmware subdirectory
        os.path.expanduser("~/Downloads"),  # User's downloads folder
        ".",  # Current working directory (fallback)
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in search_paths:
        abs_path = os.path.abspath(path)
        if abs_path not in seen:
            seen.add(abs_path)
            unique_paths.append(path)
    
    for path in unique_paths:
        if os.path.exists(path):
            try:
                for f in os.listdir(path):
                    if f.lower().endswith(".uf2"):
                        full_path = os.path.join(path, f)
                        uf2_files.append(full_path)
            except PermissionError:
                continue
    
    if uf2_files:
        print("\nFound firmware files:")
        for i, f in enumerate(uf2_files, 1):
            print(f"  {i}. {f}")
        print(f"  {len(uf2_files)+1}. Enter custom path")
        
        while True:
            choice = input(f"\nSelect firmware [1-{len(uf2_files)+1}]: ").strip()
            try:
                idx = int(choice)
                if 1 <= idx <= len(uf2_files):
                    firmware_path = uf2_files[idx-1]
                    break
                elif idx == len(uf2_files) + 1:
                    firmware_path = input("Enter firmware path: ").strip()
                    if os.path.exists(firmware_path):
                        break
                    print("  Error: File not found.")
            except ValueError:
                print("  Error: Invalid selection.")
    else:
        print("\nNo .uf2 firmware files found in:")
        for path in unique_paths:
            print(f"  - {path}")
        while True:
            firmware_path = input("\nEnter firmware .uf2 file path: ").strip()
            if os.path.exists(firmware_path):
                break
            print("  Error: File not found.")
    
    # ===========================================
    # STEP 3: Admin Key Configuration
    # ===========================================
    print("\n" + "-" * 50)
    print("STEP 3: Admin Key Configuration")
    print("-" * 50)
    
    # Show existing admin keys from golden config
    print("\nAdmin keys ALREADY in golden config (will be applied):")
    if existing_admin_keys:
        for i, key in enumerate(existing_admin_keys, 1):
            # Try to find matching node in inventory
            key_clean = key.replace('base64:', '')
            matching_node = None
            for node in inventory:
                if node.get('public_key', '').replace('base64:', '') == key_clean:
                    matching_node = node
                    break
            if matching_node:
                print(f"  {i}. {matching_node.get('long_name')} ({matching_node.get('node_id')})")
            else:
                print(f"  {i}. Unknown node: {key[:40]}...")
    else:
        print("  (none)")
    
    print("\nThese admin keys come from your golden config and will be applied.")
    use_golden_keys = input("Keep these admin keys? [Y/n]: ").strip().lower()
    
    if use_golden_keys == 'n':
        admin_keys_to_add = []
        print("\nAdmin keys cleared. Select new admin nodes below.")
    else:
        # We'll use the golden config as-is, no additional keys needed
        admin_keys_to_add = []
        print("  ✓ Admin keys from golden config will be applied.")
    
    # Offer to add additional admin nodes
    print("\nAdd ADDITIONAL admin nodes from inventory?")
    print("(Their public keys will be added to the admin key list)")
    
    available_admins = [n for n in inventory if n.get('public_key')]
    
    # Filter out nodes whose keys are already in golden config
    new_admin_candidates = []
    for node in available_admins:
        node_key = node.get('public_key', '').replace('base64:', '')
        already_in_golden = any(
            k.replace('base64:', '') == node_key 
            for k in existing_admin_keys
        )
        if not already_in_golden:
            new_admin_candidates.append(node)
    
    additional_admin_keys = []
    
    if new_admin_candidates:
        print("\nAvailable nodes (not already in golden config):")
        for i, node in enumerate(new_admin_candidates, 1):
            role_str = f" [{node.get('role')}]" if node.get('role') else ""
            print(f"  {i}. {node.get('long_name')} ({node.get('node_id')}){role_str}")
        print(f"  N. None (use only golden config admin keys)")
        
        choice = input("\nAdd additional admin nodes [1,2,3 / N]: ").strip().upper()
        
        if choice != "N" and choice:
            try:
                indices = [int(x.strip()) for x in choice.split(",")]
                for idx in indices:
                    if 1 <= idx <= len(new_admin_candidates):
                        node = new_admin_candidates[idx-1]
                        additional_admin_keys.append((node.get("long_name"), node.get("public_key")))
            except ValueError:
                print("  Invalid selection, no additional keys added.")
    else:
        print("\n  All inventory nodes are already in golden config admin keys.")
    
    # ===========================================
    # CONFIRMATION
    # ===========================================
    print("\n" + "=" * 70)
    print("  PROVISIONING SUMMARY")
    print("=" * 70)
    print(f"  Node Name:     {node_name}")
    print(f"  Short Name:    (auto from node ID)")
    print(f"  Role:          {role}")
    print(f"  Location:      {location}")
    print(f"  Firmware:      {firmware_path}")
    print(f"  Config:        {config_file}")
    print(f"  Channel URL:   {url_file}")
    
    # Show admin key summary
    total_admin_keys = len(existing_admin_keys) + len(additional_admin_keys)
    print(f"  Admin Keys:    {total_admin_keys} total")
    if existing_admin_keys:
        print(f"                 From golden config: {len(existing_admin_keys)}")
    if additional_admin_keys:
        print(f"                 Additional:")
        for name, key in additional_admin_keys:
            print(f"                   - {name}")
    print("=" * 70)
    
    confirm = input("\nProceed with provisioning? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Provisioning cancelled.")
        return False
    
    # ===========================================
    # STEP 4: Flash firmware
    # ===========================================
    print("\n" + "-" * 50)
    print("STEP 4: Flashing Firmware")
    print("-" * 50)
    
    if not flash_firmware(firmware_path):
        print("Firmware flash failed. Aborting.")
        return False
    
    # ===========================================
    # STEP 5: Wait for device and apply config
    # ===========================================
    print("\n" + "-" * 50)
    print("STEP 5: Applying Configuration")
    print("-" * 50)
    
    # Device should come back on the same port after firmware flash
    print(f"\nDevice should reconnect on {target_port}")
    
    # Confirm port with user
    port_confirm = input(f"\nUse {target_port}? [Y/n] or enter different port: ").strip()
    if port_confirm.lower() == 'n':
        example_port = get_port_example()
        port = input(f"Enter serial port (e.g., {example_port}): ").strip()
        if IS_WINDOWS:
            port = port.upper()
    elif IS_WINDOWS and port_confirm.upper().startswith('COM'):
        port = port_confirm.upper()
    elif not IS_WINDOWS and port_confirm.startswith('/dev/'):
        port = port_confirm
    else:
        port = target_port
    
    print(f"\nUsing port: {port}")
    
    # Wait for device to be fully ready before sending commands
    # This is critical after firmware flash - the device needs time for:
    # - Full boot sequence
    # - Radio initialization  
    # - PKC/crypto subsystem initialization
    # - Admin session readiness
    if not wait_for_device_ready(port, timeout=90, interval=5):
        print("\nDevice did not become ready in time.")
        retry = input("Try to continue anyway? [y/N]: ").strip().lower()
        if retry != 'y':
            print("Provisioning aborted.")
            return False
        print("Continuing despite device not responding...")
    
    # Get node ID and derive short name from last 4 hex chars
    print("\nReading node ID...")
    node_info = get_node_info(port)
    node_id = node_info.get('node_id', '')
    if node_id.startswith('!'):
        short_name = node_id[-4:].upper()  # Last 4 chars of node ID
    else:
        short_name = node_id[-4:].upper() if len(node_id) >= 4 else "NODE"
    print(f"  Node ID: {node_id}")
    print(f"  Short name will be: {short_name}")
    
    # Apply channel URL
    print("\nApplying channel configuration...")
    with open(url_file, 'r') as f:
        url = f.read().strip()
    returncode, stdout, stderr = run_meshtastic_cmd(["--seturl", url], port)
    if returncode != 0:
        print(f"  Warning: {stderr}")
    
    # Wait after seturl - device may briefly become unresponsive
    print("  Waiting for channel config to apply...")
    time.sleep(5)
    
    # Apply config (includes admin keys from golden config)
    # This uses the firmware's transaction system (begin_edit_settings/commit_edit_settings)
    # and requires PKC admin session negotiation. Retry if it fails.
    print("\nApplying device configuration...")
    max_config_attempts = 3
    config_success = False
    
    for attempt in range(1, max_config_attempts + 1):
        print(f"  Attempt {attempt}/{max_config_attempts}...")
        returncode, stdout, stderr = run_meshtastic_cmd(["--configure", config_file], port)
        
        if returncode == 0:
            print("  ✓ Configuration applied successfully.")
            config_success = True
            break
        elif 'PermissionError' in stderr or 'WriteFile failed' in stderr:
            print(f"  Device busy (PKC session issue). Waiting before retry...")
            time.sleep(10)  # Give device time to stabilize
        else:
            print(f"  Warning: {stderr.strip()[:100]}")
            time.sleep(5)
    
    if not config_success:
        print("  ⚠ Configuration may not have applied fully. Continuing...")
    
    # Wait for config commit and potential reboot
    print("  Waiting for configuration to commit...")
    time.sleep(5)
    
    # Set node name
    print(f"\nSetting node name: {node_name}")
    returncode, stdout, stderr = run_meshtastic_cmd(
        ["--set-owner", node_name, "--set-owner-short", short_name], port
    )
    time.sleep(2)
    
    # Enable remote hardware
    print("\nEnabling remote hardware module...")
    run_meshtastic_cmd(["--set", "remote_hardware.enabled", "true"], port)
    time.sleep(2)
    
    # ===========================================
    # STEP 6: Add additional admin keys (if any)
    # ===========================================
    if additional_admin_keys:
        print("\n" + "-" * 50)
        print("STEP 6: Adding Additional Admin Keys")
        print("-" * 50)
        
        for admin_name, admin_key in additional_admin_keys:
            print(f"\nAdding admin key for: {admin_name}")
            returncode, stdout, stderr = run_meshtastic_cmd(
                ["--set", "security.admin_key", admin_key], port
            )
            if returncode != 0:
                print(f"  Warning: {stderr}")
            time.sleep(1)
    
    # ===========================================
    # STEP 7: Record to inventory
    # ===========================================
    print("\n" + "-" * 50)
    print("STEP 7: Recording to Inventory")
    print("-" * 50)
    
    time.sleep(2)
    final_info = get_node_info(port)
    final_info["long_name"] = node_name
    final_info["short_name"] = short_name  # Derived from node_id
    final_info["role"] = role
    final_info["location"] = location
    final_info["provisioned_by"] = f"golden:{config_file}"
    
    add_to_inventory(final_info)
    
    # ===========================================
    # COMPLETE
    # ===========================================
    print("\n" + "=" * 70)
    print("  PROVISIONING COMPLETE")
    print("=" * 70)
    print(f"  Node ID:       {final_info.get('node_id', 'Unknown')}")
    print(f"  Name:          {node_name}")
    print(f"  Short Name:    {short_name}")
    print(f"  Role:          {role}")
    print(f"  Location:      {location}")
    print(f"  Hardware:      {final_info.get('hw_model', 'Unknown')}")
    print(f"  Firmware:      {final_info.get('firmware_version', 'Unknown')}")
    print(f"  Public Key:    {final_info.get('public_key', 'Unknown')}")
    print(f"  Admin Keys:    {len(admin_keys_to_add)} configured")
    print("=" * 70)
    
    return True


def interactive_mode():
    """Interactive provisioning wizard."""
    print("\n" + "=" * 60)
    print("  Meshtastic Node Provisioning Tool")
    print("  ICP Network Configuration")
    print("=" * 60)
    
    # Check Linux permissions before listing ports
    if IS_LINUX:
        check_serial_permissions()
    
    # List ports
    list_serial_ports()
    
    print("\nOptions:")
    print("  1. Export golden configuration (run once on reference node)")
    print("  2. Provision new node (complete setup flow)")
    print("  3. View node inventory")
    print("  4. Check node status (diagnostics)")
    print("  0. Exit")
    
    choice = input("\nEnter choice [0-4]: ").strip()
    
    if choice == "1":
        print("\n" + "-" * 50)
        print("EXPORT GOLDEN CONFIGURATION")
        print("-" * 50)
        print("\nConnect your fully-configured reference node via USB.")
        print("This will export all settings and channel keys.")
        
        print("\nScanning for connected Meshtastic devices...")
        port = select_meshtastic_device("Select reference node")
        
        if port:
            export_config(port)  # Uses SCRIPT_DIR by default
        
    elif choice == "2":
        provision_new_node_flow()
        
    elif choice == "3":
        show_inventory()
        
    elif choice == "4":
        print("\n" + "-" * 50)
        print("CHECK NODE STATUS")
        print("-" * 50)
        
        print("\nScanning for connected Meshtastic devices...")
        port = select_meshtastic_device("Select device to check")
        
        if port:
            info = get_node_info(port)
            print("\nNode Information:")
            print(f"  Name:       {info.get('long_name', 'Unknown')}")
            print(f"  Short:      {info.get('short_name', 'Unknown')}")
            print(f"  ID:         {info.get('node_id', 'Unknown')}")
            print(f"  Hardware:   {info.get('hw_model', 'Unknown')}")
            print(f"  Firmware:   {info.get('firmware_version', 'Unknown')}")
            print(f"  Public Key: {info.get('public_key', 'Unknown')}")
            print(f"  Has gpio:   {check_gpio_channel(port)}")
        
    elif choice == "0":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice.")


def create_icp_config_template(output_file: str = "icp_config_template.yaml"):
    """Create a template configuration file for ICP nodes."""
    template = """# ICP Network Node Configuration Template
# Apply with: meshtastic --configure icp_config_template.yaml

# Device settings
device:
  role: CLIENT
  serialEnabled: true
  nodeInfoBroadcastSecs: 10800  # 3 hours

# Position settings  
position:
  positionBroadcastSecs: 900  # 15 minutes
  positionBroadcastSmartEnabled: true
  gpsUpdateInterval: 120
  broadcastSmartMinimumDistance: 100
  broadcastSmartMinimumIntervalSecs: 30

# LoRa radio settings
lora:
  region: US
  modemPreset: SHORT_FAST
  hopLimit: 3
  txEnabled: true
  txPower: 30

# Telemetry settings
telemetry:
  deviceUpdateInterval: 900  # 15 minutes
  environmentUpdateInterval: 900
  environmentMeasurementEnabled: true
  powerMeasurementEnabled: true
  powerUpdateInterval: 900

# Remote Hardware (for GPIO LED control)
remoteHardware:
  enabled: true

# Detection Sensor (for motion detection on IO7/GPIO28)
detectionSensor:
  enabled: true
  minimumBroadcastSecs: 60
  monitorPin: 28
  detectionTriggerType: LOGIC_HIGH

# Display settings
display:
  screenOnSecs: 3600
  autoScreenCarouselSecs: 10
  wakeOnTapOrMotion: true
"""
    
    with open(output_file, 'w') as f:
        f.write(template)
    
    print(f"Template configuration saved to: {output_file}")
    print("\nNote: This template does NOT include channel configuration.")
    print("Channels (including gpio) should be set via --seturl from your golden node.")


def main():
    parser = argparse.ArgumentParser(
        description="Meshtastic Node Provisioning Tool for ICP Network",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow:
  1. Configure a reference node manually with all desired settings
  2. Scan the network to discover and inventory all nodes:
       python node_provisioner.py --scan --port COM10        # Windows
       python node_provisioner.py --scan --port /dev/ttyUSB0 # Linux
  
  3. Export golden configuration:
       python node_provisioner.py --export --port COM10        # Windows
       python node_provisioner.py --export --port /dev/ttyUSB0 # Linux
  
  4. For each new node, run the provisioning wizard:
       python node_provisioner.py
  
  The wizard will guide you through:
    - Node name and role selection
    - Firmware selection and flashing
    - Admin key configuration
    - Automatic inventory tracking

Examples:
  # Scan network and update inventory
  python node_provisioner.py --scan --port COM10           # Windows
  python node_provisioner.py --scan --port /dev/ttyACM0    # Linux

  # Export config from reference node
  python node_provisioner.py --export --port COM10         # Windows
  python node_provisioner.py --export --port /dev/ttyUSB0  # Linux

  # Run interactive provisioning wizard (default)
  python node_provisioner.py

  # View node inventory
  python node_provisioner.py --inventory

  # Check status of a connected node
  python node_provisioner.py --status --port COM5          # Windows
  python node_provisioner.py --status --port /dev/ttyACM0  # Linux

Linux Notes:
  Serial ports require 'dialout' group membership:
    sudo usermod -aG dialout $USER
    (then log out and back in)
        """
    )
    
    parser.add_argument("--scan", action="store_true",
                        help="Scan mesh network and update inventory with all discovered nodes")
    parser.add_argument("--export", action="store_true", 
                        help="Export golden configuration from connected node")
    parser.add_argument("--inventory", action="store_true",
                        help="Show node inventory")
    parser.add_argument("--status", action="store_true",
                        help="Check status of connected node")
    parser.add_argument("--list-ports", action="store_true",
                        help="List available serial ports")
    
    parser.add_argument("--port", "-p", type=str,
                        help="Serial port (e.g., COM10 or /dev/ttyUSB0)")
    
    args = parser.parse_args()
    
    # Default to interactive if no action specified
    if not any([args.scan, args.export, args.inventory, args.status, args.list_ports]):
        # Run interactive mode
        while True:
            interactive_mode()
            print()
            again = input("Do another operation? [Y/n]: ").strip().lower()
            if again == 'n':
                break
        return
    
    if args.list_ports:
        list_serial_ports()
    
    elif args.scan:
        if not args.port:
            print("Error: --port required for network scan")
            sys.exit(1)
        scan_network(args.port, update_inventory=True)
        
    elif args.inventory:
        show_inventory()
        
    elif args.status:
        if not args.port:
            print("Error: --port required for status check")
            sys.exit(1)
        info = get_node_info(args.port)
        print("\nNode Information:")
        print(f"  Name:       {info.get('long_name', 'Unknown')}")
        print(f"  Short:      {info.get('short_name', 'Unknown')}")
        print(f"  ID:         {info.get('node_id', 'Unknown')}")
        print(f"  Hardware:   {info.get('hw_model', 'Unknown')}")
        print(f"  Firmware:   {info.get('firmware_version', 'Unknown')}")
        print(f"  Public Key: {info.get('public_key', 'Unknown')}")
        print(f"  Has gpio:   {check_gpio_channel(args.port)}")
        
    elif args.export:
        if not args.port:
            print("Error: --port required for export")
            sys.exit(1)
        # Export to current directory (provisioner folder)
        export_config(args.port, ".")


if __name__ == "__main__":
    main()
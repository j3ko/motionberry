#!/bin/bash

# Exit on any error
set -e

# Function to print section headers
print_header() {
    echo "====================================="
    echo "$1"
    echo "====================================="
}

# Function to check if the system needs a reboot
needs_reboot=0

# Update System and Firmware
print_header "Updating System and Firmware"
echo "Updating package lists and performing full system upgrade..."
sudo apt update && sudo apt -y full-upgrade
# echo "Running rpi-update to update firmware..."
# sudo SKIP_SDK=1 rpi-update
echo "System and firmware update completed."

# Install Required Packages
print_header "Installing Required Packages"
echo "Installing wireless-tools and zram-tools..."
sudo apt install -y wireless-tools zram-tools
echo "Required packages installed."

# Disable Bluetooth
print_header "Disabling Bluetooth"
echo "Disabling and stopping hciuart.service..."
sudo systemctl disable --now hciuart.service
echo "Bluetooth disabled."

# Disable GPIO Triggerhappy
print_header "Disabling GPIO Triggerhappy"
echo "Disabling and stopping triggerhappy.service..."
sudo systemctl disable --now triggerhappy.service
echo "GPIO triggerhappy service disabled."

# Disable Disk Swap
print_header "Disabling Disk Swap"
echo "Editing /etc/dphys-swapfile to disable swap..."
sudo sed -i 's/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=0/' /etc/dphys-swapfile || echo "CONF_SWAPSIZE=0" | sudo tee -a /etc/dphys-swapfile
echo "Turning off swap and disabling swap service..."
sudo dphys-swapfile swapoff || echo "Swap already off."
sudo systemctl disable --now dphys-swapfile
echo "Disk swap disabled."

# Enable ZRAM
print_header "Enabling ZRAM"
echo "Configuring zramswap with zstd algorithm and 100% RAM usage..."
sudo bash -c 'cat > /etc/default/zramswap << EOL
# ALGO: Compression algorithm (e.g. lz4, zstd, lzo)
ALGO=zstd

# PERCENT: RAM to use for zram (e.g. 100 = 100%)
PERCENT=100

# ZRAM_DEVICES: Optional, number of devices (usually = CPU cores)
# ZRAM_DEVICES=4
EOL'
echo "Restarting zramswap service..."
sudo systemctl restart zramswap
echo "Checking zram status..."
swapon --show || echo "No swap devices active."
echo "ZRAM enabled."

# Configure WiFi Module
print_header "Configuring WiFi Module"
echo "Creating/editing /etc/modprobe.d/brcmfmac.conf for WiFi stability..."
sudo bash -c 'cat > /etc/modprobe.d/brcmfmac.conf << EOL
options brcmfmac roamoff=1 feature_disable=0x82000 fcmode=0
EOL'
echo "WiFi module configuration applied (roaming disabled, power-save offload and TDLS disabled, frame coalescing disabled)."

# Disable WiFi Power Management
print_header "Disabling WiFi Power Management"
echo "Creating/editing /etc/rc.local to disable WiFi power management..."
if [ ! -f /etc/rc.local ]; then
    echo "Creating new /etc/rc.local..."
    sudo bash -c 'cat > /etc/rc.local << EOL
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Ensure the script exits with "0" on success or any other value on error.
#
/usr/sbin/iwconfig wlan0 power off
exit 0
EOL'
else
    echo "Appending WiFi power management disable command to existing /etc/rc.local..."
    sudo sed -i '/exit 0/d' /etc/rc.local
    sudo bash -c 'echo "/usr/sbin/iwconfig wlan0 power off" >> /etc/rc.local'
    sudo bash -c 'echo "exit 0" >> /etc/rc.local'
fi
echo "Setting executable permissions for /etc/rc.local..."
sudo chmod +x /etc/rc.local
echo "WiFi power management will be disabled on next boot."
echo "Checking current WiFi power management status..."
iwconfig wlan0 | grep "Power Management" || echo "wlan0 not found, check WiFi interface."
needs_reboot=1

# Configure CPU/GPU/SDRAM Frequencies
print_header "Configuring CPU/GPU/SDRAM Frequencies"
echo "Editing /boot/config.txt to set CPU, GPU, and SDRAM frequencies for stability..."
if ! grep -q "arm_freq=600" /boot/config.txt; then
    sudo bash -c 'cat >> /boot/config.txt << EOL
# Throttle CPU/GPU/SDRAM for stability (reduce heat or SDIO Wi-Fi issues)
arm_freq=600
gpu_freq=300
sdram_freq=400
EOL'
else
    echo "Frequencies already configured in /boot/config.txt."
fi
echo "Commenting out arm_boost if enabled..."
sudo sed -i 's/^arm_boost=1/#arm_boost=1/' /boot/config.txt || echo "arm_boost not found, no changes made."
echo "CPU/GPU/SDRAM frequencies configured."
needs_reboot=1

# Final Instructions
print_header "Setup Complete"
echo "All optimizations have been applied."
if [ $needs_reboot -eq 1 ]; then
    echo "A reboot is required to apply some changes."
    echo "Would you like to reboot now? (y/n)"
    read -r answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        echo "Rebooting now..."
        sudo reboot
    else
        echo "Please reboot manually later to apply all changes."
    fi
else
    echo "No reboot required."
fi
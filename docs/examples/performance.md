# Performance Tuning Guide

This guide outlines essential steps to set up and optimize your Raspberry Pi OS 64-bit system for Motionberry. Following these steps will improve performance and ensure your Motionberry system operates smoothly.

---

## Update Your System

Start by updating your system to ensure all software is up-to-date:

```bash
sudo apt update && sudo apt -y upgrade
```

---

## Disable WiFi Power Management

Disabling WiFi power management can improve network stability and reduce power-saving interruptions. Follow these steps:

1. Install the `wireless-tools` package if not already installed:
    ```bash
    sudo apt install wireless-tools
    ```

2. Open the `rc.local` file for editing:
    ```bash
    sudo nano /etc/rc.local
    ```

3. Paste the following lines into the file:
    ```bash
    #!/bin/sh -e
    #
    # rc.local
    #
    # This script is executed at the end of each multiuser runlevel.
    # Ensure the script exits with "0" on success or any other value on error.
    #
    # By default, this script does nothing.
    #
    /usr/sbin/iwconfig wlan0 power off
    exit 0
   ```

4. Change the file permissions to make it executable:
    ```bash
    sudo chmod +x /etc/rc.local
    ```

5. Reboot your Raspberry Pi to apply the changes:
    ```bash
    sudo reboot
    ```

6. After rebooting, check the status of WiFi power management:
    ```bash
    iwconfig
    ```
    You should see `Power Management:off` in the output for `wlan0`.

---

## Increase Swap

Increasing the swap file size can improve performance when dealing with memory-intensive tasks. Follow these steps:

1. Disable the Swap File
    ```bash
    sudo dphys-swapfile swapoff
    ```

2. Open the swap file configuration file:
    ```bash
    sudo nano /etc/dphys-swapfile
    ```

    Update the swap size setting to 1024 MB:
    ```bash
    CONF_SWAPSIZE=1024
    ```

3. Set up the new swap file:
    ```bash
    sudo dphys-swapfile setup
    ```

4. Enable the swap file:
    ```bash
    sudo dphys-swapfile swapon
    ```

---

## Tweak Swap Settings

Tuning the swap settings can optimize system performance by adjusting memory management behavior.

1. Open the system configuration file for editing:
    ```bash
    sudo nano /etc/sysctl.conf
    ```

2. Add these parameters at the end of the file:
    ```bash
    vm.swappiness=10
    vm.vfs_cache_pressure=50
    ```

3. Reboot the Raspberry Pi to apply the changes:
    ```bash
    sudo reboot
    ```

4. After rebooting, verify the updated cache settings:
    ```bash
    sudo swapon --show
    cat /proc/sys/vm/swappiness
    cat /proc/sys/vm/vfs_cache_pressure
    ```

---

## Enable ZRAM

Enabling zram allows the system to use compressed block devices as swap space, improving performance on memory-limited systems by reducing swapping to the slower SD card or disk. Follow these steps to enable zram:

1. Install `git` if not already installed:
    ```bash
    sudo apt install git
    ```

2. Clone the script from GitHub:
    ```bash
    git clone https://github.com/foundObjects/zram-swap
    ```

3. Navigate to the script directory and run the install script:
    ```bash
    cd zram-swap
    sudo ./install.sh
   ```

4. Check zram swap status:
    ```bash
    sudo cat /proc/swaps
    ```

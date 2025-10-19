# Vestwoods BMS Home Assistant Custom Component

This custom component integrates Vestwoods Battery Management Systems (BMS) with Home Assistant, allowing you to monitor your battery's status, cell voltages, temperatures, and more.

It connects to the BMS via Bluetooth Low Energy (BLE) and publishes the data to your Home Assistant's MQTT broker, which is then exposed as sensors in Home Assistant.

## Features

*   Monitor key BMS parameters (Total Voltage, SOC, Current, Temperatures).
*   Configurable refresh interval.
*   Graceful handling of BLE connection drops with automatic retries.

## Installation

There are two recommended ways to install this custom component:

### 1. Installation via HACS (Recommended for easy updates!)

The Home Assistant Community Store (HACS) makes it incredibly easy to install and manage custom components, including automatic updates.

1.  **Install HACS:** If you don't already have HACS, follow the installation instructions on the [HACS Website](https://hacs.xyz/).
2.  **Add Custom Repository:**
    *   In Home Assistant, go to **HACS** -> **Integrations**.
    *   Click the three dots in the top right corner and select **"Custom repositories"**.
    *   Enter the URL of this GitHub repository (`https://github.com/jasondeklerk/VestwoodsBMS`) in the "Repository" field.
    *   Select "Integration" as the "Category".
    *   Click "Add".
3.  **Install the Integration:**
    *   Search for "Vestwoods BMS" in HACS and click on it.
    *   Click "Download" and select the latest version.
    *   Restart Home Assistant when prompted.
4.  **Configure the Integration:**
    *   Go to **Settings** -> **Devices & Services** -> **Integrations**.
    *   Click the **"+ Add Integration"** button.
    *   Search for "Vestwoods BMS" and follow the configuration wizard to enter your BMS's MAC address and desired refresh interval.

### 2. Manual Installation

1.  **Download the Component:**
    *   Navigate to the latest release on this GitHub repository.
    *   Download the `vestwoods_bms` folder.
2.  **Copy to Custom Components:**
    *   Copy the entire `vestwoods_bms` folder into your Home Assistant's `custom_components` directory.
    *   Your Home Assistant configuration directory is typically located at `/config` (e.g., `/usr/share/hassio/homeassistant/` for Home Assistant OS, or `~/.homeassistant/` for a Home Assistant Core installation).
    *   The final path should look like: `<HA_CONFIG_DIR>/custom_components/vestwoods_bms/`.
3.  **Restart Home Assistant:** Restart your Home Assistant instance to load the new component.
4.  **Configure the Integration:**
    *   Go to **Settings** -> **Devices & Services** -> **Integrations**.
    *   Click the **"+ Add Integration"** button.
    *   Search for "Vestwoods BMS" and follow the configuration wizard to enter your BMS's MAC address and desired refresh interval.

## Requirements

*   **Home Assistant with MQTT Integration:** This component relies on your Home Assistant instance having the [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) configured and running.
*   **Bluetooth on Host System:** Your Home Assistant host system must have Bluetooth enabled and properly configured for the component to communicate with your BMS via BLE.
*   **Python Dependencies:** The component automatically handles its Python dependencies (`Bleak`, `paho-mqtt`).

## Configuration

During the setup process, you will be asked for:

*   **MAC Address:** The Bluetooth MAC address of your Vestwoods BMS (e.g., `XX:XX:XX:XX:XX:XX`).
*   **Refresh Interval (seconds):** How often the component should attempt to read data from the BMS (e.g., `30` for every 30 seconds).

## Sensors

Once configured, the following sensors will be available in Home Assistant:

*   `sensor.vestwoods_bms_<mac_address_sanitized>_total_voltage`
*   `sensor.vestwoods_bms_<mac_address_sanitized>_state_of_charge`
*   `sensor.vestwoods_bms_<mac_address_sanitized>_total_current`
*   `sensor.vestwoods_bms_<mac_address_sanitized>_environmental_temperature`
*   `sensor.vestwoods_bms_<mac_address_sanitized>_pcb_temperature`

(Note: `<mac_address_sanitized>` will have colons replaced with underscores.)

## Troubleshooting

*   **"Integration not found"**: Ensure the `vestwoods_bms` folder is correctly placed in `custom_components` and Home Assistant has been restarted.
*   **"Failed to connect to BMS"**: 
    *   Double-check the MAC address.
    *   Ensure your Home Assistant host has Bluetooth enabled and is within range of the BMS.
    *   Check Home Assistant logs for more detailed error messages.
*   **No sensor data**: 
    *   Verify your MQTT integration is working correctly.
    *   Check Home Assistant logs for any errors from the "Vestwoods BMS" integration.

#
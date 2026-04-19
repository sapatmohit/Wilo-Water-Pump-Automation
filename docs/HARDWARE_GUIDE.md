# LoRa Hardware & Testing Guide

This guide details the wiring connections and testing procedures for the Point-to-Point LoRa communication system.

## 1. Hardware Connections

### A. ESP32 (Sender) to SX1278/SX1276
**Note:** The ESP32 uses 3.3V logic. **DO NOT** connect to 5V.

| SX127x Pin | ESP32 Pin (GPIO) | Description       |
|------------|------------------|-------------------|
| VCC        | 3.3V             | Power             |
| GND        | GND              | Ground            |
| MISO       | GPIO 19          | SPI Data Out      |
| MOSI       | GPIO 23          | SPI Data In       |
| SCK        | GPIO 18          | SPI Clock         |
| NSS (CS)   | GPIO 5           | Chip Select       |
| RST        | GPIO 14          | Reset             |
| DIO0       | GPIO 26          | Interrupt (Done)  |

*Check `embedded/esp32_sender/esp32_sender.ino` if you need to change these pins.*

---

### B. Raspberry Pi Zero 2W (Receiver) to SX1278/SX1276
**Note:** Raspberry Pi GPIO is strictly 3.3V.

| SX127x Pin | RPi Pin (Physical) | RPi GPIO (BCM) | Description      |
|------------|--------------------|----------------|------------------|
| VCC        | Pin 1 or 17        | 3.3V           | Power            |
| GND        | Pin 6, 9, 20 etc.  | GND            | Ground           |
| MISO       | Pin 21             | GPIO 9         | SPI MISO         |
| MOSI       | Pin 19             | GPIO 10        | SPI MOSI         |
| SCK        | Pin 23             | GPIO 11        | SPI SCLK         |
| NSS (CS)   | Pin 24             | GPIO 8 (CE0)   | Chip Select      |
| RST        | Pin 22             | GPIO 25        | Reset            |
| DIO0       | Pin 18             | GPIO 24        | Interrupt        |

*Warning: Double-check pin numbers. Physical Pin number is different from BCM GPIO number.*

## 2. Software Prerequisites

### ESP32
1. Install **Arduino IDE** or **VS Code + PlatformIO**.
2. Install Library: `LoRa` by **Sandeep Mistry**.

### Raspberry Pi
1. Enable SPI:
   - Run `sudo raspi-config`
   - **Interface Options** -> **SPI** -> **Yes**.
   - Reboot (`sudo reboot`).
2. Install Python dependencies:
   ```bash
   cd "c:\Project\Industrial Projects\Wilo Water Pump Automation\embedded\rpi_receiver"
   # On RPi:
   # cd ~/Wilo-Water-Pump-Automation/embedded/rpi_receiver
   pip3 install -r requirements.txt
   ```

## 3. Testing Procedure

### Step 1: Upload Sender Code
1. Open `embedded/esp32_sender/esp32_sender.ino`.
2. Connect ESP32 via USB.
3. Select correct Board and Port.
4. Upload.
5. Open Serial Monitor (115200 baud). You should see:
   ```
   LoRa Sender Setup...
   LoRa Initialized OK!
   Sending packet: 0
   Sending packet: 1
   ```

### Step 2: Run Receiver Script
1. On the Raspberry Pi terminal:
   ```bash
   python3 receiver.py
   ```
2. Success Output:
   ```
   Initializing LoRa Receiver...
   SX127x Version: 0x12
   LoRa Initialized. Listening for packets...
   ```
   *(If Version is `0x00`, check Wiring!)*

### Step 3: Verify Transmission
If both are running, the RPi terminal should show:
```
Received Packet: '{"device":"esp32","count":5,"value":42}' | RSSI: -45 dBm | SNR: 9.00 dB
```

## 4. Troubleshooting
- **Range Issues**: Ensure antennas are connected to both LoRa modules.
- **Garbage Data**: Check if `BAND` (433E6 vs 868E6) matches in both scripts.
- **"Starting LoRa failed!" (ESP32)**: Check connections, specifically NSS, RST, and DIO0.

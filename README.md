# Wilo AI Water Transfer System

A professional IoT and AI-powered industrial water pump automation system featuring real-time hydrostatic tank estimation, LoRa pressure telemetry, ACS712 current sensing, deterministic festival/holiday policies (Rang Panchami & Indian holidays), municipal water cut handling, and machine learning schedule prediction.

---

## 🏆 JURY DAY QUICK START (ONE-CLICK LAUNCH)

### Target Dashboard Address:
```text
http://192.168.137.64:8080
```

### Steps to Run on Jury Day:
1. **Power Hardware**: Power on the Raspberry Pi 4, ESP32 transmitter, and pump relay electronics.
2. **Connect Network**: Ensure your Windows PC and the Raspberry Pi are connected to the same network / Wi-Fi / phone hotspot (`192.168.137.64`).
3. **Double Click**: Run [`Run-Wilo.bat`](Run-Wilo.bat) from this repository on your Windows PC.
4. **Automated Verification**:
   - `[1/4]` Pings Raspberry Pi at `192.168.137.64`.
   - `[2/4]` Verifies dashboard port `8080`.
   - `[3/4]` Starts services via SSH automatically if not already active.
   - `[4/4]` Confirms service readiness.
5. **Browser Opens Automatically**: Displays the full live dashboard at `http://192.168.137.64:8080`.
6. **Verify Live Telemetry**:
   - **Upper Tank Pressure**: Live readings streamed over LoRa from ESP32.
   - **Motor Current**: Live RMS current measured by ADS1115 / ACS712.
   - **Pump Relay State**: Real GPIO 17 output state.
   - **Festival Policy**: Rang Panchami auto-start restriction (< 19:00 IST) active and visible.

---

## 🏛️ System Architecture

```text
                                 WINDOWS PC (OPERATOR / JURY)
                                              │
                                 LAN / Wi-Fi (192.168.137.64)
                                              │
                                              ▼
                             RASPBERRY PI (192.168.137.64)
                                              │
               ┌──────────────────────────────┴──────────────────────────────┐
               │                                                             │
               ▼                                                             ▼
     React Dashboard (Vite)                                         Flask API Server
     Port 8080 (0.0.0.0)                                            Port 5050 (127.0.0.1)
     ├── SCADA Simulation View                                      ├── SSE Telemetry Stream (/stream)
     ├── Admin Hardware Diagnostics                                 ├── Sensor Status (/api/hardware/status)
     ├── Municipal Water Cut Management                             ├── Festival Policies (/api/festival/*)
     └── Festival Policy Calendar                                   └── Pump Control API (/api/pump/*)
               │                                                             │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
                                   CONTROLLER PIPELINE
                                              │
               ┌──────────────────────────────┼──────────────────────────────┐
               │                              │                              │
               ▼                              ▼                              ▼
          LoRa RX (SPI)                 ADC Sensors                    Relay (GPIO)
          SX1278 (433 MHz)              ADS1115 (I2C)                  GPIO 17 (Pump)
          ESP32 Telemetry               ACS712 Current                 GPIO 27 (Valve)
               │                        ZMPT101B Voltage               Override Buttons
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                                              ▼
                                   DECISION & POLICY CHAIN
                                              │
                                              ▼
                                   [ EMERGENCY STOP LAYER ]
                                              ↓
                                   [ SENSOR SAFETY GUARDS ]
                                    (Dry-Run, Overfill, Stale)
                                              ↓
                                   [ DETERMINISTIC POLICIES ]
                                    (Rang Panchami, Water Cuts)
                                              ↓
                                   [ ML PREDICTIVE SCHEDULE ]
                                              ↓
                                        RELAY OUTPUT
```

---


## 🏗️ Project Structure

```
Wilo Water Pump Automation/
├── config/                     # Configuration files
│   └── settings.py             # Main configuration settings
├── data/                       # Data storage
│   ├── raw/                    # Raw data files (CSV, logs)
│   └── processed/              # Processed data outputs
├── docs/                       # Documentation
│   ├── api/                    # API documentation
│   └── user/                   # User guides
├── logs/                       # Application logs
│   ├── pump/                   # Pump operation logs
│   └── simulation/             # Simulation logs
├── models/                     # Machine learning models
│   └── trained/                # Trained model files (.pkl)
├── scripts/                    # Utility scripts
│   ├── deploy/                 # Deployment scripts
│   └── maintenance/            # Maintenance utilities
├── src/                        # Source code
│   ├── core/                   # Core application logic
│   │   └── main.py             # Main application file
│   ├── dashboard/              # Terminal UI components
│   │   └── terminal_ui.py      # Professional dashboard styling
│   ├── models/                 # ML model handlers
│   │   └── prediction.py       # Prediction algorithms
│   ├── simulation/             # Simulation modules
│   │   ├── run_simulation.py   # Basic simulation
│   │   └── simulation_30days.py # Extended simulation
│   └── utils/                  # Utility modules
│       ├── data_handler.py     # Data processing utilities
│       └── sensors.py          # Sensor data handling
├── tests/                      # Test files
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
└── run.py                      # Main entry point
```

## 🚀 Features

### Core Functionality

- **Predictive Pump Control**: AI-powered prediction of optimal pump operation times
- **Historical Pattern Analysis**: 2-year historical data analysis for pattern recognition
- **Intelligent Scheduling**: Smart scheduling based on usage patterns and environmental factors
- **Professional Dashboard**: Beautiful terminal-based monitoring interface

### Advanced Capabilities

- **Fallback Mechanisms**: Robust fallback systems for sensor failures
- **Environmental Adaptation**: Adaptive algorithms based on temperature, humidity, and seasonal patterns
- **Real-time Monitoring**: Continuous sensor data monitoring and analysis
- **Comprehensive Logging**: Detailed operation logging for trend analysis

### LoRa Test Folder

For direct ESP32-to-ESP32 LoRa validation, use:

- [`firmware/lora_testing/README.md`](firmware/lora_testing/README.md)

### ESP32 Sender -> Raspberry Pi CSV Logger

For the production path where the ESP32 sender transmits pressure packets and the
Raspberry Pi receives them and appends them to a CSV, use:

- [`src/controller/lora_csv_receiver.py`](src/controller/lora_csv_receiver.py)

Run on the Pi:

```bash
python3 src/controller/lora_csv_receiver.py
```

To auto-start on boot, install:

```bash
sudo cp src/controller/wilo-lora-csv-receiver.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wilo-lora-csv-receiver
sudo systemctl start wilo-lora-csv-receiver
```

The CSV is created automatically at:

```text
logs/lora/esp32_pressure_packets.csv
```

### Simulation Features

- **Fast-Forward Simulation**: 30-day simulation with 60x speed
- **Basic Simulation**: Real-time simulation for testing
- **Pattern Validation**: Historical pattern validation through simulation

## 📋 Requirements

### System Requirements

- Python 3.8 or higher
- Windows/Linux/macOS
- Minimum 4GB RAM
- 1GB free disk space

### Python Dependencies

```
joblib>=1.3.0
numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=1.0.0
```

## 🔧 Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd "Wilo Water Pump Automation"
   ```

2. **Create virtual environment**

   ```bash
   python -m venv env
   source env/bin/activate  # Linux/macOS
   # or
   env\Scripts\activate  # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**

   ```bash
   python run.py --help
   ```

## 🏃 How to Run

This is a multi-device system. Each component runs on a **specific device** — read the table first, then jump to the section for the device you're setting up.

### System Overview — who runs what

| # | Device | Component | Path | Command | Port |
|---|--------|-----------|------|---------|------|
| 1 | **ESP32** (sender) | Sensor firmware | `firmware/esp32_sender/` | Flash via Arduino IDE | LoRa 433 MHz |
| 2 | **Raspberry Pi** | Pump controller (the brain) | `src/controller/pump_controller.py` | `python3 pump_controller.py` | — (GPIO) |
| 3 | **Raspberry Pi** | Backend API + live dashboard | `src/dashboard/server.py` | `python3 server.py` | `5050` |
| 4 | **Any PC / the Pi** | Frontend web dashboard (React) | `dashboard/` | `bun dev` / `npm run dev` | `8080` |
| 5 | **Any PC** (optional) | Terminal control panel (TUI) | `tui/` | `npm run dev` (over SSH) | — |
| 6 | **Any PC** (optional) | ML simulation / offline app | `run.py` | `python run.py` | — |

**Data flow:** ESP32 → *(LoRa)* → Pi controller → *(status JSON + `/api`)* → Backend `server.py` → *(HTTP :5050)* → Frontend dashboard.

> The **backend** (`server.py`) both serves the built-in HTML dashboard on port `5050` **and** exposes the `/api/*` endpoints that the React **frontend** talks to. The React app (port `8080`) proxies `/api`, `/latest`, `/stream` to `127.0.0.1:5050`.

---

### 1. ESP32 — Sensor Node (sender)

The ESP32 reads the PR12-P210 pressure sensor on the upper tank and broadcasts JSON packets over LoRa.

1. Open `firmware/esp32_sender/esp32_sender.ino` in the **Arduino IDE** (or `arduino-cli`).
2. Install the ESP32 board package and a LoRa (SX127x) library.
3. Select your ESP32 board + port, then **Upload**.
4. Wire per `docs/HARDWARE_GUIDE.md` (sensor on GPIO34, LoRa on the SPI pins defined at the top of the sketch).

Test sketches also live in `firmware/`: `esp32_relay_test/`, `esp32_lora_hello/`, `esp32_receiver/`.

---

### 2. Raspberry Pi Deployment (Automated or Manual)

The Raspberry Pi runs the complete hardware loop:
- **Pump Controller (`pump_controller.py`)**: Runs pump logic, LoRa packet parsing, ADS1115 sensor reading, and GPIO 17 relay control.
- **Flask API Backend (`server.py`)**: Runs on port `5050` (or serves built SPA), handles REST API, auth, and SSE `/stream`.
- **React Frontend (`dashboard/`)**: Runs on port `8080` (binds `0.0.0.0`) and proxies API calls to Flask.

#### Option A: One-Command Automated Setup (Recommended)
Automatically builds the dashboard, installs systemd services, and enables auto-start on boot:
```bash
git clone https://github.com/sapatmohit/Wilo-Water-Pump-Automation.git
cd Wilo-Water-Pump-Automation
pip install -r requirements.txt
bash scripts/setup_systemd.sh
```

#### Option B: Manual Startup via Script
```bash
cd Wilo-Water-Pump-Automation
pip install -r requirements.txt
cd dashboard && npm install && npm run build && cd ..
bash start_wilo.sh
```

#### Option C: Running Services Individually
```bash
# 1. Start Pump Controller (in terminal 1)
python3 src/controller/pump_controller.py

# 2. Start Flask Telemetry Backend (in terminal 2)
python3 src/dashboard/server.py --port 5050

# 3. Start React Frontend (in terminal 3)
cd dashboard
npm run preview -- --host 0.0.0.0 --port 8080
# Or for live hot-reload development:
npm run dev -- --host 0.0.0.0 --port 8080
```

---

### 3. Windows PC — Local Development & Jury Execution

#### A. Jury Day Execution (Connecting to Raspberry Pi):
Simply double-click:
```bat
Run-Wilo.bat
```
This tests connectivity to `192.168.137.64`, starts services over SSH if needed, waits for port `8080`, and opens `http://192.168.137.64:8080`.

#### B. Local Windows Development Mode (Offline / Mock Hardware):
```bash
# Terminal 1: Backend
python src/dashboard/server.py --port 5050

# Terminal 2: Frontend
cd dashboard
npm run dev
```
Open `http://localhost:8080` in your browser. All hardware gracefully reports mock/offline status without errors.

---

### 4. Optional — Terminal UI (remote control over SSH)

Controls the Pi's live controller from your laptop without racing GPIO (it writes override commands the controller consumes):

```bash
cd tui
npm install
WILO_PI_HOST=wilopi.local WILO_PI_USER=wilopi npm run dev
```

---

### 5. Optional — ML Simulation / Offline App

Runs anywhere (no hardware needed) — the predictive dashboard, simulations, and tests:

```bash
python run.py                              # predictive terminal app
python src/simulation/run_simulation.py    # basic simulation
python src/simulation/simulation_30days.py # 30-day fast-forward simulation
python -m pytest tests/unit/               # tests
```

### Configuration

Two separate config files — don't mix them up:

- `config/settings.py` — the **ML / simulation app** (model paths, fallbacks, dashboard widths).
- `src/controller/tank_config.py` — the **Pi hardware** (GPIO pins, tank thresholds, LoRa/sensor calibration, safety guards).

## 📊 Data Structure

### Historical Data Format

- **Date**: YYYY-MM-DD format
- **Hour**: Hour of operation (0-23)
- **Duration**: Operation duration in minutes
- **TopTankLevel**: Water level percentage (0-100)
- **Voltage**: System voltage (V)
- **Current**: System current (A)
- **Temperature**: Ambient temperature (°C)
- **Humidity**: Relative humidity (%)

### Log Data Format

- **date**: Operation date
- **start_hour**: Predicted start hour
- **duration**: Predicted duration
- **sensor_data**: Real-time sensor readings

## 🎛️ Dashboard Interface

The professional terminal dashboard provides:

### Visual Elements

- **Color-coded status indicators**
- **Real-time sensor data display**
- **Historical analysis summaries**
- **Prediction results**
- **System alerts and notifications**

### Information Panels

- **System Header**: Application title and version
- **Configuration Panel**: Current settings and file paths
- **Historical Analysis**: 2-year pattern analysis
- **Real-time Monitoring**: Live sensor data and predictions
- **Status Updates**: Operation logs and alerts

## 🔮 Prediction Algorithms

### Machine Learning Models

- **Start Hour Prediction**: Predicts optimal pump start time
- **Duration Prediction**: Predicts optimal operation duration
- **Pattern Recognition**: Identifies historical usage patterns

### Fallback Systems

1. **Historical Pattern Matching**: Uses similar historical conditions
2. **Statistical Averages**: Falls back to statistical patterns
3. **Default Parameters**: Final fallback with safe defaults

## 🧪 Testing

### Unit Tests

```bash
# Run all unit tests
python -m pytest tests/unit/

# Run specific test
python tests/unit/test_analysis.py
```

### Integration Tests

```bash
# Run integration tests
python -m pytest tests/integration/
```

## 📈 Monitoring & Logging

### Log Files

- **Pump Operations**: `logs/pump/pump_usage_log.csv`
- **System Events**: Console output with timestamps
- **Simulation Results**: `data/processed/simulation_results.csv`

### Dashboard Tags

- `[INFO]`: General information
- `[SUCCESS]`: Successful operations
- `[WARNING]`: Warning messages
- `[ERROR]`: Error conditions
- `[CONFIG]`: Configuration information
- `[CONTROL]`: Pump control operations
- `[SENSORS]`: Sensor data
- `[PREDICT]`: Prediction results

## 🔧 Customization

### Adding New Sensors

1. Modify `src/utils/sensors.py`
2. Update data structure in `src/utils/data_handler.py`
3. Adjust prediction models if needed

### Custom Prediction Algorithms

1. Create new module in `src/models/`
2. Implement prediction interface
3. Update main application to use new algorithm

### Dashboard Customization

1. Modify `src/dashboard/terminal_ui.py`
2. Adjust colors, layouts, and formatting
3. Add new display components

## 🚨 Troubleshooting

### Common Issues

**Model Loading Errors**

- Ensure model files exist in `models/trained/`
- Check file permissions
- Verify Python dependencies

**Data Loading Issues**

- Verify CSV file format
- Check file paths in configuration
- Ensure sufficient disk space

**Permission Errors**

- Run with appropriate permissions
- Check directory write access
- Verify log directory exists

### Debug Mode

Set `LOG_LEVEL = 'DEBUG'` in `config/settings.py` for detailed logging.

## 🔌 Connecting the Laptop to the Raspberry Pi over SSH (Mobile Hotspot)

The Pi runs headless — you control it from your laptop over SSH. In the field there's usually no router, so the simplest setup is a **phone hotspot** that both the Pi and the laptop join. Both devices must be on the **same hotspot**.

```
   📱 Phone Hotspot  (e.g. "Sarthak-iPhone")
        │
   ┌────┴─────┐
   │          │
 💻 Laptop   🍓 Raspberry Pi
              (headless — SSH target)
```

### 1. Enable SSH on the Raspberry Pi

- **Raspberry Pi Imager**: enable SSH (and set hostname/user/password) in the advanced options before flashing, **or**
- On a running Pi: `sudo raspi-config` → *Interface Options* → *SSH* → *Enable*, **or**
- Headless: drop an empty file named `ssh` into the boot partition of the SD card.

Default project user/hostname (from the systemd + TUI config): user `wilopi`, hostname `wilopi.local`.

### 2. Make the Pi auto-join the phone hotspot

Since the Pi is headless, it must already know the hotspot's Wi-Fi so it connects on boot. Set a **fixed SSID + password** on the phone hotspot, then tell the Pi about it:

- **Easiest (before flashing):** in Raspberry Pi Imager advanced options, set the Wi-Fi SSID/password to your **hotspot's** name and password.
- **Headless SD-card edit:** create `wpa_supplicant.conf` in the SD card's boot partition:

  ```text
  country=IN
  ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
  update_config=1

  network={
      ssid="YOUR_HOTSPOT_NAME"
      psk="YOUR_HOTSPOT_PASSWORD"
  }
  ```

- **On a Pi you can already reach:** `sudo raspi-config` → *System Options* → *Wireless LAN*, or `sudo nmcli dev wifi connect "YOUR_HOTSPOT_NAME" password "YOUR_HOTSPOT_PASSWORD"`.

> 💡 Turn the phone hotspot **on first**, then power the Pi — it joins automatically. Keep the SSID/password the same every time so the Pi always reconnects.

### 3. Connect the laptop to the **same** hotspot, then find the Pi's IP

Join the laptop to the same phone hotspot. Phone hotspots often **don't** resolve `wilopi.local` (no mDNS), so find the Pi's IP address:

- **On the phone:** open *Hotspot / Connected Devices* — it lists each connected device's name and IP (the Pi shows up as `wilopi` or `raspberrypi`).
- **From the laptop:** scan the hotspot subnet (commonly `172.20.10.x` on iPhone, `192.168.43.x` on Android):

  ```bash
  # try the hostname first (sometimes works)
  ping wilopi.local

  # otherwise scan the subnet (install nmap, or use arp)
  nmap -sn 172.20.10.0/24
  arp -a | grep -iE 'b8:27:eb|dc:a6:32|e4:5f:01'   # Raspberry Pi MAC prefixes
  ```

### 4. SSH in from the laptop

```bash
# Using the fixed deployment IP:
ssh wilopi@192.168.137.64

# …or by hostname if mDNS works on your network:
ssh wilopi@wilopi.local
```

First connection asks to confirm the host fingerprint — type `yes`. Then enter the Pi password.

### 5. Passwordless login (SSH keys — recommended)

Generate a key on the **laptop** (skip if you already have `~/.ssh/id_ed25519.pub`), then copy it to the Pi:

```bash
ssh-keygen -t ed25519            # press Enter through the prompts
ssh-copy-id wilopi@192.168.137.64 # copies your public key to the Pi
```

Now `ssh wilopi@192.168.137.64` logs in with no password.

### 6. Reach the dashboard from the laptop browser

Browse directly to:
```text
http://192.168.137.64:8080
```
Or use [`Run-Wilo.bat`](Run-Wilo.bat) for automated connectivity check and browser launch.

---

## 🔧 Comprehensive Troubleshooting Guide

### 1. Raspberry Pi Unreachable (`192.168.137.64`)
- Ensure the Pi is powered with a dedicated 5V 3A USB-C power supply.
- Check that your laptop Wi-Fi is connected to the same network / phone hotspot.
- On Windows PowerShell, test: `ping 192.168.137.64` or `arp -a | findstr 192.168.137`.
- If using a phone hotspot, ensure "AP Isolation / Client Isolation" is disabled.

### 2. Port 8080 Unavailable
- Check if frontend is running: `ssh wilopi@192.168.137.64 "sudo systemctl status wilo-frontend"`
- Verify port binding: `ssh wilopi@192.168.137.64 "sudo ss -tulpn | grep 8080"`
- To manually start: `cd ~/Desktop/Wilo-Water-Pump-Automation/dashboard && npm run preview -- --host 0.0.0.0 --port 8080`

### 3. Backend (Port 5050) Unavailable
- Check status: `sudo systemctl status wilo-server`
- Check logs: `journalctl -u wilo-server -n 50 --no-pager`
- Verify health: `curl -s http://127.0.0.1:5050/api/health`

### 4. LoRa ESP32 Telemetry "TIMEOUT" or "OFFLINE"
- Verify ESP32 is powered and the OLED/Serial shows `LoRa sent #...`.
- Verify SPI bus is enabled on the Pi: `ls /dev/spidev0.*` (run `sudo raspi-config` -> Interfaces -> SPI -> Enable if missing).
- Ensure frequency matches on both sides: `433E6` (433 MHz).
- Check packet log: `tail -n 20 logs/lora/esp32_pressure_packets.csv`.

### 5. Current Sensor Reading 0 A or Offline
- Ensure ADS1115 I2C connection is seated: `i2cdetect -y 1` should show address `0x48`.
- Ensure CT sensor clamp is around only ONE live conductor (not around a 2-wire cable).

### 6. Relay Not Clicking
- Check GPIO 17 wiring: Pin 11 on Raspberry Pi 4.
- Verify manual pump toggle: `curl -X POST http://127.0.0.1:5050/api/pump/on`
- Test relay script: `python3 -c "import RPi.GPIO as G; G.setmode(G.BCM); G.setup(17, G.OUT); G.output(17, G.LOW); import time; time.sleep(2); G.output(17, G.HIGH); G.cleanup()"`


# Wilo Pump Automation — Complete Hardware Wiring Guide

> **System**: ESP32 (upper tank) ↔ LoRa 433 MHz ↔ RPi Zero 2W (pump room)

---

## Overview

```
┌─────────────────────────────────┐        LoRa 433 MHz        ┌──────────────────────────────────────┐
│        UPPER TANK (Roof)        │ ~~~~~~~~~~~~~~~~~~~~~~~~>  │      MAIN TANK / PUMP ROOM           │
│                                 │                            │                                      │
│  PR12 P210 Pressure Sensor      │                            │  RPi Zero 2W                         │
│        ↓ (0.5–4.5 V)           │                            │   ├─ SX1278 LoRa Module (SPI)        │
│  ESP32 GPIO34 (ADC)             │                            │   ├─ ADS1115 ADC (I2C)               │
│        ↓                        │                            │   │   ├─ ACS712T-30A (current)        │
│  SX1278 LoRa Module (SPI)       │                            │   │   └─ ZMPT101B (voltage)           │
│                                 │                            │   ├─ 2-CH Relay Module                │
│                                 │                            │   ├─ Manual Override Buttons (×2)     │
│                                 │                            │   └─ Status LED                       │
└─────────────────────────────────┘                            └──────────────────────────────────────┘
```

---

## 1. RPi Zero 2W → SX1278 LoRa Module (SPI0)

| SX1278 Pin | RPi Physical Pin | RPi GPIO (BCM) | Wire Colour (suggested) |
|------------|-----------------|----------------|------------------------|
| **VCC**    | Pin 1           | 3.3V           | 🔴 Red                |
| **GND**    | Pin 6           | GND            | ⚫ Black              |
| **MISO**   | Pin 21          | GPIO 9         | 🟡 Yellow             |
| **MOSI**   | Pin 19          | GPIO 10        | 🟢 Green              |
| **SCK**    | Pin 23          | GPIO 11        | 🟠 Orange             |
| **NSS/CS** | Pin 24          | GPIO 8 (CE0)   | 🔵 Blue               |
| **RST**    | Pin 22          | GPIO 25        | ⚪ White              |
| **DIO0**   | Pin 18          | GPIO 24        | 🟣 Purple             |

> ⚠️ **SX1278 is 3.3V only. DO NOT connect VCC to 5V!**
> ⚠️ **Antenna MUST be connected before powering on.**

---

## 2. RPi → ADS1115 ADC Module (I2C1)

| ADS1115 Pin | RPi Physical Pin | RPi GPIO (BCM) | Notes                  |
|-------------|-----------------|----------------|------------------------|
| **VDD**     | Pin 2           | 5V             | Power (allows 0–5V inputs) |
| **GND**     | Pin 9           | GND            | Ground                 |
| **SDA**     | Pin 3           | GPIO 2 (SDA1)  | I2C Data (3.3V logic)  |
| **SCL**     | Pin 5           | GPIO 3 (SCL1)  | I2C Clock (3.3V logic) |
| **ADDR**    | → GND           | —              | Address = 0x48         |
| **A0**      | ← ACS712T OUT   | —              | Current sensor input   |
| **A1**      | ← ZMPT101B OUT  | —              | Voltage sensor input   |

> ⚠️ **Caution**: Since ADS1115 is now powered by 5V, ensure your module's I2C pull-up resistors (if any) are not pulling SDA/SCL to 5V. RPi pins are 3.3V only.
> ⚠️ Enable I2C: `sudo raspi-config` → Interface Options → I2C → Yes → Reboot

### ADS1115 Required Setup
```bash
# Verify I2C is working
sudo i2cdetect -y 1
# Should show 0x48
```

---

## 3. ACS712T-30A Current Sensor → ADS1115

The ACS712T outputs 0–5V. Note that if ADS1115 is powered at 3.3V, its inputs should ideally stay below 3.3V. 

```
                 ACS712T
              ┌───────────┐
  Pump Live ──┤ IP+   IP- ├── Pump Load
              │           │
      5V   ───┤ VCC       │
      GND  ───┤ GND  OUT ─┼────────────── → ADS1115 A0
              └───────────┘
```

**Scaling**: V_adc = V_out
- At 0A: V_out = 2.5V → V_adc = 2.5V
- At 30A: V_out = 4.48V → V_adc = 4.48V (No clipping since ADS1115 VDD = 5V)

### ACS712T Power
| Pin   | Connection        |
|-------|-------------------|
| VCC   | 5V (RPi Pin 2)    |
| GND   | GND (RPi Pin 14)  |
| OUT   | Direct to ADS1115 A0 |

> ⚠️ The ACS712T measures current through the **IP+ / IP-** terminals.
> Route one of the pump's live wires through these terminals.

---

## 4. ZMPT101B Voltage Sensor → ADS1115

```
              ZMPT101B
           ┌────────────┐
  AC Live ─┤            ├─ AC Neutral (or same Live)
           │            │
    5V  ───┤ VCC   OUT ─┼──────────────── → ADS1115 A1
    GND ───┤ GND        │
           └────────────┘
```

### ZMPT101B Power
| Pin   | Connection        |
|-------|-------------------|
| VCC   | 5V (RPi Pin 4)    |
| GND   | GND (RPi Pin 14)  |
| OUT   | Direct to ADS1115 A1 |

> ⚠️ **ZMPT101B must be calibrated**: Compare its reading with a known multimeter.
> Adjust `ZMPT101B_CAL_FACTOR` in `tank_config.py`.

---

## 5. RPi → 2-Channel Relay Module

| Relay Pin | RPi Physical Pin | RPi GPIO (BCM) | Function              |
|-----------|-----------------|----------------|-----------------------|
| **VCC**   | Pin 2           | 5V             | Relay power           |
| **GND**   | Pin 20          | GND            | Ground                |
| **IN1**   | Pin 11          | GPIO 17        | **Pump ON/OFF**       |
| **IN2**   | Pin 13          | GPIO 27        | Spare / inlet valve   |

> Most relay modules are **active-LOW** (IN=LOW → relay ON).
> Set `RELAY_ACTIVE_LOW = True` in `tank_config.py` (default).

### Relay → Pump Wiring
```
                    Relay Module
              ┌───────────────────┐
    GPIO 17 ──┤ IN1               │
              │          COM1  ───┼─── Mains Live (from MCB)
              │          NO1  ────┼─── Pump Live Input
              │                   │
    GPIO 27 ──┤ IN2               │
              │          COM2  ───┼─── (Spare)
              │          NO2  ────┼─── (Spare)
              │                   │
    5V     ───┤ VCC               │
    GND    ───┤ GND               │
              └───────────────────┘
```

> **NO** = Normally Open (pump OFF when relay is not energised = safe default)
> ⚠️ Use a relay rated for your pump's current (typically 10A+ for pump motors).

---

## 6. Manual Override Buttons

Two normally-open momentary push buttons with internal pull-ups.

| Button          | RPi Physical Pin | RPi GPIO (BCM) | Function        |
|-----------------|-----------------|----------------|-----------------|
| **Force ON**    | Pin 15          | GPIO 22        | Override pump ON  |
| **Force OFF**   | Pin 29          | GPIO 5         | Override pump OFF |

### Wiring (each button)
```
    RPi GPIO pin ──── Button ──── GND (any GND pin)
       (pull-up enabled in software)
```

> Pressing the button pulls GPIO LOW → detected as pressed.
> Override auto-expires after 60 minutes (configurable).

---

## 7. Status LED

| LED              | RPi Physical Pin | RPi GPIO (BCM) | Notes              |
|------------------|-----------------|----------------|--------------------|
| **Pump Status**  | Pin 31          | GPIO 6         | ON = pump running  |

### Wiring
```
    GPIO 6 ── 330Ω resistor ── LED (+) ── LED (-) ── GND
```

---

## 8. Complete RPi GPIO Pin Map

```
                    RPi Zero 2W
              ┌─────────┬─────────┐
     3.3V [1] │ ●     ● │ [2] 5V       ← ADS1115/ACS712/ZMPT101B/Relay VCC
  I2C SDA [3] │ ●     ● │ [4] 5V
  I2C SCL [5] │ ●     ● │ [6] GND      ← Common ground
          [7] │ ○     ○ │ [8]
      GND [9] │ ●     ○ │ [10]
 RELAY P [11] │ ●     ○ │ [12]          GPIO 17 → Pump relay IN1
 RELAY V [13] │ ●     ○ │ [14] GND     GPIO 27 → Valve relay IN2
  BTN ON [15] │ ●     ○ │ [16]          GPIO 22 → Force ON button
     3.3V [17]│ ●     ● │ [18] DIO0    ← LoRa DIO0 (GPIO 24)
 SPI MOSI [19]│ ●     ○ │ [20] GND
 SPI MISO [21]│ ●     ● │ [22] RST     ← LoRa RST (GPIO 25)
  SPI SCK [23]│ ●     ● │ [24] SPI CE0 ← LoRa NSS (GPIO 8)
      GND [25]│ ●     ○ │ [26]
          [27]│ ○     ○ │ [28]
 BTN OFF [29] │ ●     ○ │ [30] GND     GPIO 5 → Force OFF button
  LED    [31] │ ●     ○ │ [32]          GPIO 6 → Status LED
          [33]│ ○     ○ │ [34] GND
          [35]│ ○     ○ │ [36]
          [37]│ ○     ○ │ [38]
      GND [39]│ ●     ○ │ [40]
              └─────────┴─────────┘

● = Used    ○ = Available
```

---

## 9. Shopping List (if missing)

| Item | Purpose | Approx. Price |
|------|---------|--------------|
| **ADS1115** 16-bit I2C ADC | Read ACS712T + ZMPT101B analog outputs | ₹150–250 |
| **2-channel relay module** (5V, optocoupler) | Control pump power | ₹80–120 |
| **Jumper wires** | Connections | ₹50 |
| **330 Ω resistor** (×1) | Status LED current limiter | ₹2 |
| **LED** (any colour) | Pump status indicator | ₹5 |
| **Push buttons** (×2) | Manual override ON/OFF | ₹10 |

> ⚠️ **ADS1115 is REQUIRED** for current/voltage sensing. Without it,
> the system will still work using LoRa pressure data only (degraded mode).

---

## 10. Software Setup on RPi

```bash
# 1. Enable SPI and I2C
sudo raspi-config
# → Interface Options → SPI → Yes
# → Interface Options → I2C → Yes
# → Reboot

# 2. Clone/copy project
cd ~
git clone <repo-url> Wilo-Water-Pump-Automation
cd Wilo-Water-Pump-Automation/embedded/rpi_receiver

# 3. Install Python dependencies
pip3 install -r requirements.txt

# 4. Test (dry-run, no GPIO needed)
python3 pump_controller.py --dry-run --verbose

# 5. Test LoRa reception (with ESP32 powered on)
python3 receiver.py

# 6. Run for real
python3 pump_controller.py --verbose

# 7. Install as system service (auto-start on boot)
sudo cp wilo-pump.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wilo-pump
sudo systemctl start wilo-pump
sudo journalctl -u wilo-pump -f   # watch logs
```

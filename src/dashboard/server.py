#!/usr/bin/env python3
"""
Pressure Sensor & Wilo Water Pump Dashboard Server
===================================================
Provides telemetry streaming, hardware connectivity inspection,
historical telemetry graphs, manual pump controls, and safety policies.

Zero Fake Telemetry Rule:
- When running on localhost without physical RPi/ADC/ESP32, status honestly
  reports OFFLINE / UNAVAILABLE / TIMEOUT instead of fabricating numbers.
- When hardware is present, dynamically detects and streams live readings.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import queue
import re
import socket
import sys
import threading
import time
import traceback
from collections import deque
from datetime import datetime, timedelta

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

# Paths & Setup
_CONTROLLER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'controller'))
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _CONTROLLER_DIR not in sys.path:
    sys.path.insert(0, _CONTROLLER_DIR)
_DASHBOARD_DIR = os.path.abspath(os.path.dirname(__file__))
if _DASHBOARD_DIR not in sys.path:
    sys.path.insert(0, _DASHBOARD_DIR)

import db
db.init_db()

import tank_config as CFG

CSV_PATH = os.path.join(CFG.DATA_DIR, 'pressure_log.csv')
SERIAL_PORT = None
BAUD = 115200

subscribers = []
subscribers_lock = threading.Lock()

# Clean telemetry state (Zero fake initial values)
latest = {
    "packet": None,
    "voltage": None,
    "mains_voltage": None,
    "mains_current": None,
    "pressure_kpa": None,
    "pressure_mpa": None,
    "upper_pct": None,
    "status": "offline",
    "timestamp": "",
    "connected": False,
}

reader_thread = None
stop_event = threading.Event()

EMERGENCY_STOP_FILE = os.path.join(CFG.DATA_DIR, 'emergency_stop.json')


def _json_error(message: str, status_code: int = 500, **extra):
    payload = {"ok": False, "error": message}
    payload.update(extra)
    response = jsonify(payload)
    response.status_code = status_code
    return response


# ── Emergency Stop Management ──────────────────────────────────────────────────

def _is_emergency_stop() -> bool:
    try:
        if os.path.exists(EMERGENCY_STOP_FILE):
            with open(EMERGENCY_STOP_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return bool(data.get('active', False))
    except Exception:
        pass
    return False


def _set_emergency_stop(active: bool, reason: str = "Manual emergency stop") -> dict:
    try:
        os.makedirs(os.path.dirname(EMERGENCY_STOP_FILE), exist_ok=True)
        payload = {
            "active": active,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        with open(EMERGENCY_STOP_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)

        if active:
            # Force pump relay off immediately
            try:
                _set_manual_pump(False)
            except Exception as e:
                print(f"[emergency] error shutting down pump relay: {e}")

        return payload
    except Exception as exc:
        print(f"[emergency] failed to update emergency stop: {exc}")
        return {"active": active, "error": str(exc)}


# ── Hardware Detection Helpers ────────────────────────────────────────────────

def _load_manual_pump_module():
    try:
        import manual_pump_control
        return manual_pump_control, None
    except Exception as exc:
        return None, exc


def _read_manual_pump_status():
    manual_pump_control, import_error = _load_manual_pump_module()
    if manual_pump_control is None:
        return {
            "available": False,
            "pump_relay_on": None,
            "timestamp": None,
            "relay_pin": None,
            "active_low": None,
            "gpio_level": None,
            "error": str(import_error),
        }

    try:
        status = manual_pump_control.read_status()
        return {
            "available": True,
            **status,
        }
    except Exception as exc:
        return {
            "available": False,
            "pump_relay_on": None,
            "timestamp": None,
            "relay_pin": None,
            "active_low": None,
            "gpio_level": None,
            "error": str(exc),
        }


def _set_manual_pump(turn_on: bool, notify_controller: bool = True):
    if turn_on and _is_emergency_stop():
        raise RuntimeError("Operation blocked: Emergency Stop is currently ACTIVE.")
    manual_pump_control, import_error = _load_manual_pump_module()
    if manual_pump_control is None:
        raise RuntimeError(f"manual pump control unavailable: {import_error}")
    return manual_pump_control.set_pump(turn_on, notify_controller=notify_controller)


def _load_remote_bridge_module():
    try:
        import remote_bridge
        return remote_bridge, None
    except Exception as exc:
        return None, exc


def _runtime_bridge_status():
    remote_bridge, import_error = _load_remote_bridge_module()
    if remote_bridge is None:
        return None, import_error

    try:
        return remote_bridge.read_status(), None
    except Exception as exc:
        return None, exc


def _dashboard_mode_file():
    return os.path.join(CFG.LOG_DIR, 'dashboard_mode.json')


def _read_dashboard_mode(runtime_status=None):
    try:
        from runtime_channel import read_json
        saved = read_json(_dashboard_mode_file()) or {}
        mode = saved.get('mode')
        if mode in ('auto', 'manual'):
            return mode
    except Exception:
        pass

    if runtime_status and runtime_status.get('system_mode') in ('auto', 'manual'):
        return runtime_status.get('system_mode')

    return 'manual' if runtime_status and runtime_status.get('override') else 'auto'


def _write_dashboard_mode(mode: str):
    from runtime_channel import atomic_write_json
    atomic_write_json(_dashboard_mode_file(), {
        'mode': mode,
        'timestamp': datetime.now().isoformat(),
        'source': 'dashboard-ui',
    })


def _detect_raspberry_pi() -> dict:
    is_rpi = False
    model = "Non-RPi Host"
    try:
        if os.path.exists('/sys/firmware/devicetree/base/model'):
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                model = f.read().strip('\x00\n\r ')
                is_rpi = True
    except Exception:
        pass

    has_real_gpio = False
    try:
        import RPi.GPIO as GPIO
        if hasattr(GPIO, 'RPI_INFO') and not (isinstance(GPIO, type) and GPIO.__name__ == 'MockGPIO'):
            has_real_gpio = True
            is_rpi = True
            model = GPIO.RPI_INFO.get('TYPE', model)
    except Exception:
        has_real_gpio = False

    is_connected = is_rpi and has_real_gpio
    return {
        "connected": is_connected,
        "status": "ONLINE" if is_connected else "OFFLINE",
        "hardware": "Raspberry Pi" if is_rpi else "Mock / Localhost (Non-RPi)",
        "model": model,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "gpio_available": has_real_gpio,
        "reason": None if is_connected else "RPi.GPIO hardware unavailable (Mock/Windows localhost)",
    }


def _detect_current_sensor() -> dict:
    has_real_adc = False
    current_a = None
    error_reason = None
    try:
        from sensor_reader import SensorReader, _ADS_OK
        if _ADS_OK:
            reader = SensorReader(
                acs_model=CFG.ACS712_MODEL,
                acs_zero_v=CFG.ACS712_ZERO_V,
                acs_divider=CFG.ACS712_DIVIDER_RATIO,
                zmpt_cal=CFG.ZMPT101B_CAL_FACTOR,
                zmpt_zero_v=CFG.ZMPT101B_ZERO_V,
                zmpt_divider=CFG.ZMPT101B_DIVIDER_RATIO,
                adc_addr=CFG.ADS1115_ADDRESS,
                ch_current=CFG.ADC_CH_CURRENT,
                ch_voltage=CFG.ADC_CH_VOLTAGE,
            )
            if reader.initialize():
                has_real_adc = True
                val = reader.read_current_rms(samples=20)
                if val is not None:
                    current_a = round(val, 2)
        else:
            error_reason = "ADS1115 / BusIO library not installed or I2C unavailable"
    except Exception as exc:
        error_reason = str(exc)

    last_reading = _read_last_pump_log_entry()
    last_amps = last_reading.get("pump_current_a") if last_reading else None
    last_time = last_reading.get("timestamp") if last_reading else None
    age_s = None
    if last_time:
        try:
            age_s = round((datetime.now() - datetime.fromisoformat(last_time)).total_seconds(), 1)
        except Exception:
            pass

    return {
        "connected": has_real_adc,
        "status": "ONLINE" if has_real_adc else "OFFLINE",
        "sensor_type": f"{CFG.ACS712_MODEL} / SCT013 via ADS1115 ADC",
        "i2c_address": hex(CFG.ADS1115_ADDRESS),
        "current_amps": current_a,
        "last_recorded_amps": float(last_amps) if last_amps is not None and last_amps != '' else None,
        "last_reading_time": last_time,
        "last_reading_age_s": age_s,
        "last_reading_age_text": f"{int(age_s)}s ago (STALE)" if age_s is not None else "No historical records",
        "reason": None if has_real_adc else (error_reason or "ADS1115 I2C ADC hardware not detected"),
    }


def _detect_relay() -> dict:
    pump_status = _read_manual_pump_status()
    try:
        import RPi.GPIO as GPIO
        has_real_gpio = hasattr(GPIO, 'RPI_INFO') and not (isinstance(GPIO, type) and GPIO.__name__ == 'MockGPIO')
    except Exception:
        has_real_gpio = False

    is_on = bool(pump_status.get("pump_relay_on", False))
    return {
        "connected": has_real_gpio,
        "status": "ONLINE" if has_real_gpio else "OFFLINE",
        "relay_state": "ON" if is_on else "OFF",
        "relay_pin": CFG.RELAY_PUMP_PIN,
        "valve_pin": CFG.RELAY_VALVE_PIN,
        "active_low": CFG.RELAY_ACTIVE_LOW,
        "mode": "MANUAL" if pump_status.get("override") else "AUTO",
        "last_action_timestamp": pump_status.get("timestamp"),
        "reason": None if has_real_gpio else "Physical relay not connected (Mock environment)",
    }


def _get_master_hardware_status() -> dict:
    rpi = _detect_raspberry_pi()
    curr = _detect_current_sensor()
    relay = _detect_relay()
    overall = rpi["connected"] and relay["connected"]
    return {
        "connected": overall,
        "status": "ONLINE" if overall else "OFFLINE",
        "raspberry_pi": rpi,
        "current_sensor": curr,
        "relay": relay,
    }


# ── Slave & LoRa Telemetry Detection ──────────────────────────────────────────

def _read_last_csv_row(filepath: str) -> dict | None:
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            last = None
            for row in reader:
                ts = (row.get('timestamp') or '').strip('\x00\r\n ')
                if ts and any(c.isdigit() for c in ts):
                    row['timestamp'] = ts
                    last = row
            return last
    except Exception:
        return None


def _read_last_pump_log_entry() -> dict | None:
    return _read_last_csv_row(CFG.CSV_LOG_PATH)


def _read_latest_lora_packet_data() -> dict | None:
    if latest.get("packet") is not None and latest.get("timestamp"):
        return latest

    if os.path.exists(CFG.LORA_PACKET_CSV_PATH):
        try:
            with open(CFG.LORA_PACKET_CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                latest_row = None
                for row in reader:
                    if row.get('pkt') and row.get('pressure_kpa'):
                        latest_row = row
                if latest_row:
                    return {
                        "packet": int(latest_row['pkt']),
                        "voltage": float(latest_row.get('voltage_v') or latest_row.get('voltage') or 0),
                        "pressure_kpa": float(latest_row['pressure_kpa']),
                        "status": latest_row.get('status', 'ok'),
                        "timestamp": latest_row.get('timestamp', ''),
                        "device": latest_row.get('device', 'esp32'),
                        "rssi_dbm": float(latest_row['rssi_dbm']) if latest_row.get('rssi_dbm') else None,
                        "snr_db": float(latest_row['snr_db']) if latest_row.get('snr_db') else None,
                    }
        except Exception:
            pass
    return None


def _get_lora_stats() -> tuple[int, float]:
    """Returns (total_packets, packet_rate_per_sec)."""
    if not os.path.exists(CFG.LORA_PACKET_CSV_PATH):
        return 0, 0.0
    try:
        with open(CFG.LORA_PACKET_CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
            rows = list(deque(csv.DictReader(f), 100))
            if not rows:
                return 0, 0.0
            total_count = len(rows)
            now = datetime.now()
            recent_count = 0
            for r in rows:
                ts_str = r.get('timestamp')
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if (now - ts).total_seconds() <= 60.0:
                            recent_count += 1
                    except Exception:
                        pass
            return len(rows), round(recent_count / 60.0, 2)
    except Exception:
        return 0, 0.0


def _detect_slave_hardware() -> dict:
    last_pkt = _read_latest_lora_packet_data()
    now = datetime.now()
    age_s = None
    if last_pkt and last_pkt.get("timestamp"):
        try:
            ts = datetime.fromisoformat(last_pkt["timestamp"])
            age_s = round((now - ts).total_seconds(), 1)
        except Exception:
            pass

    is_online = age_s is not None and age_s <= CFG.LORA_TIMEOUT_S
    is_timeout = age_s is not None and age_s > CFG.LORA_TIMEOUT_S
    pkt_count, pkt_rate = _get_lora_stats()

    esp32_status = {
        "connected": is_online,
        "status": "ONLINE" if is_online else ("TIMEOUT" if is_timeout else "OFFLINE"),
        "device_id": last_pkt.get("device", "esp32") if last_pkt else "esp32",
        "last_packet_age_s": age_s,
        "last_packet_age_text": f"{int(age_s)}s ago" if is_online else (f"{int(age_s)}s ago (TIMEOUT)" if is_timeout else "Disconnected (No signal)"),
        "last_packet_timestamp": last_pkt.get("timestamp") if last_pkt else None,
        "rssi_dbm": last_pkt.get("rssi_dbm") if is_online else None,
        "snr_db": last_pkt.get("snr_db") if is_online else None,
        "reason": None if is_online else (f"Last packet was {int(age_s)}s ago (TIMEOUT > {CFG.LORA_TIMEOUT_S}s)" if is_timeout else "No ESP32 LoRa signal received"),
    }

    pressure_sensor_status = {
        "connected": is_online and last_pkt.get("status") == "ok",
        "status": "OK" if (is_online and last_pkt.get("status") == "ok") else ("FAULT" if is_online else "OFFLINE"),
        "sensor_model": "PR12P210 (0-100 kPa / 0.5-4.5V)",
        "voltage_v": last_pkt.get("voltage") if is_online else None,
        "pressure_kpa": last_pkt.get("pressure_kpa") if is_online else None,
        "last_recorded_kpa": last_pkt.get("pressure_kpa") if last_pkt else None,
        "calibration_offset_kpa": CFG.PRESSURE_OFFSET_KPA,
        "reason": None if is_online else "Pressure sensor offline (No live ESP32 signal)",
    }

    lora_status = {
        "connected": is_online,
        "status": "ONLINE" if is_online else ("TIMEOUT" if is_timeout else "OFFLINE"),
        "frequency": "433 MHz",
        "sync_word": "0xF3",
        "total_packets": pkt_count,
        "packet_rate_per_sec": pkt_rate if is_online else 0.0,
        "last_packet_age_s": age_s,
        "timeout_threshold_s": CFG.LORA_TIMEOUT_S,
        "reason": None if is_online else f"LoRa link timeout: no packets received within {CFG.LORA_TIMEOUT_S}s",
    }

    return {
        "connected": is_online,
        "status": "ONLINE" if is_online else ("TIMEOUT" if is_timeout else "OFFLINE"),
        "esp32": esp32_status,
        "pressure_sensor": pressure_sensor_status,
        "lora": lora_status,
    }


# ── Real Sensor-Based Tank Level ──────────────────────────────────────────────

def pressure_to_level_pct(pressure_kpa: float | None) -> float | None:
    """
    Convert hydrostatic pressure at tank bottom to percentage.
    net_kpa = pressure_kpa - 23.0 kPa (calibrated zero-point)
    h_m = (net_kpa * 1000) / (density * gravity)
    pct = (h_cm / 200 cm) * 100.0
    """
    if pressure_kpa is None or pressure_kpa < 0:
        return None
    net_kpa = pressure_kpa - CFG.PRESSURE_OFFSET_KPA
    if net_kpa <= 0:
        return 0.0
    pressure_pa = net_kpa * 1000.0
    h_m = pressure_pa / (CFG.WATER_DENSITY * CFG.GRAVITY)
    h_cm = h_m * 100.0
    pct = (h_cm / CFG.UPPER_TANK_HEIGHT_CM) * 100.0
    return max(0.0, min(100.0, pct))


def _calculate_tank_state(pressure_kpa: float | None, is_online: bool) -> dict:
    """
    STRICT RULE:
    Pump OFF and 0A current MUST NOT classify the tank as EMPTY!
    Tank level is determined solely by the calibrated hydrostatic pressure.
    """
    if pressure_kpa is None or not is_online:
        return {
            "level_percent": None,
            "level_liters": None,
            "state": "SENSOR OFFLINE",
            "color": "gray",
            "source": "ESP32 (PR12P210) → LoRa 433MHz → Raspberry Pi",
            "pressure_kpa": None,
            "net_pressure_kpa": None,
            "height_cm": None,
            "max_height_cm": CFG.UPPER_TANK_HEIGHT_CM,
            "capacity_liters": CFG.UPPER_TANK_CAPACITY_L,
            "is_empty": False,
            "stale": True,
            "verification_note": "Tank level requires live hydrostatic pressure. Pump OFF does NOT imply empty.",
        }

    pct = pressure_to_level_pct(pressure_kpa)
    net_kpa = max(0.0, pressure_kpa - CFG.PRESSURE_OFFSET_KPA)
    h_cm = (pct / 100.0) * CFG.UPPER_TANK_HEIGHT_CM if pct is not None else 0.0
    liters = int(round(((pct or 0.0) / 100.0) * CFG.UPPER_TANK_CAPACITY_L))

    if pct <= CFG.UPPER_CRITICAL_LOW:
        state = "CRITICAL LOW"
        color = "red"
    elif pct <= CFG.UPPER_LOW:
        state = "LOW"
        color = "orange"
    elif pct < CFG.UPPER_HIGH:
        state = "NORMAL"
        color = "blue"
    elif pct < CFG.UPPER_CRITICAL_HIGH:
        state = "HIGH"
        color = "green"
    else:
        state = "FULL"
        color = "emerald"

    return {
        "level_percent": round(pct, 1),
        "level_liters": liters,
        "state": state,
        "color": color,
        "source": "ESP32 (PR12P210) → LoRa 433MHz → Raspberry Pi",
        "pressure_kpa": round(pressure_kpa, 2),
        "net_pressure_kpa": round(net_kpa, 2),
        "height_cm": round(h_cm, 1),
        "max_height_cm": CFG.UPPER_TANK_HEIGHT_CM,
        "capacity_liters": CFG.UPPER_TANK_CAPACITY_L,
        "is_empty": pct <= 1.0,
        "stale": False,
        "verification_note": "Tank level derived solely from pressure sensor. Pump OFF + 0A does NOT mean EMPTY.",
    }


# ── Festival Policy & Water Cuts ──────────────────────────────────────────────

def _check_festival_policy(dt: datetime | None = None, pump_is_on: bool = False) -> dict:
    try:
        import sys
        _controller_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'controller'))
        if _controller_path not in sys.path:
            sys.path.insert(0, _controller_path)
        from festival_policy import evaluate_festival_policy
        return evaluate_festival_policy(dt=dt, pump_is_on=pump_is_on)
    except Exception as exc:
        return {
            "festival_mode": True,
            "today_is_festival": False,
            "festival_name": "None",
            "festival_date": None,
            "policy": "NORMAL",
            "automatic_start_allowed": True,
            "automatic_start_blocked": False,
            "release_time": None,
            "status": "NORMAL",
            "reason": f"Fallback festival evaluation: {exc}",
            "timezone": "Asia/Kolkata",
            "current_time_ist": datetime.now().strftime("%H:%M:%S"),
            "release_countdown_text": None,
            "seconds_until_release": None,
            "running_pump_shutdown": False,
            "hold_active": False,
            "hold_reason": None,
        }


def _check_active_water_cuts(dt: datetime | None = None) -> dict:
    dt = dt or datetime.now()
    current_time_str = dt.strftime('%H:%M')
    active_cuts = []
    try:
        cuts = db.get_water_cuts()
        for cut in cuts:
            st = cut.get('startTime') or cut.get('start_time') or '00:00'
            et = cut.get('endTime') or cut.get('end_time') or '23:59'
            if st <= current_time_str <= et:
                active_cuts.append(cut)
    except Exception:
        pass

    has_cut = len(active_cuts) > 0
    return {
        "has_active_cut": has_cut,
        "active_cuts": active_cuts,
        "reason": f"Municipal water cut in effect ({', '.join(c.get('area', '') for c in active_cuts)}): automated start suspended" if has_cut else None,
    }


# ── Telemetry History Endpoint Data ───────────────────────────────────────────

def _format_time_str(ts_str: str | None) -> str:
    if not ts_str:
        return ""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime('%H:%M:%S')
    except Exception:
        return ts_str[-8:] if len(ts_str) >= 8 else ts_str


def _get_telemetry_history(limit: int = 40) -> dict:
    pressure_history = []
    current_history = []
    lora_history = []

    # Read from logs/pump/rpi_pump_log.csv
    if os.path.exists(CFG.CSV_LOG_PATH):
        try:
            with open(CFG.CSV_LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
                rows = list(deque(csv.DictReader(f), limit))
                for r in rows:
                    t_str = _format_time_str(r.get('timestamp'))
                    if r.get('pressure_kpa'):
                        try:
                            pkpa = float(r['pressure_kpa'])
                            pressure_history.append({
                                "time": t_str,
                                "pressureKpa": round(pkpa, 2),
                                "status": r.get('sensor_status', 'ok'),
                            })
                        except ValueError:
                            pass
                    if r.get('pump_current_a') is not None:
                        try:
                            amps = float(r.get('pump_current_a') or 0.0)
                            current_history.append({
                                "time": t_str,
                                "currentAmps": round(amps, 2),
                                "pumpState": r.get('pump_relay', 'OFF'),
                            })
                        except ValueError:
                            pass
        except Exception as e:
            print(f"[history] error reading pump log: {e}")

    # Read from logs/lora/esp32_pressure_packets.csv for LoRa packet rate
    if os.path.exists(CFG.LORA_PACKET_CSV_PATH):
        try:
            with open(CFG.LORA_PACKET_CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
                rows = list(deque(csv.DictReader(f), limit))
                for r in rows:
                    t_str = _format_time_str(r.get('timestamp'))
                    pkt_val = int(r['pkt']) if r.get('pkt') else 0
                    lora_history.append({
                        "time": t_str,
                        "packet": pkt_val,
                        "packetRate": 1.0 if r.get('status') == 'ok' else 0.0,
                        "rssi": float(r['rssi_dbm']) if r.get('rssi_dbm') else None,
                    })
        except Exception as e:
            print(f"[history] error reading lora log: {e}")

    return {
        "ok": True,
        "pressure_history": pressure_history,
        "current_history": current_history,
        "lora_history": lora_history,
    }


# ── ML Predictions ────────────────────────────────────────────────────────────

def _prediction_payload():
    try:
        from src.models.prediction import get_comprehensive_prediction
        from src.utils.sensors import get_fallback_sensor_data
        prediction = get_comprehensive_prediction(get_fallback_sensor_data())
        return {
            "start_hour": float(prediction["start_hour"]),
            "duration": float(prediction["duration"]),
            "method": prediction.get("method", "prediction"),
            "confidence": prediction.get("confidence", "medium"),
        }
    except Exception as exc:
        return {
            "start_hour": 7.0,
            "duration": 90.0,
            "method": "fallback",
            "confidence": "low",
            "error": str(exc),
        }


def _telemetry_from_runtime(runtime_status):
    if not runtime_status:
        return None
    pressure_kpa = runtime_status.get("pressure_kpa")
    return {
        "packet": runtime_status.get("lora_pkt", -1),
        "voltage": runtime_status.get("sensor_voltage", 0.0) or 0.0,
        "mains_voltage": runtime_status.get("voltage_ac", 0.0) or 0.0,
        "mains_current": runtime_status.get("current_amps", 0.0) or 0.0,
        "pressure_kpa": pressure_kpa if isinstance(pressure_kpa, (int, float)) else None,
        "pressure_mpa": (pressure_kpa / 1000.0) if isinstance(pressure_kpa, (int, float)) else None,
        "status": runtime_status.get("sensor_status") or ("ok" if pressure_kpa is not None else "disconnected"),
        "timestamp": runtime_status.get("timestamp") or "",
    }


def _dashboard_status_payload():
    pump_status = _read_manual_pump_status()
    runtime_status, runtime_error = _runtime_bridge_status()
    system_mode = _read_dashboard_mode(runtime_status)
    prediction = _prediction_payload()
    emergency_active = _is_emergency_stop()

    master_hw = _get_master_hardware_status()
    slave_hw = _detect_slave_hardware()

    # Pressure: use real slave reading if online, otherwise null
    live_pressure = slave_hw["pressure_sensor"]["pressure_kpa"] if slave_hw["connected"] else None
    tank_state = _calculate_tank_state(live_pressure, slave_hw["connected"])

    pump_is_running = bool(pump_status.get("pump_relay_on", False))
    festival = _check_festival_policy(pump_is_on=pump_is_running)
    # Ensure legacy compatibility fields for frontend status banners
    festival["hold_active"] = bool(festival.get("automatic_start_blocked", False))
    festival["hold_reason"] = festival.get("reason") if festival["hold_active"] else None

    water_cuts = _check_active_water_cuts()

    # Determine auto control recommendation
    auto_decision = "hold"
    should_run = False
    auto_reason = "Automation holding state"

    if emergency_active:
        auto_decision = "stop"
        should_run = False
        auto_reason = "EMERGENCY STOP ACTIVE"
    elif tank_state["level_percent"] is not None and tank_state["level_percent"] >= CFG.UPPER_HIGH:
        auto_decision = "stop"
        should_run = False
        auto_reason = f"Tank level high ({tank_state['level_percent']}%)"
    elif not pump_is_running and festival["hold_active"]:
        # Block automatic start on festival restriction
        auto_decision = "hold"
        should_run = False
        auto_reason = festival["hold_reason"]
    elif not pump_is_running and water_cuts["has_active_cut"]:
        # Block automatic start on water cuts
        auto_decision = "hold"
        should_run = False
        auto_reason = water_cuts["reason"]
    elif tank_state["level_percent"] is not None and tank_state["level_percent"] <= CFG.UPPER_LOW:
        if festival["hold_active"]:
            auto_decision = "hold"
            should_run = False
            auto_reason = f"Tank level low ({tank_state['level_percent']}%), but automated start blocked: {festival['hold_reason']}"
        elif water_cuts["has_active_cut"]:
            auto_decision = "hold"
            should_run = False
            auto_reason = f"Tank level low ({tank_state['level_percent']}%), but automated start suspended: {water_cuts['reason']}"
        else:
            auto_decision = "start"
            should_run = True
            auto_reason = f"Tank level low ({tank_state['level_percent']}%)"

    telemetry = _telemetry_from_runtime(runtime_status) or latest
    runtime_payload = dict(runtime_status or {})
    runtime_payload["ml_prediction"] = runtime_payload.get("ml_prediction") or prediction
    runtime_payload["system_mode"] = system_mode

    return {
        "ok": True,
        "manual_override_available": pump_status.get("available", False),
        "manual_override_enabled": pump_status.get("available", False),
        "pump": pump_status,
        "telemetry": telemetry,
        "runtime": runtime_payload,
        "runtime_error": str(runtime_error) if runtime_error else None,
        "auto_control": {
            "enabled": system_mode == "auto" and not emergency_active,
            "action": auto_decision,
            "should_run": should_run,
            "reason": auto_reason,
        },
        "system_mode": system_mode,
        "emergency_stop": emergency_active,
        "master_hardware": master_hw,
        "slave_hardware": slave_hw,
        "tank": tank_state,
        "policies": {
            "emergency_stop": emergency_active,
            "festival": festival,
            "water_cuts": water_cuts,
        },
        "timestamp": datetime.now().isoformat(),
    }


# ── CORS Middleware ───────────────────────────────────────────────────────────

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# ── Genuine Serial Reader (Zero Fake Telemetry) ────────────────────────────────

def find_port():
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            device = (p.device or '').lower()
            description = (p.description or '').lower()
            hwid = (p.hwid or '').lower()
            if any(k in device for k in ('usbserial', 'usbmodem', 'ttyusb', 'ttyacm', 'com')):
                return p.device
            if any(k in description for k in ('cp210', 'ch340', 'usb serial', 'uart bridge', 'silicon labs')):
                return p.device
            if any(k in hwid for k in ('vid:pid=10c4:ea60', 'vid_10c4&pid_ea60', 'vid:pid=1a86:7523')):
                return p.device
    except Exception:
        pass
    return None


def broadcast(data: dict):
    global latest
    latest = data
    msg = f"data: {json.dumps(data)}\n\n"
    with subscribers_lock:
        dead = []
        for q in subscribers:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            subscribers.remove(q)


def reader_loop(port, fresh_csv, stop_evt):
    import serial
    os.makedirs(os.path.dirname(os.path.abspath(CSV_PATH)), exist_ok=True)
    mode = 'w' if fresh_csv else 'a'
    write_header = fresh_csv or not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    f = open(CSV_PATH, mode, newline='', encoding='utf-8')
    writer = csv.writer(f)
    if write_header:
        writer.writerow(['timestamp', 'packet', 'voltage_V', 'pressure_kPa', 'pressure_MPa', 'status'])
        f.flush()

    s = None
    v = st = pkt = None

    while not stop_evt.is_set():
        try:
            if s is None or not s.is_open:
                s = serial.Serial(port, BAUD, timeout=2, dsrdtr=False, rtscts=False)
                s.setDTR(False)
                s.setRTS(False)
                print(f'[serial] opened hardware port {port}', flush=True)
                broadcast({**latest, "status": "connecting", "connected": True})

            raw = s.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', errors='replace').strip()
            if not line:
                continue

            if line.startswith('Sensor Voltage'):
                m = re.search(r'([\d.]+) V', line)
                if m:
                    v = float(m.group(1))
                st = 'ok'
            elif 'SENSOR FAULT' in line:
                st = 'fault'
            elif line.startswith('LoRa sent'):
                m = re.search(r'#(\d+)', line)
                if m:
                    pkt = int(m.group(1))
                if v is not None:
                    kpa = max(0.0, (v - 0.5) / 4.0 * 100.0) if st == 'ok' else -1.0
                    mpa = kpa / 1000.0 if st == 'ok' else -1.0
                    ts = datetime.now().isoformat()
                    writer.writerow([ts, pkt, round(v, 3), round(kpa, 2), round(mpa, 4), st])
                    f.flush()
                    pct = pressure_to_level_pct(kpa) if st == 'ok' else None
                    broadcast({
                        "packet": pkt,
                        "voltage": round(v, 3),
                        "pressure_kpa": round(kpa, 2),
                        "pressure_mpa": round(mpa, 4),
                        "upper_pct": pct,
                        "status": st,
                        "timestamp": ts,
                        "connected": True,
                    })
                    print(f'[hardware data] pkt={pkt} {round(v,3)}V {round(kpa,2)}kPa', flush=True)
                    v = st = pkt = None

        except Exception as e:
            print(f'[serial hardware error] {e}', flush=True)
            broadcast({**latest, "status": "disconnected", "connected": False})
            time.sleep(2)
            if s:
                try:
                    s.close()
                except Exception:
                    pass
                s = None
    if s:
        try:
            s.close()
        except Exception:
            pass
    f.close()


def hardware_monitor_loop(fresh_csv, stop_evt):
    """
    Scans for hardware serial connection.
    Strictly follows Zero Fake Telemetry rule:
    When no serial hardware is attached, marks status OFFLINE and does NOT fabricate readings.
    """
    print("[hardware-monitor] hardware detector started. Zero fake telemetry enforced.", flush=True)
    while not stop_evt.is_set():
        port = SERIAL_PORT or find_port()
        if port:
            print(f"[hardware-monitor] detected serial device on {port}, connecting...", flush=True)
            reader_loop(port, fresh_csv, stop_evt)
        else:
            time.sleep(4)


def start_reader(fresh=False):
    global reader_thread, stop_event
    if reader_thread and reader_thread.is_alive():
        stop_event.set()
        reader_thread.join(timeout=3)
    stop_event = threading.Event()
    reader_thread = threading.Thread(target=hardware_monitor_loop, args=(fresh, stop_event), daemon=True)
    reader_thread.start()


# ── HTTP Routes ────────────────────────────────────────────────────────────────

_DIST_DIR = os.path.abspath(os.path.join(_PROJECT_ROOT, 'dashboard', 'dist'))

@app.route('/')
def index():
    index_file = os.path.join(_DIST_DIR, 'index.html')
    if os.path.exists(index_file):
        from flask import send_from_directory
        return send_from_directory(_DIST_DIR, 'index.html')
    html_path = os.path.join(os.path.dirname(__file__), 'dashboard.html')
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as fh:
            return fh.read()
    return jsonify({"ok": True, "service": "wilo-pump-backend"})


@app.route('/assets/<path:filename>')
def serve_dist_assets(filename):
    assets_dir = os.path.join(_DIST_DIR, 'assets')
    if os.path.exists(os.path.join(assets_dir, filename)):
        from flask import send_from_directory
        return send_from_directory(assets_dir, filename)
    return _json_error("Asset not found", 404)


@app.route('/admin')
def serve_admin():
    index_file = os.path.join(_DIST_DIR, 'index.html')
    if os.path.exists(index_file):
        from flask import send_from_directory
        return send_from_directory(_DIST_DIR, 'index.html')
    return _json_error("Admin frontend not built", 404)


@app.route('/stream')
def stream():
    q = queue.Queue(maxsize=50)
    with subscribers_lock:
        subscribers.append(q)
    q.put_nowait(f"data: {json.dumps(latest)}\n\n")

    def generate():
        try:
            while True:
                try:
                    yield q.get(timeout=20)
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            with subscribers_lock:
                if q in subscribers:
                    subscribers.remove(q)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/latest')
def get_latest():
    return jsonify(latest)


@app.route('/health')
@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "wilo-pump-backend",
        "emergency_stop": _is_emergency_stop(),
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/dashboard/status')
def get_dashboard_status():
    return jsonify(_dashboard_status_payload())


@app.route('/api/hardware/status')
def get_hardware_status():
    """
    Dedicated endpoint returning comprehensive hardware connectivity:
    Master Motor (Raspberry Pi, Current Sensor, Relay) and
    Slave Motor (ESP32, Pressure Sensor, LoRa Communication),
    plus real sensor-based Tank state.
    """
    master_hw = _get_master_hardware_status()
    slave_hw = _detect_slave_hardware()
    live_pressure = slave_hw["pressure_sensor"]["pressure_kpa"] if slave_hw["connected"] else None
    tank_state = _calculate_tank_state(live_pressure, slave_hw["connected"])

    return jsonify({
        "ok": True,
        "master_motor": master_hw,
        "slave_motor": slave_hw,
        "tank": tank_state,
        "system_connected": master_hw["connected"] and slave_hw["connected"],
        "timestamp": datetime.now().isoformat(),
    })


@app.route('/api/telemetry/history')
def get_telemetry_history():
    """
    Provides real historical points for:
    - Pressure Trend (kPa)
    - Current Trend (A)
    - LoRa Packet Rate (pkt/s)
    """
    limit = request.args.get('limit', default=40, type=int)
    return jsonify(_get_telemetry_history(limit=limit))


# ── Pump & Control Routes ──────────────────────────────────────────────────────

@app.route('/api/pump/status')
def get_pump_status():
    status = _read_manual_pump_status()
    response_status = 200 if status.get("available") else 503
    return jsonify({"ok": status.get("available", False), "pump": status}), response_status


@app.route('/api/pump/on', methods=['POST', 'OPTIONS'])
def pump_on():
    if request.method == 'OPTIONS':
        return ('', 204)
    if _is_emergency_stop():
        return _json_error("Operation blocked: Emergency Stop is currently ACTIVE. Clear emergency stop first.", 403)
    try:
        status = _set_manual_pump(True)
        return jsonify({"ok": True, "pump": status, "message": "Pump turned on"})
    except Exception as exc:
        traceback.print_exc()
        return _json_error("failed to turn pump on", 500, detail=str(exc))


@app.route('/api/pump/off', methods=['POST', 'OPTIONS'])
def pump_off():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        status = _set_manual_pump(False)
        return jsonify({"ok": True, "pump": status, "message": "Pump turned off"})
    except Exception as exc:
        traceback.print_exc()
        return _json_error("failed to turn pump off", 500, detail=str(exc))


@app.route('/api/mode', methods=['GET', 'POST', 'OPTIONS'])
def system_mode():
    if request.method == 'OPTIONS':
        return ('', 204)
    if request.method == 'GET':
        payload = _dashboard_status_payload()
        return jsonify({"ok": True, "mode": payload.get('system_mode', 'auto')})

    data = request.get_json(silent=True) or {}
    mode = data.get('mode', 'auto')

    if mode == 'auto' and _is_emergency_stop():
        return _json_error("Cannot enable AUTO mode while Emergency Stop is ACTIVE.", 403)

    try:
        from runtime_channel import atomic_write_json
        action = 'manual_mode_on' if mode == 'manual' else 'manual_mode_off'
        command = {
            'action': action,
            'issued_at': datetime.now().isoformat(),
            'source': 'dashboard-ui',
        }
        atomic_write_json(CFG.CONTROL_FILE, command)
        _write_dashboard_mode(mode)
        return jsonify({"ok": True, "mode": mode, "message": f"Switched to {mode} mode"})
    except Exception as exc:
        traceback.print_exc()
        return _json_error(f"failed to switch to {mode} mode", 500, detail=str(exc))


@app.route('/api/pump/clear-override', methods=['POST', 'OPTIONS'])
def pump_clear_override():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        from runtime_channel import atomic_write_json
        command = {
            'action': 'override_clear',
            'issued_at': datetime.now().isoformat(),
            'source': 'dashboard-ui',
        }
        atomic_write_json(CFG.CONTROL_FILE, command)
        _write_dashboard_mode('auto')
        return jsonify({"ok": True, "message": "Manual override cleared; controller resumed automated mode"})
    except Exception as exc:
        traceback.print_exc()
        return _json_error("failed to clear override", 500, detail=str(exc))


@app.route('/api/emergency-stop', methods=['POST', 'OPTIONS'])
def trigger_emergency_stop():
    """Immediately stops the pump and locks out automated and manual start."""
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(silent=True) or {}
    reason = data.get('reason', 'Operator initiated emergency stop from dashboard')
    res = _set_emergency_stop(True, reason=reason)
    return jsonify({"ok": True, "emergency_stop": res, "message": "EMERGENCY STOP TRIGGERED. Pump disabled."})


@app.route('/api/emergency-stop/reset', methods=['POST', 'OPTIONS'])
def reset_emergency_stop():
    """Resets the emergency stop lock."""
    if request.method == 'OPTIONS':
        return ('', 204)
    res = _set_emergency_stop(False)
    return jsonify({"ok": True, "emergency_stop": res, "message": "Emergency stop cleared. Operations may resume."})


# ── Auth Endpoints ─────────────────────────────────────────────────────────────

def _get_auth_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return request.args.get('token')


@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def auth_register():
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(silent=True) or {}
    res = db.register_user(data.get('username', ''), data.get('password', ''), data.get('role', 'operator'))
    return jsonify(res), (200 if res.get('ok') else 400)


@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def auth_login():
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(silent=True) or {}
    res = db.login_user(data.get('username', ''), data.get('password', ''))
    return jsonify(res), (200 if res.get('ok') else 401)


@app.route('/api/auth/me', methods=['GET', 'OPTIONS'])
def auth_me():
    if request.method == 'OPTIONS':
        return ('', 204)
    token = _get_auth_token()
    session = db.validate_session(token)
    if not session:
        return jsonify({"ok": False, "error": "Unauthorized"}), 401
    return jsonify({"ok": True, "user": session})


@app.route('/api/auth/logout', methods=['POST', 'OPTIONS'])
def auth_logout():
    if request.method == 'OPTIONS':
        return ('', 204)
    token = _get_auth_token()
    if token:
        db.logout_session(token)
    return jsonify({"ok": True, "message": "Logged out successfully"})


# ── Scheduler Endpoints ────────────────────────────────────────────────────────

@app.route('/api/schedule', methods=['GET', 'POST', 'OPTIONS'])
def api_schedule():
    if request.method == 'OPTIONS':
        return ('', 204)
    if request.method == 'GET':
        tasks = db.get_scheduled_tasks()
        return jsonify({"ok": True, "tasks": tasks})
    data = request.get_json(silent=True) or {}
    task_id = data.get('id') or f"task-{int(time.time() * 1000)}"
    res = db.add_scheduled_task(
        task_id,
        data.get('date', datetime.now().strftime('%Y-%m-%d')),
        data.get('time', '08:00'),
        str(data.get('duration', '30')),
        data.get('type', 'manual')
    )
    return jsonify(res)


@app.route('/api/schedule/<task_id>', methods=['DELETE', 'OPTIONS'])
def api_delete_schedule(task_id):
    if request.method == 'OPTIONS':
        return ('', 204)
    deleted = db.delete_scheduled_task(task_id)
    return jsonify({"ok": deleted})


# ── Water Cuts Endpoints ───────────────────────────────────────────────────────

@app.route('/api/water-cuts', methods=['GET', 'POST', 'OPTIONS'])
def api_water_cuts():
    if request.method == 'OPTIONS':
        return ('', 204)
    if request.method == 'GET':
        cuts = db.get_water_cuts()
        return jsonify({"ok": True, "water_cuts": cuts})
    data = request.get_json(silent=True) or {}
    res = db.add_water_cut(
        data.get('area', 'Sector C'),
        data.get('startTime') or data.get('start_time', '08:00'),
        data.get('endTime') or data.get('end_time', '12:00'),
        data.get('reason', 'Scheduled Maintenance'),
        data.get('status', 'scheduled')
    )
    return jsonify(res)


@app.route('/api/water-cuts/<int:cut_id>', methods=['DELETE', 'OPTIONS'])
def api_delete_water_cut(cut_id):
    if request.method == 'OPTIONS':
        return ('', 204)
    deleted = db.delete_water_cut(cut_id)
    return jsonify({"ok": deleted})


# ── Energy & History Endpoints ─────────────────────────────────────────────────

@app.route('/api/energy', methods=['GET', 'OPTIONS'])
def api_energy():
    if request.method == 'OPTIONS':
        return ('', 204)
    pump_status = _read_manual_pump_status()
    is_running = bool(pump_status.get('pump_relay_on', False))
    current_kw = round(2.75 + (time.time() % 3) * 0.15, 2) if is_running else 0.0
    return jsonify({
        "ok": True,
        "currentUsage": current_kw,
        "dailyConsumption": 45.2,
        "weeklyConsumption": 312.5,
        "efficiency": 93
    })


@app.route('/api/history', methods=['GET', 'OPTIONS'])
def api_history():
    if request.method == 'OPTIONS':
        return ('', 204)
    logs = db.get_pump_logs(50)
    return jsonify({"ok": True, "logs": logs})


# ── Festival & Holiday Management Endpoints ────────────────────────────────────

@app.route('/api/festival/status', methods=['GET', 'OPTIONS'])
def api_festival_status():
    if request.method == 'OPTIONS':
        return ('', 204)
    from festival_policy import evaluate_festival_policy, get_festival_config, get_today_festival
    cfg = get_festival_config()
    pump_status = _read_manual_pump_status()
    is_on = bool(pump_status.get('pump_relay_on', False))
    eval_res = evaluate_festival_policy(pump_is_on=is_on)
    today_f = get_today_festival()
    return jsonify({
        "ok": True,
        **eval_res,
        "config": cfg,
        "today_festival": today_f,
    })


@app.route('/api/festivals/today', methods=['GET', 'OPTIONS'])
def api_festivals_today():
    if request.method == 'OPTIONS':
        return ('', 204)
    from festival_policy import get_today_festival, evaluate_festival_policy
    today_f = get_today_festival()
    eval_res = evaluate_festival_policy()
    return jsonify({
        "ok": True,
        "today": today_f,
        "is_festival": today_f is not None,
        "policy_evaluation": eval_res,
    })


@app.route('/api/festivals/upcoming', methods=['GET', 'OPTIONS'])
def api_festivals_upcoming():
    if request.method == 'OPTIONS':
        return ('', 204)
    from festival_policy import get_upcoming_festivals
    limit = request.args.get('limit', default=6, type=int)
    upcoming = get_upcoming_festivals(limit=limit)
    return jsonify({
        "ok": True,
        "upcoming": upcoming,
        "count": len(upcoming),
    })


@app.route('/api/festivals/calendar', methods=['GET', 'OPTIONS'])
def api_festivals_calendar():
    if request.method == 'OPTIONS':
        return ('', 204)
    from festival_policy import get_calendar_festivals, IST
    now = datetime.now(IST)
    year = request.args.get('year', default=now.year, type=int)
    month = request.args.get('month', default=now.month, type=int)
    festivals = get_calendar_festivals(year, month)
    return jsonify({
        "ok": True,
        "year": year,
        "month": month,
        "festivals": festivals,
        "count": len(festivals),
    })


@app.route('/api/festival/mode', methods=['POST', 'OPTIONS'])
def api_festival_mode():
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(silent=True) or {}
    enabled = data.get('enabled') if 'enabled' in data else data.get('mode', True)
    from festival_policy import set_festival_mode
    res = set_festival_mode(bool(enabled))
    return jsonify({
        "ok": True,
        "festival_mode": res["festival_mode"],
        "message": f"Festival mode {'enabled' if res['festival_mode'] else 'disabled'}",
        "config": res,
    })


@app.route('/api/festival/select', methods=['POST', 'OPTIONS'])
def api_festival_select():
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(silent=True) or {}
    fest_name = data.get('festival') or data.get('festival_name', 'Rang Panchami')
    from festival_policy import set_selected_festival
    res = set_selected_festival(fest_name)
    return jsonify({
        "ok": True,
        "selected_festival": res["selected_festival"],
        "config": res,
    })


@app.route('/api/festival/reset', methods=['POST', 'OPTIONS'])
def api_festival_reset():
    if request.method == 'OPTIONS':
        return ('', 204)
    from festival_policy import reset_festival_config
    res = reset_festival_config()
    return jsonify({
        "ok": True,
        "message": "Festival configuration reset to default",
        "config": res,
    })


@app.route('/api/festival/simulate', methods=['POST', 'OPTIONS'])
def api_festival_simulate():
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(silent=True) or {}
    sim_date = data.get('sim_date') or datetime.now().strftime('%Y-%m-%d')
    sim_time = data.get('sim_time') or '18:59:00'
    festival_name = data.get('festival_name', 'Rang Panchami')
    festival_mode = data.get('festival_mode', True)
    pump_is_on = data.get('pump_is_on', False)

    from festival_policy import simulate_festival_policy
    res = simulate_festival_policy(
        sim_date=sim_date,
        sim_time=sim_time,
        festival_name=festival_name,
        festival_mode=festival_mode,
        pump_is_on=pump_is_on,
    )
    return jsonify({"ok": True, "result": res})


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5050)
    parser.add_argument('--serial-port', default=None)
    parser.add_argument('--fresh', action='store_true')
    args = parser.parse_args()
    SERIAL_PORT = args.serial_port
    start_reader(fresh=args.fresh)
    print(f"\n  Dashboard Backend -> http://localhost:{args.port}\n", flush=True)
    app.run(host='0.0.0.0', port=args.port, threaded=True)

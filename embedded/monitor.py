#!/usr/bin/env python3
"""
ESP32 Pressure Sensor Monitor
Reads serial output from ESP32 and logs to CSV.

Usage:
    python3 monitor.py                        # auto-detect port, append to CSV
    python3 monitor.py --fresh                # overwrite CSV
    python3 monitor.py --port /dev/cu.xxx     # specify port
    python3 monitor.py --baud 115200          # specify baud rate
"""

import serial
import serial.tools.list_ports
import re
import csv
import time
import os
import argparse
from datetime import datetime

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pressure_log.csv')

def find_esp32_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if 'usbserial' in p.device or 'usbmodem' in p.device or 'CP210' in (p.description or '') or 'CH340' in (p.description or ''):
            return p.device
    # fallback: return first available port
    if ports:
        return ports[0].device
    return None

def main():
    parser = argparse.ArgumentParser(description='ESP32 Pressure Sensor Monitor')
    parser.add_argument('--port', help='Serial port (auto-detected if omitted)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--fresh', action='store_true', help='Overwrite CSV instead of appending')
    args = parser.parse_args()

    port = args.port or find_esp32_port()
    if not port:
        print('ERROR: No serial port found. Connect ESP32 and retry, or use --port.')
        return

    os.makedirs(os.path.dirname(os.path.abspath(CSV_PATH)), exist_ok=True)
    mode = 'w' if args.fresh else 'a'
    write_header = args.fresh or not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0

    f = open(CSV_PATH, mode, newline='')
    writer = csv.writer(f)
    if write_header:
        writer.writerow(['timestamp', 'packet', 'voltage_V', 'pressure_kPa', 'pressure_MPa', 'status'])
        f.flush()

    print(f'Port      : {port} @ {args.baud} baud')
    print(f'CSV       : {os.path.abspath(CSV_PATH)} ({"fresh" if args.fresh else "append"})')
    print(f'Started   : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('Press Ctrl+C to stop.\n')

    s = serial.Serial(port, args.baud, timeout=2, dsrdtr=False, rtscts=False)
    s.setDTR(False)
    s.setRTS(False)

    voltage = status = pkt = None

    try:
        while True:
            try:
                raw = s.readline()
                if not raw:
                    continue
                line = raw.decode('utf-8', errors='replace').strip()
                if not line:
                    continue
                print(line, flush=True)

                if line.startswith('Sensor Voltage'):
                    m = re.search(r'([\d.]+) V', line)
                    if m:
                        voltage = float(m.group(1))
                    status = 'ok'
                elif 'SENSOR FAULT' in line:
                    status = 'fault'
                elif line.startswith('LoRa sent'):
                    m = re.search(r'#(\d+)', line)
                    if m:
                        pkt = int(m.group(1))
                    if voltage is not None:
                        kpa  = max(0.0, (voltage - 0.5) / 4.0 * 100.0) if status == 'ok' else -1.0
                        mpa  = kpa / 1000.0 if status == 'ok' else -1.0
                        writer.writerow([
                            datetime.now().isoformat(),
                            pkt,
                            round(voltage, 3),
                            round(kpa, 2),
                            round(mpa, 4),
                            status
                        ])
                        f.flush()
                        print(f'[CSV] pkt={pkt}  {round(voltage,3)}V  {round(kpa,2)} kPa  ({status})', flush=True)
                        voltage = status = pkt = None

            except serial.SerialException as e:
                print(f'[WARN] Serial error: {e} — reconnecting in 2s...', flush=True)
                time.sleep(2)
                try:
                    s.close()
                    s.open()
                except Exception:
                    pass

    except KeyboardInterrupt:
        print(f'\nStopped. Data saved to {os.path.abspath(CSV_PATH)}')
    finally:
        s.close()
        f.close()

if __name__ == '__main__':
    main()

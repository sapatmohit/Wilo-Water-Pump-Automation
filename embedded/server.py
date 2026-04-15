#!/usr/bin/env python3
"""
Pressure Sensor Dashboard Server
Serves live ESP32 data via SSE to the browser dashboard.

Usage: python3 server.py [--port 5050] [--fresh]
"""

import serial
import serial.tools.list_ports
import re, csv, threading, queue, time, os, json, argparse
from datetime import datetime
from flask import Flask, Response, render_template_string

app = Flask(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pressure_log.csv')
SERIAL_PORT = None
BAUD = 115200

subscribers = []
subscribers_lock = threading.Lock()
latest = {"packet": -1, "voltage": 0.0, "pressure_kpa": 0.0, "pressure_mpa": 0.0, "status": "connecting", "timestamp": ""}
reader_thread = None
stop_event = threading.Event()

# ── Serial reader ──────────────────────────────────────────────────────────────

def find_port():
    for p in serial.tools.list_ports.comports():
        if any(k in p.device for k in ('usbserial', 'usbmodem', 'ttyUSB', 'ttyACM')):
            return p.device
    ports = serial.tools.list_ports.comports()
    return ports[0].device if ports else None

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
    os.makedirs(os.path.dirname(os.path.abspath(CSV_PATH)), exist_ok=True)
    mode = 'w' if fresh_csv else 'a'
    write_header = fresh_csv or not os.path.exists(CSV_PATH) or os.path.getsize(CSV_PATH) == 0
    f = open(CSV_PATH, mode, newline='')
    writer = csv.writer(f)
    if write_header:
        writer.writerow(['timestamp', 'packet', 'voltage_V', 'pressure_kPa', 'pressure_MPa', 'status'])
        f.flush()

    s = None
    while not stop_evt.is_set():
        try:
            if s is None or not s.is_open:
                s = serial.Serial(port, BAUD, timeout=2, dsrdtr=False, rtscts=False)
                s.setDTR(False); s.setRTS(False)
                broadcast({**latest, "status": "connecting"})

            raw = s.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', errors='replace').strip()
            if not line:
                continue

            # parse
            global _v, _st, _pkt
            if line.startswith('Sensor Voltage'):
                m = re.search(r'([\d.]+) V', line)
                if m: _v = float(m.group(1))
                _st = 'ok'
            elif 'SENSOR FAULT' in line:
                _st = 'fault'
            elif line.startswith('LoRa sent'):
                m = re.search(r'#(\d+)', line)
                if m: _pkt = int(m.group(1))
                if _v is not None:
                    kpa = max(0.0, (_v - 0.5) / 4.0 * 100.0) if _st == 'ok' else -1.0
                    mpa = kpa / 1000.0 if _st == 'ok' else -1.0
                    ts  = datetime.now().isoformat()
                    writer.writerow([ts, _pkt, round(_v,3), round(kpa,2), round(mpa,4), _st])
                    f.flush()
                    broadcast({"packet": _pkt, "voltage": round(_v,3),
                               "pressure_kpa": round(kpa,2), "pressure_mpa": round(mpa,4),
                               "status": _st, "timestamp": ts})
                    _v = _st = _pkt = None

        except serial.SerialException as e:
            broadcast({**latest, "status": "disconnected"})
            time.sleep(2)
            if s:
                try: s.close()
                except: pass
                s = None
    if s:
        try: s.close()
        except: pass
    f.close()

_v = _st = _pkt = None

def start_reader(fresh=False):
    global reader_thread, stop_event, _v, _st, _pkt
    _v = _st = _pkt = None
    if reader_thread and reader_thread.is_alive():
        stop_event.set()
        reader_thread.join(timeout=3)
    stop_event = threading.Event()
    port = SERIAL_PORT or find_port()
    reader_thread = threading.Thread(target=reader_loop, args=(port, fresh, stop_event), daemon=True)
    reader_thread.start()

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    with open(os.path.join(os.path.dirname(__file__), 'dashboard.html')) as fh:
        return fh.read()

@app.route('/stream')
def stream():
    q = queue.Queue(maxsize=50)
    with subscribers_lock:
        subscribers.append(q)
    # send current state immediately
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

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/restart', methods=['POST'])
def restart():
    start_reader(fresh=True)
    return ('', 204)

@app.route('/latest')
def get_latest():
    from flask import jsonify
    return jsonify(latest)

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5050)
    parser.add_argument('--serial-port', default=None)
    parser.add_argument('--fresh', action='store_true')
    args = parser.parse_args()
    SERIAL_PORT = args.serial_port
    start_reader(fresh=args.fresh)
    print(f"\n  Dashboard → http://localhost:{args.port}\n")
    app.run(host='0.0.0.0', port=args.port, threaded=True)

#!/usr/bin/env python3
"""
ESP32 LoRa pressure packet receiver for Raspberry Pi.

Listens for JSON packets from the ESP32 sender, decodes the payload,
and appends each packet to a CSV file. The CSV file is created with
headers automatically if it does not already exist.

Expected ESP32 payload:
    {"device":"esp32","sensor":"PR12P210","status":"ok",
     "voltage":1.234,"pressure_kpa":12.50,"pkt":42}
"""

import argparse
import csv
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.abspath(os.path.join(_HERE, '..', '..'))
sys.path.insert(0, _PROJECT)
sys.path.insert(0, _HERE)

import tank_config as CFG
from sx127x import SX127x

logger = logging.getLogger("wilo.lora_csv")

CSV_HEADER = [
    "timestamp",
    "device",
    "sensor",
    "status",
    "voltage_v",
    "pressure_kpa",
    "pkt",
    "rssi_dbm",
    "snr_db",
    "raw_payload",
    "parse_error",
]


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")


def parse_lora_packet(raw_str):
    """
    Parse the ESP32 JSON payload.
    Returns a dictionary with normalized fields.
    """
    payload = raw_str.strip()
    if not payload:
        raise ValueError("empty payload")

    data = json.loads(payload)
    return {
        "device": data.get("device", ""),
        "sensor": data.get("sensor", ""),
        "status": data.get("status", "unknown"),
        "voltage_v": data.get("voltage", None),
        "pressure_kpa": data.get("pressure_kpa", None),
        "pkt": data.get("pkt", None),
    }


class PacketCsvLogger:
    """Append-only CSV logger for LoRa packets."""

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self._file = None
        self._writer = None
        self._rows = 0

    def initialize(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.csv_path)), exist_ok=True)
        write_header = (not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0)
        self._file = open(self.csv_path, "a", newline="")
        self._writer = csv.writer(self._file)
        if write_header:
            self._writer.writerow(CSV_HEADER)
            self._file.flush()
        logger.info("CSV logging to %s", os.path.abspath(self.csv_path))

    def write_packet(self, packet, rssi=None, snr=None, raw_payload="", parse_error=""):
        if self._writer is None:
            raise RuntimeError("CSV logger not initialized")

        self._writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            packet.get("device", "") if packet else "",
            packet.get("sensor", "") if packet else "",
            packet.get("status", "") if packet else "",
            packet.get("voltage_v", "") if packet and packet.get("voltage_v") is not None else "",
            packet.get("pressure_kpa", "") if packet and packet.get("pressure_kpa") is not None else "",
            packet.get("pkt", "") if packet and packet.get("pkt") is not None else "",
            rssi if rssi is not None else "",
            f"{snr:.2f}" if snr is not None else "",
            raw_payload,
            parse_error,
        ])
        self._rows += 1
        self._file.flush()

    def close(self):
        if self._file:
            self._file.flush()
            self._file.close()
            logger.info("CSV closed after %d rows", self._rows)


class LoRaCsvReceiver:
    """Receive LoRa packets and append them to CSV."""

    def __init__(self, csv_path):
        self.csv_logger = PacketCsvLogger(csv_path)
        self.lora = None
        self.running = True

    def initialize(self):
        logger.info("Initializing LoRa receiver on 433 MHz")
        self.lora = SX127x(
            spi_bus=CFG.LORA_SPI_BUS,
            spi_cs=CFG.LORA_SPI_CS,
            reset_pin=CFG.LORA_RESET_PIN,
            dio0_pin=CFG.LORA_DIO0_PIN,
            frequency=CFG.LORA_FREQUENCY,
        )
        self.lora.receive()
        self.csv_logger.initialize()
        logger.info("Listening for ESP32 pressure packets...")

    def handle_signal(self, *_):
        self.running = False

    def run(self):
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

        self.initialize()
        try:
            while self.running:
                if self.lora.available():
                    raw = self.lora.read_payload()
                    raw_str = "".join(chr(c) for c in raw).replace("\x00", "").strip()
                    rssi = self.lora.get_packet_rssi()
                    snr = self.lora.get_packet_snr()

                    try:
                        packet = parse_lora_packet(raw_str)
                        self.csv_logger.write_packet(
                            packet=packet,
                            rssi=rssi,
                            snr=snr,
                            raw_payload=raw_str,
                            parse_error="",
                        )
                        logger.info(
                            "RX pkt=%s device=%s pressure=%s kPa voltage=%s V RSSI=%s dBm SNR=%.2f dB",
                            packet.get("pkt", ""),
                            packet.get("device", ""),
                            packet.get("pressure_kpa", ""),
                            packet.get("voltage_v", ""),
                            rssi,
                            snr,
                        )
                    except Exception as exc:
                        logger.warning("Packet parse failed: %s | raw=%r", exc, raw_str)
                        self.csv_logger.write_packet(
                            packet=None,
                            rssi=rssi,
                            snr=snr,
                            raw_payload=raw_str,
                            parse_error=str(exc),
                        )

                time.sleep(0.01)
        finally:
            try:
                self.csv_logger.close()
            finally:
                if self.lora:
                    self.lora.close()


def main():
    parser = argparse.ArgumentParser(description="Receive ESP32 LoRa pressure packets and append them to CSV.")
    parser.add_argument(
        "--csv",
        default=CFG.LORA_PACKET_CSV_PATH,
        help="Path to the CSV file (default: tank_config.LORA_PACKET_CSV_PATH)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    receiver = LoRaCsvReceiver(csv_path=args.csv)
    receiver.run()


if __name__ == "__main__":
    main()

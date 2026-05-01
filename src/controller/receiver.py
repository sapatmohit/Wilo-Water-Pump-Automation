#!/usr/bin/env python3
"""
Compatibility entry point for the Pi LoRa receiver.

This now forwards to the CSV logger receiver so existing scripts and
service files can keep calling ``receiver.py`` without changes.
"""

from lora_csv_receiver import main


if __name__ == "__main__":
    main()

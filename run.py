#!/usr/bin/env python3
"""
Wilo Water Pump Automation System - Main Entry Point

Professional water pump automation system with predictive control,
historical pattern analysis, and intelligent scheduling capabilities.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the main application
from src.core.main import main_loop

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Application terminated by user.")
    except Exception as e:
        print(f"[ERROR] Application failed to start: {e}")
        sys.exit(1)
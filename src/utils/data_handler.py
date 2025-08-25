"""
Data handling utilities for the Wilo Water Pump Automation System
"""

import pandas as pd
import numpy as np
import csv
import os
from datetime import datetime
from config.settings import LOG_FILE, HISTORICAL_DATA_FILE

def load_historical_data():
    """Load the 2-year historical dataset"""
    try:
        print("[INFO] Loading 2-year historical data...")
        data = pd.read_csv(HISTORICAL_DATA_FILE)
        data['Date'] = pd.to_datetime(data['Date'])
        data['Hour'] = pd.to_datetime(data['Hour'], format='%H:%M').dt.hour
        print(f"[SUCCESS] Loaded {len(data)} historical records from {data['Date'].min().date()} to {data['Date'].max().date()}")
        return data
    except Exception as e:
        print(f"[ERROR] Failed to load historical data: {e}")
        return None

def initialize_csv():
    """Initialize CSV file with headers if it doesn't exist"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['date', 'start_hour', 'duration', 'water_level', 'flow_rate', 
                           'voltage', 'current', 'temperature', 'inflow_rate', 'outflow_rate', 
                           'is_special_day', 'has_inflow'])
        print(f"[INFO] Created new log file: {LOG_FILE}")

def load_past_usage():
    """Load past usage data from CSV"""
    past_usage = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    past_usage.append({
                        'date': row['date'],
                        'start_hour': float(row['start_hour']),
                        'duration': float(row['duration']),
                        'water_level': float(row['water_level']),
                        'flow_rate': float(row['flow_rate']),
                        'voltage': float(row['voltage']),
                        'current': float(row['current']),
                        'temperature': float(row['temperature']),
                        'inflow_rate': float(row['inflow_rate']),
                        'outflow_rate': float(row['outflow_rate']),
                        'is_special_day': int(row['is_special_day']),
                        'has_inflow': int(row['has_inflow'])
                    })
        except Exception as e:
            print(f"[ERROR] Failed to load past usage data: {e}")
    return past_usage

def save_log_to_csv(start_hour, duration, sensor_data):
    """Save run log to CSV file for trend learning"""
    now = datetime.now()
    
    try:
        with open(LOG_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                now.strftime('%Y-%m-%d'),
                f"{start_hour:.2f}",
                f"{duration:.2f}",
                f"{sensor_data[0][0]:.2f}",  # water_level
                f"{sensor_data[0][1]:.2f}",  # flow_rate
                f"{sensor_data[0][2]:.2f}",  # voltage
                f"{sensor_data[0][3]:.2f}",  # current
                f"{sensor_data[0][4]:.2f}",  # temperature
                f"{sensor_data[0][5]:.2f}",  # inflow_rate
                f"{sensor_data[0][6]:.2f}",  # outflow_rate
                f"{sensor_data[0][7]:.0f}",  # is_special_day
                f"{sensor_data[0][8]:.0f}"   # has_inflow
            ])
        
        print(f"[LOG] Data saved to {LOG_FILE}: Start at {start_hour:.2f} for {duration:.2f} mins.")
    except Exception as e:
        print(f"[ERROR] Failed to save log data: {e}")

def validate_sensor_data(sensor_data):
    """Validate sensor data for anomalies"""
    if sensor_data is None or len(sensor_data) == 0:
        return False
    
    # Check for NaN values
    if np.any(np.isnan(sensor_data)):
        return False
    
    # Basic range validation
    water_level = sensor_data[0][0]
    voltage = sensor_data[0][2]
    current = sensor_data[0][3]
    temperature = sensor_data[0][4]
    
    if not (0 <= water_level <= 100):
        return False
    if not (200 <= voltage <= 250):
        return False
    if not (0 <= current <= 10):
        return False
    if not (-10 <= temperature <= 50):
        return False
    
    return True
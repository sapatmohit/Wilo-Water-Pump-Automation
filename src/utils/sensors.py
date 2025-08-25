"""
Sensor utilities for the Wilo Water Pump Automation System
"""

import numpy as np
import random
from datetime import datetime
from src.utils.data_handler import load_historical_data

def get_sensor_data():
    """
    Generate realistic sensor data based on historical patterns.
    """
    data = load_historical_data()
    now = datetime.now()
    
    if data is None:
        return get_fallback_sensor_data()
    
    # Get similar historical conditions
    current_month = now.month
    current_hour = now.hour
    current_weekday = now.weekday()
    
    # Filter historical data for similar conditions
    similar_data = data[
        (data['Date'].dt.month == current_month) &
        (data['Date'].dt.weekday == current_weekday) &
        (data['Hour'] == current_hour)
    ]
    
    if len(similar_data) > 0:
        # Use historical patterns with some variation
        water_level = similar_data['TopTankLevel'].mean() + random.uniform(-5, 5)
        voltage = similar_data['Voltage'].mean() + random.uniform(-2, 2)
        current = similar_data['Current'].mean() + random.uniform(-0.1, 0.1)
        temperature = similar_data['Temperature'].mean() + random.uniform(-1, 1)
        humidity = similar_data['Humidity'].mean() + random.uniform(-2, 2)
    else:
        return get_fallback_sensor_data()
    
    # Calculate derived values
    flow_rate = 200 + (water_level - 50) * 2 + random.uniform(-20, 20)
    inflow_rate = 1.0 + random.uniform(-0.3, 0.5)
    outflow_rate = 50 + random.uniform(-10, 20)
    
    # Special day logic
    is_special_day = 1 if current_weekday >= 5 else 0  # Weekend
    has_inflow = 1 if random.random() > 0.3 else 0
    
    return np.array([[water_level, flow_rate, voltage, current, temperature, 
                     inflow_rate, outflow_rate, is_special_day, has_inflow]])

def get_fallback_sensor_data():
    """
    Generate fallback sensor data when historical data is not available.
    """
    water_level = 60 + random.uniform(-10, 20)
    voltage = 220 + random.uniform(-10, 10)
    current = 3.0 + random.uniform(-0.5, 1.0)
    temperature = 25 + random.uniform(-5, 10)
    humidity = 60 + random.uniform(-10, 10)
    
    # Calculate derived values
    flow_rate = 200 + (water_level - 50) * 2 + random.uniform(-20, 20)
    inflow_rate = 1.0 + random.uniform(-0.3, 0.5)
    outflow_rate = 50 + random.uniform(-10, 20)
    
    # Special day logic
    now = datetime.now()
    is_special_day = 1 if now.weekday() >= 5 else 0  # Weekend
    has_inflow = 1 if random.random() > 0.3 else 0
    
    return np.array([[water_level, flow_rate, voltage, current, temperature, 
                     inflow_rate, outflow_rate, is_special_day, has_inflow]])

def simulate_sensor_failure():
    """
    Simulate sensor failure by returning NaN values.
    """
    return np.array([[np.nan, np.nan, np.nan, np.nan, np.nan, 
                     np.nan, np.nan, np.nan, np.nan]])

def get_sensor_summary(sensor_data):
    """
    Generate a summary of current sensor readings.
    """
    if sensor_data is None or len(sensor_data) == 0:
        return "No sensor data available"
    
    return {
        'water_level': sensor_data[0][0],
        'flow_rate': sensor_data[0][1],
        'voltage': sensor_data[0][2],
        'current': sensor_data[0][3],
        'temperature': sensor_data[0][4],
        'inflow_rate': sensor_data[0][5],
        'outflow_rate': sensor_data[0][6],
        'is_special_day': bool(sensor_data[0][7]),
        'has_inflow': bool(sensor_data[0][8])
    }
import joblib
import numpy as np
import time
import csv
import os
import pandas as pd
from datetime import datetime, timedelta
import random

# Load models
hour_model = joblib.load('start_hour_model.pkl')
dur_model = joblib.load('duration_model.pkl')

# CSV files
HISTORICAL_DATA_FILE = 'synthetic_water_data.csv'
SIMULATION_LOG_FILE = 'simulation_30days.csv'

# Global variable to store historical data
historical_data = None

# Simulation settings
SIMULATION_SPEED = 60  # 1 minute = 1 hour (60x speed)
SIMULATION_DAYS = 30
START_DATE = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

def load_historical_data():
    """Load the 2-year historical dataset"""
    global historical_data
    if historical_data is None:
        print("📊 Loading 2-year historical data...")
        historical_data = pd.read_csv(HISTORICAL_DATA_FILE)
        historical_data['Date'] = pd.to_datetime(historical_data['Date'])
        historical_data['Hour'] = pd.to_datetime(historical_data['Hour'], format='%H:%M').dt.hour
        print(f"✅ Loaded {len(historical_data)} historical records")
    return historical_data

def get_sensor_data(simulation_time):
    """Generate realistic sensor data for simulation time"""
    data = load_historical_data()
    
    # Get similar historical conditions
    current_month = simulation_time.month
    current_hour = simulation_time.hour
    current_weekday = simulation_time.weekday()
    
    # Filter historical data for similar conditions
    similar_data = data[
        (data['Date'].dt.month == current_month) &
        (data['Date'].dt.weekday == current_weekday) &
        (data['Hour'] == current_hour)
    ]
    
    if len(similar_data) > 0:
        water_level = similar_data['TopTankLevel'].mean() + random.uniform(-5, 5)
        voltage = similar_data['Voltage'].mean() + random.uniform(-2, 2)
        current = similar_data['Current'].mean() + random.uniform(-0.1, 0.1)
        temperature = similar_data['Temperature'].mean() + random.uniform(-1, 1)
    else:
        water_level = 60 + random.uniform(-10, 20)
        voltage = 220 + random.uniform(-10, 10)
        current = 3.0 + random.uniform(-0.5, 1.0)
        temperature = 25 + random.uniform(-5, 10)
    
    flow_rate = 200 + (water_level - 50) * 2 + random.uniform(-20, 20)
    inflow_rate = 1.0 + random.uniform(-0.3, 0.5)
    outflow_rate = 50 + random.uniform(-10, 20)
    is_special_day = 1 if current_weekday >= 5 else 0
    has_inflow = 1 if random.random() > 0.3 else 0
    
    return np.array([[water_level, flow_rate, voltage, current, temperature, 
                     inflow_rate, outflow_rate, is_special_day, has_inflow]])

def get_prediction(simulation_time):
    """Get prediction using ML model or historical patterns"""
    sensor_data = get_sensor_data(simulation_time)
    
    try:
        predicted_hour = hour_model.predict(sensor_data)[0]
        predicted_duration = dur_model.predict(sensor_data)[0]
    except:
        # Fallback to historical patterns
        data = load_historical_data()
        similar_runs = data[
            (data['Date'].dt.month == simulation_time.month) &
            (data['Date'].dt.weekday == simulation_time.weekday()) &
            (data['Duration'] > 0)
        ]
        
        if len(similar_runs) > 0:
            predicted_hour = similar_runs['Hour'].mean()
            predicted_duration = similar_runs['Duration'].mean()
        else:
            predicted_hour = 7.0
            predicted_duration = 90.0
    
    return predicted_hour, predicted_duration, sensor_data

def initialize_simulation_csv():
    """Initialize simulation CSV file"""
    if not os.path.exists(SIMULATION_LOG_FILE):
        with open(SIMULATION_LOG_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['simulation_date', 'simulation_time', 'predicted_hour', 
                           'predicted_duration', 'pump_activated', 'water_level', 
                           'temperature', 'weekday'])

def save_simulation_log(simulation_time, predicted_hour, predicted_duration, 
                       pump_activated, sensor_data, weekday_name):
    """Save simulation log"""
    with open(SIMULATION_LOG_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            simulation_time.strftime('%Y-%m-%d'),
            simulation_time.strftime('%H:%M'),
            f"{predicted_hour:.2f}",
            f"{predicted_duration:.2f}",
            "YES" if pump_activated else "NO",
            f"{sensor_data[0][0]:.1f}",
            f"{sensor_data[0][4]:.1f}",
            weekday_name
        ])

def run_simulation():
    """Run 30-day fast-forward simulation"""
    print("🚀 Starting 30-Day Fast-Forward Simulation")
    print(f"⏱️ Speed: 1 minute = 1 hour ({SIMULATION_SPEED}x)")
    print(f"📅 Duration: {SIMULATION_DAYS} days")
    print(f"🎬 Start date: {START_DATE.strftime('%Y-%m-%d')}")
    print("="*60)
    
    # Initialize
    initialize_simulation_csv()
    load_historical_data()
    
    current_simulation_time = START_DATE
    end_simulation_time = START_DATE + timedelta(days=SIMULATION_DAYS)
    pump_cycles = 0
    total_pump_time = 0
    
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    print(f"🕐 Starting simulation at: {current_simulation_time.strftime('%Y-%m-%d %H:%M')}")
    print("⏳ Simulation running... (Press Ctrl+C to stop early)")
    
    try:
        while current_simulation_time < end_simulation_time:
            # Get prediction
            predicted_hour, predicted_duration, sensor_data = get_prediction(current_simulation_time)
            
            current_hour = current_simulation_time.hour + current_simulation_time.minute / 60
            weekday_name = weekday_names[current_simulation_time.weekday()]
            
            # Check if pump should activate (within 5-minute window)
            pump_activated = abs(current_hour - predicted_hour) < 0.08
            
            # Log the simulation step
            save_simulation_log(current_simulation_time, predicted_hour, 
                              predicted_duration, pump_activated, sensor_data, weekday_name)
            
            # Display status
            if pump_activated:
                print(f"⏰ {current_simulation_time.strftime('%m-%d %H:%M')} | {weekday_name} | "
                      f"🔮 Pred: {predicted_hour:.1f}h ({predicted_duration:.0f}min) | "
                      f"💧 Water: {sensor_data[0][0]:.0f}% | 🌡️ Temp: {sensor_data[0][4]:.1f}°C | "
                      f"🚰 PUMP ACTIVATED!")
                
                # Simulate pump running
                pump_duration_minutes = min(predicted_duration, 120)  # Cap at 2 hours
                simulation_duration_seconds = (pump_duration_minutes * 60) / SIMULATION_SPEED
                
                print(f"⏱️ Pump running for {pump_duration_minutes:.0f} minutes "
                      f"(simulation: {simulation_duration_seconds:.1f}s)")
                
                time.sleep(simulation_duration_seconds)
                
                pump_cycles += 1
                total_pump_time += pump_duration_minutes
                
                # Skip ahead past the pump duration
                current_simulation_time += timedelta(minutes=pump_duration_minutes)
            else:
                # Show status every 6 hours
                if current_simulation_time.minute % 60 == 0:
                    time_diff = predicted_hour - current_hour
                    if time_diff > 0:
                        next_pump = f"in {time_diff:.1f}h"
                    else:
                        next_pump = f"in {24 + time_diff:.1f}h"
                    
                    print(f"⏳ {current_simulation_time.strftime('%m-%d %H:%M')} | {weekday_name} | "
                          f"🔮 Pred: {predicted_hour:.1f}h | Next pump: {next_pump} | "
                          f"💧 Water: {sensor_data[0][0]:.0f}% | 🌡️ Temp: {sensor_data[0][4]:.1f}°C")
            
            # Advance simulation time by 1 hour
            current_simulation_time += timedelta(hours=1)
            
            # Wait 1 minute (simulates 1 hour)
            time.sleep(60 / SIMULATION_SPEED)
    
    except KeyboardInterrupt:
        print("\n⏹️ Simulation stopped by user.")
    
    # Simulation complete
    print("\n" + "="*60)
    print("🎬 SIMULATION COMPLETE!")
    print("="*60)
    print(f"📅 Simulated period: {START_DATE.strftime('%Y-%m-%d')} to {current_simulation_time.strftime('%Y-%m-%d')}")
    print(f"🚰 Total pump cycles: {pump_cycles}")
    print(f"⏱️ Total pump runtime: {total_pump_time:.0f} minutes ({total_pump_time/60:.1f} hours)")
    if pump_cycles > 0:
        print(f"📊 Average cycles per day: {pump_cycles/SIMULATION_DAYS:.1f}")
    print(f"📁 Simulation log saved to: {SIMULATION_LOG_FILE}")
    print("="*60)

if __name__ == "__main__":
    run_simulation() 
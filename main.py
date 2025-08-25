import joblib
import numpy as np
import time
import csv
import os
import pandas as pd
from datetime import datetime, timedelta
import random
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# Load models
hour_model = joblib.load('start_hour_model.pkl')
dur_model = joblib.load('duration_model.pkl')

# CSV files
LOG_FILE = 'pump_usage_log.csv'
HISTORICAL_DATA_FILE = 'synthetic_water_data.csv'

# Global variable to store historical data
historical_data = None

def load_historical_data():
    """Load the 2-year historical dataset"""
    global historical_data
    if historical_data is None:
        print("[INFO] Loading 2-year historical data...")
        historical_data = pd.read_csv(HISTORICAL_DATA_FILE)
        historical_data['Date'] = pd.to_datetime(historical_data['Date'])
        historical_data['Hour'] = pd.to_datetime(historical_data['Hour'], format='%H:%M').dt.hour
        print(f"[SUCCESS] Loaded {len(historical_data)} historical records from {historical_data['Date'].min().date()} to {historical_data['Date'].max().date()}")
    return historical_data

def get_historical_patterns():
    """Analyze historical patterns for better predictions"""
    data = load_historical_data()
    
    # Filter records where pump was actually running (Duration > 0)
    pump_runs = data[data['Duration'] > 0].copy()
    
    if len(pump_runs) == 0:
        return None
    
    # Calculate patterns
    patterns = {
        'avg_start_hour': pump_runs['Hour'].mean(),
        'avg_duration': pump_runs['Duration'].mean(),
        'common_start_hours': pump_runs['Hour'].value_counts().head(3).to_dict(),
        'weekday_patterns': {},
        'monthly_patterns': {},
        'temperature_effects': {}
    }
    
    # Weekday patterns
    pump_runs['weekday'] = pump_runs['Date'].dt.weekday
    weekday_stats = pump_runs.groupby('weekday').agg({
        'Hour': 'mean',
        'Duration': 'mean'
    }).round(2)
    patterns['weekday_patterns'] = weekday_stats.to_dict()
    
    # Monthly patterns
    pump_runs['month'] = pump_runs['Date'].dt.month
    monthly_stats = pump_runs.groupby('month').agg({
        'Hour': 'mean',
        'Duration': 'mean'
    }).round(2)
    patterns['monthly_patterns'] = monthly_stats.to_dict()
    
    # Temperature effects
    temp_bins = pd.cut(pump_runs['Temperature'], bins=[-10, 10, 20, 30, 40])
    temp_stats = pump_runs.groupby(temp_bins).agg({
        'Hour': 'mean',
        'Duration': 'mean'
    }).round(2)
    patterns['temperature_effects'] = temp_stats.to_dict()
    
    return patterns

def get_sensor_data():
    """
    Generate realistic sensor data based on historical patterns.
    """
    data = load_historical_data()
    now = datetime.now()
    
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
        # Fallback to realistic ranges
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
    is_special_day = 1 if current_weekday >= 5 else 0  # Weekend
    has_inflow = 1 if random.random() > 0.3 else 0
    
    return np.array([[water_level, flow_rate, voltage, current, temperature, 
                     inflow_rate, outflow_rate, is_special_day, has_inflow]])

def get_historical_based_prediction():
    """
    Get prediction based on historical patterns for similar conditions.
    """
    data = load_historical_data()
    now = datetime.now()
    
    # Get pump runs for similar conditions
    similar_runs = data[
        (data['Date'].dt.month == now.month) &
        (data['Date'].dt.weekday == now.weekday()) &
        (data['Duration'] > 0)
    ]
    
    if len(similar_runs) > 0:
        # Use historical patterns
        avg_hour = similar_runs['Hour'].mean()
        avg_duration = similar_runs['Duration'].mean()
        
        # Add some variation based on current conditions
        if now.weekday() >= 5:  # Weekend
            avg_hour += 0.5
            avg_duration += 10
        
        return avg_hour, avg_duration
    else:
        return fallback_prediction()

def fallback_prediction():
    """
    Fallback prediction based on historical data patterns.
    """
    patterns = get_historical_patterns()
    
    if patterns is None:
        return 7.0, 90  # Default: 7 AM start, 90 min
    
    # Use overall historical averages
    avg_hour = patterns['avg_start_hour']
    avg_duration = patterns['avg_duration']
    
    # Adjust based on current conditions
    now = datetime.now()
    if now.weekday() >= 5:  # Weekend
        avg_hour += 0.5
        avg_duration += 10
    
    return avg_hour, avg_duration

def initialize_csv():
    """Initialize CSV file with headers if it doesn't exist"""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['date', 'start_hour', 'duration', 'water_level', 'flow_rate', 
                           'voltage', 'current', 'temperature', 'inflow_rate', 'outflow_rate', 
                           'is_special_day', 'has_inflow'])

def load_past_usage():
    """Load past usage data from CSV"""
    past_usage = []
    if os.path.exists(LOG_FILE):
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
    return past_usage

def control_pump(turn_on):
    """
    Replace this with your actual GPIO or relay logic.
    """
    if turn_on:
        print("[CONTROL] PUMP STATUS: ON")
    else:
        print("[CONTROL] PUMP STATUS: OFF")

def save_log_to_csv(start_hour, duration, sensor_data):
    """
    Save run log to CSV file for trend learning.
    """
    now = datetime.now()
    
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

def analyze_historical_trends():
    """
    Analyze and display historical trends from 2-year data.
    """
    patterns = get_historical_patterns()
    
    if patterns is None:
        print("-" * 60)
        print("[WARNING] No historical pump run data found.")
        print("-" * 60)
        return
    
    print("-" * 60)
    print("[ANALYSIS] Historical Analysis (2-year data):")
    print("-" * 60)
    print(f"   • Average start time: {patterns['avg_start_hour']:.2f}h")
    print(f"   • Average duration: {patterns['avg_duration']:.2f} minutes")
    
    print("\n[DATA] Most common start times:")
    print("-" * 40)
    for hour, count in patterns['common_start_hours'].items():
        print(f"   • {hour}:00 - {count} times")
    
    print("\n[PATTERN] Weekday patterns:")
    print("-" * 40)
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for weekday, stats in patterns['weekday_patterns']['Hour'].items():
        duration = patterns['weekday_patterns']['Duration'][weekday]
        print(f"   • {weekday_names[weekday]}: {stats:.2f}h start, {duration:.2f}min duration")
    
    print("\n[ANALYSIS] Temperature effects:")
    print("-" * 40)
    for temp_range, stats in patterns['temperature_effects']['Hour'].items():
        duration = patterns['temperature_effects']['Duration'][temp_range]
        print(f"   • {temp_range}: {stats:.2f}h start, {duration:.2f}min duration")
    print("-" * 60)

def analyze_trends():
    """
    Analyze recent trends and print insights.
    """
    past_usage = load_past_usage()
    if len(past_usage) < 3:
        return
    
    recent = past_usage[-7:] if len(past_usage) >= 7 else past_usage[-3:]
    
    avg_hour = np.mean([entry['start_hour'] for entry in recent])
    avg_duration = np.mean([entry['duration'] for entry in recent])
    
    print("-" * 60)
    print(f"[TREND] Recent trends: Avg start time: {avg_hour:.2f}h, Avg duration: {avg_duration:.2f}min")
    print("-" * 60)

def main_loop():
    print("=" * 60)
    print("    WILO WATER PUMP AUTOMATION SYSTEM")
    print("=" * 60)
    print(f"[CONFIG] Logging data to: {LOG_FILE}")
    print(f"[CONFIG] Using 2-year historical data from: {HISTORICAL_DATA_FILE}")
    print("=" * 60)
    
    # Initialize CSV file
    initialize_csv()
    
    # Load and analyze historical data
    analyze_historical_trends()
    
    # Load initial historical data
    past_usage = load_past_usage()
    if past_usage:
        print("-" * 60)
        print(f"[INFO] Loaded {len(past_usage)} recent records")
        analyze_trends()
    
    print("-" * 60)
    print("[STATUS] System initialization complete. Starting monitoring loop...")
    print("=" * 60)
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            sensor_data = get_sensor_data()
            
            print(f"\n{'='*60}")
            print(f"[CYCLE {cycle_count:04d}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            print(f"[SENSORS] Water Level: {sensor_data[0][0]:.1f}% | Flow Rate: {sensor_data[0][1]:.1f}L/min | Temperature: {sensor_data[0][4]:.1f}°C")
            print(f"[SENSORS] Voltage: {sensor_data[0][2]:.1f}V | Current: {sensor_data[0][3]:.2f}A | Humidity: {sensor_data[0][5]:.1f}%")
            print("-" * 60)
            
            if np.any(np.isnan(sensor_data)):
                print("-" * 60)
                print("[WARNING] Sensor error detected. Using historical-based prediction.")
                print("-" * 60)
                predicted_hour, predicted_duration = get_historical_based_prediction()
            else:
                # Try ML model first, fallback to historical patterns
                try:
                    predicted_hour = hour_model.predict(sensor_data)[0]
                    predicted_duration = dur_model.predict(sensor_data)[0]
                except:
                    print("-" * 60)
                    print("[WARNING] ML model error. Using historical-based prediction.")
                    print("-" * 60)
                    predicted_hour, predicted_duration = get_historical_based_prediction()

            now = datetime.now()
            current_hour = now.hour + now.minute / 60

            print(f"[PREDICT] Optimal start time: {predicted_hour:.2f}h ({predicted_hour:.0f}:{int((predicted_hour % 1) * 60):02d}) | Duration: {predicted_duration:.2f} min")
            print("-" * 60)

            # Smart tolerance: ~5 min window
            if abs(current_hour - predicted_hour) < 0.08:
                print("[ACTION] PUMP ACTIVATION TRIGGERED")
                print("-" * 60)
                control_pump(True)
                
                # Simulate pump running (in real system, monitor actual pump status)
                print(f"[STATUS] Pump operating for {predicted_duration:.2f} minutes...")
                time.sleep(min(predicted_duration * 60, 300))  # Cap at 5 minutes for demo
                
                control_pump(False)
                save_log_to_csv(predicted_hour, predicted_duration, sensor_data)
                
                print("-" * 60)
                print("[STATUS] Cycle completed successfully. Waiting for next prediction window.")
                print("=" * 60)
                time.sleep(60)  # Wait 1 minute before rechecking
            else:
                time_diff = predicted_hour - current_hour
                if time_diff > 0:
                    print(f"[SCHEDULE] Next pump cycle scheduled in {time_diff:.2f} hours")
                else:
                    print(f"[SCHEDULE] Next pump cycle scheduled in {24 + time_diff:.2f} hours")
                
                print("=" * 60)
                # Check every minute
                time.sleep(60)

        except KeyboardInterrupt:
            print("\n" + "=" * 60)
            print("[SYSTEM] System stopped by user.")
            print("=" * 60)
            break
        except Exception as e:
            print("-" * 60)
            print(f"[ERROR] System error: {e}")
            print("-" * 60)
            time.sleep(60)

if __name__ == "__main__":
    main_loop()

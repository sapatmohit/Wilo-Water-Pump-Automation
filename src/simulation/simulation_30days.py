import joblib
import numpy as np
import time
import csv
import os
import pandas as pd
from datetime import datetime, timedelta
import random
import warnings

# Suppress sklearn warnings
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

# Load models
hour_model = joblib.load('start_hour_model.pkl')
dur_model = joblib.load('duration_model.pkl')

# CSV files
LOG_FILE = 'pump_usage_log.csv'
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

def get_historical_patterns():
    """Analyze historical patterns for better predictions"""
    data = load_historical_data()
    pump_runs = data[data['Duration'] > 0].copy()
    
    if len(pump_runs) == 0:
        return None
    
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
    
    return patterns

def get_sensor_data(simulation_time):
    """
    Generate realistic sensor data based on historical patterns for simulation time.
    """
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
        # Use historical patterns with some variation
        water_level = similar_data['TopTankLevel'].mean() + random.uniform(-5, 5)
        voltage = similar_data['Voltage'].mean() + random.uniform(-2, 2)
        current = similar_data['Current'].mean() + random.uniform(-0.1, 0.1)
        temperature = similar_data['Temperature'].mean() + random.uniform(-1, 1)
    else:
        # Fallback to realistic ranges
        water_level = 60 + random.uniform(-10, 20)
        voltage = 220 + random.uniform(-10, 10)
        current = 3.0 + random.uniform(-0.5, 1.0)
        temperature = 25 + random.uniform(-5, 10)
    
    # Calculate derived values
    flow_rate = 200 + (water_level - 50) * 2 + random.uniform(-20, 20)
    inflow_rate = 1.0 + random.uniform(-0.3, 0.5)
    outflow_rate = 50 + random.uniform(-10, 20)
    
    # Special day logic
    is_special_day = 1 if current_weekday >= 5 else 0  # Weekend
    has_inflow = 1 if random.random() > 0.3 else 0
    
    return np.array([[water_level, flow_rate, voltage, current, temperature, 
                     inflow_rate, outflow_rate, is_special_day, has_inflow]])

def get_historical_based_prediction(simulation_time):
    """
    Get prediction based on historical patterns for similar conditions.
    """
    data = load_historical_data()
    
    # Get pump runs for similar conditions
    similar_runs = data[
        (data['Date'].dt.month == simulation_time.month) &
        (data['Date'].dt.weekday == simulation_time.weekday()) &
        (data['Duration'] > 0)
    ]
    
    if len(similar_runs) > 0:
        # Use historical patterns
        avg_hour = similar_runs['Hour'].mean()
        avg_duration = similar_runs['Duration'].mean()
        
        # Add some variation based on current conditions
        if simulation_time.weekday() >= 5:  # Weekend
            avg_hour += 0.5
            avg_duration += 10
        
        return avg_hour, avg_duration
    else:
        # Default daily pattern if no historical data
        base_hour = 7.0 + (simulation_time.weekday() * 0.1)  # Slight variation by weekday
        base_duration = 90 + random.uniform(-15, 15)  # 75-105 minutes
        
        if simulation_time.weekday() >= 5:  # Weekend
            base_hour += 0.5
            base_duration += 10
        
        return base_hour, base_duration

def check_water_availability(simulation_time, sensor_data):
    """
    Check if water is available for pumping (simulate water cutoffs, maintenance, etc.)
    """
    # Simulate water cutoffs (rare events)
    water_level = sensor_data[0][0]
    
    # Water cutoff conditions (about 5% of days)
    cutoff_conditions = [
        simulation_time.day == 15 and simulation_time.month == 8,  # Maintenance day
        simulation_time.day == 1 and simulation_time.month == 8,   # System check
        water_level < 20,  # Emergency low water
        simulation_time.weekday() == 6 and simulation_time.day % 7 == 0,  # Monthly Sunday maintenance
    ]
    
    # Random water cutoffs (2% chance per day)
    random_cutoff = random.random() < 0.02
    
    return not (any(cutoff_conditions) or random_cutoff)

def should_activate_pump(simulation_time, predicted_hour, sensor_data):
    """
    Determine if pump should activate based on time and conditions.
    """
    current_hour = simulation_time.hour + simulation_time.minute / 60
    
    # Check if it's time for daily pump cycle (within 30-minute window)
    time_window = 0.5  # 30 minutes
    is_pump_time = abs(current_hour - predicted_hour) < time_window
    
    # Check water availability
    water_available = check_water_availability(simulation_time, sensor_data)
    
    # Additional conditions for activation
    water_level = sensor_data[0][0]
    temperature = sensor_data[0][4]
    
    # Don't pump if water level is too high (>80%) or too low (<15%)
    water_level_ok = 15 <= water_level <= 80
    
    # Don't pump during extreme temperatures
    temp_ok = 10 <= temperature <= 45
    
    return is_pump_time and water_available and water_level_ok and temp_ok

def fallback_prediction(simulation_time):
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
    if simulation_time.weekday() >= 5:  # Weekend
        avg_hour += 0.5
        avg_duration += 10
    
    return avg_hour, avg_duration

def initialize_simulation_csv():
    """Initialize simulation CSV file with headers"""
    if not os.path.exists(SIMULATION_LOG_FILE):
        with open(SIMULATION_LOG_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['simulation_date', 'simulation_time', 'real_time', 'predicted_hour', 
                           'predicted_duration', 'pump_activated', 'pump_running', 'pump_elapsed_minutes',
                           'water_level', 'temperature', 'weekday', 'is_weekend'])

def save_simulation_log(simulation_time, real_time, predicted_hour, predicted_duration, 
                       pump_activated, pump_running, pump_elapsed_minutes, sensor_data, weekday_name):
    """Save simulation log to CSV"""
    with open(SIMULATION_LOG_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            simulation_time.strftime('%Y-%m-%d'),
            simulation_time.strftime('%H:%M'),
            real_time.strftime('%Y-%m-%d %H:%M:%S'),
            f"{predicted_hour:.2f}",
            f"{predicted_duration:.2f}",
            "YES" if pump_activated else "NO",
            "YES" if pump_running else "NO",
            f"{pump_elapsed_minutes:.1f}",
            f"{sensor_data[0][0]:.1f}",
            f"{sensor_data[0][4]:.1f}",
            weekday_name,
            "YES" if simulation_time.weekday() >= 5 else "NO"
        ])

def control_pump(turn_on, simulation_time):
    """Simulate pump control"""
    if turn_on:
        print(f"🚰 Pump ON at {simulation_time.strftime('%H:%M')}")
    else:
        print(f"🛑 Pump OFF at {simulation_time.strftime('%H:%M')}")

def run_simulation():
    """Run 30-day fast-forward simulation"""
    print("🚀 Starting 30-Day Fast-Forward Simulation")
    print(f"⏱️ Speed: 1 minute = 1 hour ({SIMULATION_SPEED}x)")
    print(f"📅 Duration: {SIMULATION_DAYS} days")
    print(f"🎬 Start date: {START_DATE.strftime('%Y-%m-%d')}")
    print("="*60)
    
    # Initialize simulation log
    initialize_simulation_csv()
    
    # Load historical data
    load_historical_data()
    
    # Simulation variables
    current_simulation_time = START_DATE
    end_simulation_time = START_DATE + timedelta(days=SIMULATION_DAYS)
    pump_cycles = 0
    total_pump_time = 0
    pump_running = False
    pump_start_time = None
    pump_duration_minutes = 0
    
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    print(f"🕐 Simulation time: {current_simulation_time.strftime('%Y-%m-%d %H:%M')}")
    print("⏳ Simulation running... (Press Ctrl+C to stop early)")
    
    try:
        while current_simulation_time < end_simulation_time:
            real_time = datetime.now()
            
            # Get sensor data for current simulation time
            sensor_data = get_sensor_data(current_simulation_time)
            
            # Get prediction using historical patterns (more reliable)
            predicted_hour, predicted_duration = get_historical_based_prediction(current_simulation_time)
            
            current_hour = current_simulation_time.hour + current_simulation_time.minute / 60
            weekday_name = weekday_names[current_simulation_time.weekday()]
            
            # Check if pump should activate (within 5-minute window)
            pump_should_activate = should_activate_pump(current_simulation_time, predicted_hour, sensor_data)
            
            # Handle pump activation
            if pump_should_activate and not pump_running:
                pump_running = True
                pump_start_time = current_simulation_time
                pump_duration_minutes = min(predicted_duration, 120)  # Cap at 2 hours for simulation
                
                print(f"⏰ {current_simulation_time.strftime('%m-%d %H:%M')} | {weekday_name} | "
                      f"🔮 Pred: {predicted_hour:.1f}h ({predicted_duration:.0f}min) | "
                      f"💧 Water: {sensor_data[0][0]:.0f}% | 🌡️ Temp: {sensor_data[0][4]:.1f}°C | "
                      f"🚰 PUMP ACTIVATED!")
                
                control_pump(True, current_simulation_time)
                pump_cycles += 1
            
            # Log every hour (whether pump is running or not)
            pump_elapsed_minutes = 0
            if pump_running and pump_start_time:
                pump_elapsed_minutes = (current_simulation_time - pump_start_time).total_seconds() / 60
            
            save_simulation_log(current_simulation_time, real_time, predicted_hour, 
                              predicted_duration, pump_should_activate, pump_running, 
                              pump_elapsed_minutes, sensor_data, weekday_name)
            
            # Display status
            if pump_running:
                # Calculate remaining pump time
                elapsed_minutes = (current_simulation_time - pump_start_time).total_seconds() / 60
                remaining_minutes = pump_duration_minutes - elapsed_minutes
                
                if remaining_minutes <= 0:
                    # Pump cycle complete
                    pump_running = False
                    total_pump_time += pump_duration_minutes
                    control_pump(False, current_simulation_time)
                    print(f"✅ Pump cycle completed at {current_simulation_time.strftime('%m-%d %H:%M')} | "
                          f"Total runtime: {pump_duration_minutes:.0f} minutes")
                else:
                    # Pump still running - show status
                    print(f"🔄 {current_simulation_time.strftime('%m-%d %H:%M')} | {weekday_name} | "
                          f"🚰 PUMP RUNNING | Remaining: {remaining_minutes:.0f}min | "
                          f"💧 Water: {sensor_data[0][0]:.0f}% | 🌡️ Temp: {sensor_data[0][4]:.1f}°C")
            else:
                # Show status every 6 hours when pump is not running
                if current_simulation_time.minute % 60 == 0:
                    time_diff = predicted_hour - current_hour
                    if time_diff > 0:
                        next_pump = f"in {time_diff:.1f}h"
                    else:
                        next_pump = f"in {24 + time_diff:.1f}h"
                    
                    # Check why pump didn't activate (for debugging)
                    water_available = check_water_availability(current_simulation_time, sensor_data)
                    water_level_ok = 15 <= sensor_data[0][0] <= 80
                    temp_ok = 10 <= sensor_data[0][4] <= 45
                    
                    status_msg = f"⏳ {current_simulation_time.strftime('%m-%d %H:%M')} | {weekday_name} | "
                    status_msg += f"🔮 Pred: {predicted_hour:.1f}h | Next pump: {next_pump} | "
                    status_msg += f"💧 Water: {sensor_data[0][0]:.0f}% | 🌡️ Temp: {sensor_data[0][4]:.1f}°C"
                    
                    # Add status indicators
                    if not water_available:
                        status_msg += " | 🚫 Water cutoff"
                    elif not water_level_ok:
                        status_msg += " | ⚠️ Water level issue"
                    elif not temp_ok:
                        status_msg += " | 🌡️ Temperature issue"
                    else:
                        status_msg += " | ✅ Ready"
                    
                    print(status_msg)
            
            # Advance simulation time by 1 hour
            current_simulation_time += timedelta(hours=1)
            
            # Wait 1 minute (simulates 1 hour)
            time.sleep(60 / SIMULATION_SPEED)
    
    except KeyboardInterrupt:
        print("\n⏹️ Simulation stopped by user.")
        if pump_running:
            print("⚠️ Pump was running when stopped.")
    
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

def analyze_simulation_results():
    """Analyze the simulation results"""
    if not os.path.exists(SIMULATION_LOG_FILE):
        print("❌ No simulation log found. Run simulation first.")
        return
    
    print("\n📊 SIMULATION ANALYSIS")
    print("="*40)
    
    # Load simulation data
    sim_data = pd.read_csv(SIMULATION_LOG_FILE)
    sim_data['simulation_date'] = pd.to_datetime(sim_data['simulation_date'])
    
    # Filter pump activations
    pump_activations = sim_data[sim_data['pump_activated'] == 'YES']
    
    print(f"📅 Total days simulated: {len(sim_data['simulation_date'].dt.date.unique())}")
    print(f"🚰 Total pump activations: {len(pump_activations)}")
    print(f"⏱️ Average activations per day: {len(pump_activations)/len(sim_data['simulation_date'].dt.date.unique()):.1f}")
    
    if len(pump_activations) > 0:
        print(f"\n🕐 Average predicted start time: {pump_activations['predicted_hour'].mean():.2f}h")
        print(f"⏱️ Average predicted duration: {pump_activations['predicted_duration'].mean():.2f} minutes")
        
        # Weekday analysis
        weekday_stats = pump_activations.groupby('weekday').size()
        print(f"\n📅 Activations by weekday:")
        for weekday, count in weekday_stats.items():
            print(f"   • {weekday}: {count} activations")
        
        # Weekend vs weekday
        weekend_activations = len(pump_activations[pump_activations['is_weekend'] == 'YES'])
        weekday_activations = len(pump_activations[pump_activations['is_weekend'] == 'NO'])
        print(f"\n📊 Weekend activations: {weekend_activations}")
        print(f"📊 Weekday activations: {weekday_activations}")

if __name__ == "__main__":
    # Run simulation automatically without user input
    run_simulation()
    
    # Automatically analyze results
    print("\n" + "="*60)
    analyze_simulation_results() 
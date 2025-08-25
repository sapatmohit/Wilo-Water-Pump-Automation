"""
Main application file for Wilo Water Pump Automation System

This is the entry point for the professional water pump automation system
with predictive control and beautiful terminal dashboard.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import joblib
import numpy as np
import pandas as pd
import time
import pandas as pd
from datetime import datetime, timedelta
import warnings

# Project imports
from config.settings import (
    START_HOUR_MODEL_PATH, DURATION_MODEL_PATH, LOG_FILE, 
    HISTORICAL_DATA_FILE, CYCLE_CHECK_INTERVAL, PUMP_ACTIVATION_TOLERANCE,
    MAX_DEMO_RUNTIME, FALLBACK_START_HOUR, FALLBACK_DURATION,
    WEEKEND_HOUR_ADJUSTMENT, WEEKEND_DURATION_ADJUSTMENT
)
from src.dashboard.terminal_ui import (
    print_header, print_section, print_info, print_warning, print_error,
    print_success, print_sensor_data, print_historical_analysis,
    print_trends_analysis, print_pump_status, print_prediction,
    print_activation_alert, print_schedule_info, Colors
)
from src.utils.data_handler import (
    load_historical_data, initialize_csv, load_past_usage, save_log_to_csv,
    validate_sensor_data
)
from src.utils.sensors import get_sensor_data
from src.models.prediction import (
    get_comprehensive_prediction, analyze_holiday_impact_for_date,
    get_historical_based_prediction, fallback_prediction
)

# Suppress warnings
warnings.filterwarnings('ignore')

# Global variables
hour_model = None
dur_model = None
historical_data = None

def load_models():
    """Load the trained ML models"""
    global hour_model, dur_model
    try:
        hour_model = joblib.load(START_HOUR_MODEL_PATH)
        dur_model = joblib.load(DURATION_MODEL_PATH)
        print_info("MODEL", "Machine learning models loaded successfully", Colors.OKGREEN)
        return True
    except Exception as e:
        print_warning("MODEL", f"Failed to load ML models: {e}")
        return False

def get_historical_patterns():
    """Analyze historical patterns for better predictions"""
    global historical_data
    if historical_data is None:
        historical_data = load_historical_data()
    
    if historical_data is None:
        return None
    
    # Filter records where pump was actually running (Duration > 0)
    pump_runs = historical_data[historical_data['Duration'] > 0].copy()
    
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

# Remove the old functions that are now replaced by the enhanced prediction module
# def get_historical_based_prediction() - moved to prediction.py
# def fallback_prediction() - moved to prediction.py

def analyze_trends():
    """Analyze recent trends and print insights"""
    past_usage = load_past_usage()
    if len(past_usage) < 3:
        return
    
    recent = past_usage[-7:] if len(past_usage) >= 7 else past_usage[-3:]
    
    avg_hour = np.mean([entry['start_hour'] for entry in recent])
    avg_duration = np.mean([entry['duration'] for entry in recent])
    
    print_trends_analysis(avg_hour, avg_duration)
    
    # Analyze upcoming holidays
    tomorrow = datetime.now() + timedelta(days=1)
    holiday_impact = analyze_holiday_impact_for_date(tomorrow)
    
    if holiday_impact['has_holiday']:
        print_section("UPCOMING HOLIDAYS ANALYSIS")
        for holiday in holiday_impact['holiday_details']:
            days_text = "today" if holiday['days_ahead'] == 0 else f"in {holiday['days_ahead']} days"
            print_info("HOLIDAY", f"{holiday['event_name']} {days_text} - {holiday['impact_level']} impact", Colors.PURPLE)
        
        if holiday_impact['preparation_needed']:
            print_info("ALERT", "High impact holiday detected - increased water demand expected", Colors.WARNING)

def control_pump(turn_on):
    """Control pump operation - replace with actual GPIO/relay logic"""
    print_pump_status(turn_on)

def main_loop():
    """Main application loop"""
    print_header("WILO WATER PUMP AUTOMATION SYSTEM")
    print_info("CONFIG", f"Logging data to: {Colors.BOLD}{LOG_FILE}{Colors.ENDC}", Colors.OKBLUE)
    print_info("CONFIG", f"Using 2-year historical data from: {Colors.BOLD}{HISTORICAL_DATA_FILE}{Colors.ENDC}", Colors.OKBLUE)
    
    # Initialize system
    initialize_csv()
    models_loaded = load_models()
    
    # Load and analyze historical data
    patterns = get_historical_patterns()
    if patterns:
        print_historical_analysis(patterns)
    
    # Load recent usage data
    past_usage = load_past_usage()
    if past_usage:
        print_info("INFO", f"Loaded {Colors.BOLD}{len(past_usage)}{Colors.ENDC} recent records", Colors.OKCYAN)
        analyze_trends()
    
    print_section("SYSTEM MONITORING ACTIVE")
    print_info("STATUS", "System initialization complete. Starting monitoring loop...", Colors.OKGREEN)
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            sensor_data = get_sensor_data()
            
            print_sensor_data(sensor_data, cycle_count)
            
            if not validate_sensor_data(sensor_data):
                print_warning("WARNING", "Sensor error detected. Using historical-based prediction.")
                prediction_result = get_historical_based_prediction()
                predicted_hour, predicted_duration = prediction_result[0], prediction_result[1]
                adjustment_info = prediction_result[2] if len(prediction_result) > 2 else None
            else:
                # Get comprehensive prediction with holiday analysis
                prediction_result = get_comprehensive_prediction(sensor_data)
                predicted_hour = prediction_result['start_hour']
                predicted_duration = prediction_result['duration']
                adjustment_info = prediction_result['adjustment_info']
                
                # Display prediction method and confidence
                method_color = Colors.OKGREEN if prediction_result['method'] == 'machine_learning' else Colors.OKCYAN
                print_info("METHOD", f"Using {prediction_result['method']} (confidence: {prediction_result['confidence']})", method_color)

            now = datetime.now()
            current_hour = now.hour + now.minute / 60

            print_prediction(predicted_hour, predicted_duration)
            
            # Display holiday adjustments if available
            if 'adjustment_info' in locals() and adjustment_info and adjustment_info['factors']['holiday_impact']['has_holiday']:
                print(f"{Colors.PURPLE}[HOLIDAY] {adjustment_info['explanation']}{Colors.ENDC}")
                hour_change_min = adjustment_info['adjustments']['hour_change_minutes']
                duration_change_min = adjustment_info['adjustments']['duration_change_minutes']
                if hour_change_min != 0:
                    print(f"{Colors.PURPLE}[ADJUST] Start time: {hour_change_min:+.0f} minutes, Duration: {duration_change_min:+.0f} minutes{Colors.ENDC}")

            # Smart tolerance: ~5 min window
            if abs(current_hour - predicted_hour) < PUMP_ACTIVATION_TOLERANCE:
                print_activation_alert()
                control_pump(True)
                
                # Simulate pump running (in real system, monitor actual pump status)
                print_info("STATUS", f"Pump operating for {Colors.BOLD}{predicted_duration:.2f} minutes{Colors.ENDC}...", Colors.OKCYAN)
                time.sleep(min(predicted_duration * 60, MAX_DEMO_RUNTIME))
                
                control_pump(False)
                save_log_to_csv(predicted_hour, predicted_duration, sensor_data)
                
                print_success("STATUS", "Cycle completed successfully. Waiting for next prediction window.")
                time.sleep(CYCLE_CHECK_INTERVAL)
            else:
                time_diff = predicted_hour - current_hour
                print_schedule_info(time_diff)
                
                # Check every minute
                time.sleep(CYCLE_CHECK_INTERVAL)

        except KeyboardInterrupt:
            print_header("SYSTEM SHUTDOWN")
            print_info("SYSTEM", "System stopped by user.", Colors.WARNING)
            break
        except Exception as e:
            print_error("ERROR", f"System error: {e}")
            time.sleep(CYCLE_CHECK_INTERVAL)

if __name__ == "__main__":
    main_loop()
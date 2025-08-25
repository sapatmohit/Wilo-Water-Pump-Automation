import pandas as pd
import numpy as np
from datetime import datetime

def load_historical_data():
    """Load the 2-year historical dataset"""
    print("📊 Loading 2-year historical data...")
    data = pd.read_csv('synthetic_water_data.csv')
    data['Date'] = pd.to_datetime(data['Date'])
    data['Hour'] = pd.to_datetime(data['Hour'], format='%H:%M').dt.hour
    print(f"✅ Loaded {len(data)} historical records from {data['Date'].min().date()} to {data['Date'].max().date()}")
    return data

def analyze_historical_patterns():
    """Analyze historical patterns for better predictions"""
    data = load_historical_data()
    
    # Filter records where pump was actually running (Duration > 0)
    pump_runs = data[data['Duration'] > 0].copy()
    
    print(f"\n🔍 Found {len(pump_runs)} pump run records out of {len(data)} total records")
    
    if len(pump_runs) == 0:
        print("⚠️ No historical pump run data found.")
        return None
    
    # Calculate patterns
    patterns = {
        'avg_start_hour': pump_runs['Hour'].mean(),
        'avg_duration': pump_runs['Duration'].mean(),
        'common_start_hours': pump_runs['Hour'].value_counts().head(5).to_dict(),
        'weekday_patterns': {},
        'monthly_patterns': {},
        'temperature_effects': {}
    }
    
    # Weekday patterns
    pump_runs['weekday'] = pump_runs['Date'].dt.weekday
    weekday_stats = pump_runs.groupby('weekday').agg({
        'Hour': 'mean',
        'Duration': 'mean',
        'Date': 'count'
    }).round(2)
    patterns['weekday_patterns'] = weekday_stats.to_dict()
    
    # Monthly patterns
    pump_runs['month'] = pump_runs['Date'].dt.month
    monthly_stats = pump_runs.groupby('month').agg({
        'Hour': 'mean',
        'Duration': 'mean',
        'Date': 'count'
    }).round(2)
    patterns['monthly_patterns'] = monthly_stats.to_dict()
    
    # Temperature effects
    temp_bins = pd.cut(pump_runs['Temperature'], bins=[-10, 10, 20, 30, 40])
    temp_stats = pump_runs.groupby(temp_bins).agg({
        'Hour': 'mean',
        'Duration': 'mean',
        'Date': 'count'
    }).round(2)
    patterns['temperature_effects'] = temp_stats.to_dict()
    
    return patterns

def display_analysis():
    """Display comprehensive historical analysis"""
    patterns = analyze_historical_patterns()
    
    if patterns is None:
        return
    
    print("\n" + "="*60)
    print("📈 HISTORICAL ANALYSIS (2-Year Data)")
    print("="*60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   • Average start time: {patterns['avg_start_hour']:.2f}h ({patterns['avg_start_hour']:.0f}:{int((patterns['avg_start_hour'] % 1) * 60):02d})")
    print(f"   • Average duration: {patterns['avg_duration']:.2f} minutes")
    
    print(f"\n🕐 Most common start times:")
    for hour, count in patterns['common_start_hours'].items():
        print(f"   • {hour}:00 - {count} times ({count/len(patterns['common_start_hours'])*100:.1f}%)")
    
    print(f"\n📅 Weekday patterns:")
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for weekday, stats in patterns['weekday_patterns']['Hour'].items():
        duration = patterns['weekday_patterns']['Duration'][weekday]
        count = patterns['weekday_patterns']['Date'][weekday]
        print(f"   • {weekday_names[weekday]}: {stats:.2f}h start, {duration:.2f}min duration, {count} runs")
    
    print(f"\n📆 Monthly patterns:")
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    for month, stats in patterns['monthly_patterns']['Hour'].items():
        duration = patterns['monthly_patterns']['Duration'][month]
        count = patterns['monthly_patterns']['Date'][month]
        print(f"   • {month_names[month-1]}: {stats:.2f}h start, {duration:.2f}min duration, {count} runs")
    
    print(f"\n🌡️ Temperature effects:")
    for temp_range, stats in patterns['temperature_effects']['Hour'].items():
        duration = patterns['temperature_effects']['Duration'][temp_range]
        count = patterns['temperature_effects']['Date'][temp_range]
        print(f"   • {temp_range}: {stats:.2f}h start, {duration:.2f}min duration, {count} runs")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    display_analysis() 
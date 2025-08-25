"""
Prediction models and algorithms for the Wilo Water Pump Automation System

This module handles ML model predictions, historical pattern analysis,
and holiday-based demand forecasting for optimal pump scheduling.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from config.settings import (
    FALLBACK_START_HOUR, FALLBACK_DURATION,
    WEEKEND_HOUR_ADJUSTMENT, WEEKEND_DURATION_ADJUSTMENT
)
from src.utils.data_handler import load_historical_data
from src.utils.holiday_predictor import holiday_predictor

def get_historical_patterns():
    """Analyze historical patterns for better predictions"""
    data = load_historical_data()
    
    if data is None:
        return None
    
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

def load_models():
    """Load trained ML models"""
    import joblib
    from config.settings import START_HOUR_MODEL_PATH, DURATION_MODEL_PATH
    
    try:
        hour_model = joblib.load(START_HOUR_MODEL_PATH)
        dur_model = joblib.load(DURATION_MODEL_PATH)
        return hour_model, dur_model
    except Exception as e:
        print(f"[WARNING] Failed to load ML models: {e}")
        return None, None

def predict_with_ml(sensor_data, target_date=None):
    """Make predictions using ML models with holiday adjustments"""
    hour_model, dur_model = load_models()
    
    if hour_model is None or dur_model is None:
        return None, None, None
    
    if target_date is None:
        target_date = datetime.now()
    
    try:
        base_predicted_hour = hour_model.predict(sensor_data)[0]
        base_predicted_duration = dur_model.predict(sensor_data)[0]
        
        # Apply holiday and weekend adjustments
        adjustment_info = holiday_predictor.get_comprehensive_prediction_adjustment(
            target_date, base_predicted_hour, base_predicted_duration
        )
        
        return (adjustment_info['adjusted']['start_hour'], 
                adjustment_info['adjusted']['duration'], 
                adjustment_info)
    except Exception as e:
        print(f"[ERROR] ML prediction failed: {e}")
        return None, None, None

def get_historical_based_prediction(target_date=None):
    """Get prediction based on historical patterns for similar conditions"""
    data = load_historical_data()
    
    if data is None:
        return fallback_prediction(target_date)
    
    if target_date is None:
        target_date = datetime.now()
    
    # Get pump runs for similar conditions
    similar_runs = data[
        (data['Date'].dt.month == target_date.month) &
        (data['Date'].dt.weekday == target_date.weekday()) &
        (data['Duration'] > 0)
    ]
    
    if len(similar_runs) > 0:
        # Use historical patterns
        base_hour = similar_runs['Hour'].mean()
        base_duration = similar_runs['Duration'].mean()
        
        # Apply holiday and weekend adjustments
        adjustment_info = holiday_predictor.get_comprehensive_prediction_adjustment(
            target_date, base_hour, base_duration
        )
        
        return adjustment_info['adjusted']['start_hour'], adjustment_info['adjusted']['duration'], adjustment_info
    else:
        return fallback_prediction(target_date)

def fallback_prediction(target_date=None):
    """Fallback prediction based on historical data patterns"""
    patterns = get_historical_patterns()
    
    if target_date is None:
        target_date = datetime.now()
    
    if patterns is None:
        base_hour = FALLBACK_START_HOUR
        base_duration = FALLBACK_DURATION
    else:
        # Use overall historical averages
        base_hour = patterns['avg_start_hour']
        base_duration = patterns['avg_duration']
    
    # Apply holiday and weekend adjustments
    adjustment_info = holiday_predictor.get_comprehensive_prediction_adjustment(
        target_date, base_hour, base_duration
    )
    
    return adjustment_info['adjusted']['start_hour'], adjustment_info['adjusted']['duration'], adjustment_info

def get_comprehensive_prediction(sensor_data, target_date=None):
    """Get comprehensive prediction with holiday analysis and explanations"""
    if target_date is None:
        target_date = datetime.now()
    
    # Try ML model first
    ml_result = predict_with_ml(sensor_data, target_date)
    if ml_result[0] is not None:
        return {
            'method': 'machine_learning',
            'start_hour': ml_result[0],
            'duration': ml_result[1],
            'adjustment_info': ml_result[2],
            'confidence': 'high'
        }
    
    # Fall back to historical patterns
    hist_result = get_historical_based_prediction(target_date)
    return {
        'method': 'historical_patterns',
        'start_hour': hist_result[0],
        'duration': hist_result[1],
        'adjustment_info': hist_result[2],
        'confidence': 'medium'
    }

def analyze_trends():
    """Analyze recent trends and return insights"""
    from src.utils.data_handler import load_past_usage
    
    past_usage = load_past_usage()
    if len(past_usage) < 3:
        return None
    
    recent = past_usage[-7:] if len(past_usage) >= 7 else past_usage[-3:]
    
    avg_hour = np.mean([entry['start_hour'] for entry in recent])
    avg_duration = np.mean([entry['duration'] for entry in recent])
    
    return {
        'avg_hour': avg_hour,
        'avg_duration': avg_duration,
        'sample_size': len(recent)
    }

def analyze_holiday_impact_for_date(target_date):
    """Analyze holiday impact for a specific date"""
    return holiday_predictor.get_holiday_impact(target_date, look_ahead_days=3)
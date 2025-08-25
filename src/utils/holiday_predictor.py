"""
Holiday Predictor Module for Wilo Water Pump Automation System

This module analyzes holiday and festival data to predict increased water demand
and adjust pump operation schedules accordingly.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import get_absolute_path

# Holiday data file path
HOLIDAY_DATA_FILE = get_absolute_path('data/raw/Holidays_2020_2030.csv')

# Holiday impact factors for different types of events
HOLIDAY_IMPACT_FACTORS = {
    'high_demand': {
        'festivals': ['Holi', 'Diwali', 'Eid', 'Christmas', 'Dussehra', 'Ganesh Chaturthi', 'Durga', 'Navratri'],
        'hour_adjustment': -1.5,  # Start 1.5 hours earlier
        'duration_multiplier': 1.4,  # 40% longer duration
        'description': 'Major festivals with high water usage'
    },
    'medium_demand': {
        'festivals': ['Independence Day', 'Republic Day', 'Gandhi Jayanti', 'New Year', 'Valentine', 'Diwas'],
        'hour_adjustment': -0.5,  # Start 30 minutes earlier
        'duration_multiplier': 1.2,  # 20% longer duration
        'description': 'National holidays and celebrations'
    },
    'low_demand': {
        'festivals': ['Guru', 'Jayanti', 'Purnima', 'Ekadashi', 'Ashtami', 'Navami'],
        'hour_adjustment': -0.25,  # Start 15 minutes earlier
        'duration_multiplier': 1.1,  # 10% longer duration
        'description': 'Religious observances with moderate impact'
    }
}

class HolidayPredictor:
    """
    Predicts water demand adjustments based on holidays and festivals.
    """
    
    def __init__(self):
        self.holiday_data = None
        self.load_holiday_data()
    
    def load_holiday_data(self):
        """Load holiday data from CSV file"""
        try:
            self.holiday_data = pd.read_csv(HOLIDAY_DATA_FILE)
            self.holiday_data['date'] = pd.to_datetime(self.holiday_data['date'], format='%B %d, %Y, %A')
            print(f"[INFO] Loaded {len(self.holiday_data)} holiday records from 2020-2030")
        except Exception as e:
            print(f"[ERROR] Failed to load holiday data: {e}")
            self.holiday_data = None
    
    def get_holiday_impact(self, target_date, look_ahead_days=2):
        """
        Analyze holiday impact for a given date and nearby dates.
        
        Args:
            target_date (datetime): The date to analyze
            look_ahead_days (int): Number of days to look ahead for upcoming holidays
            
        Returns:
            dict: Holiday impact analysis including adjustments
        """
        if self.holiday_data is None:
            return self._get_default_impact()
        
        # Convert target_date to datetime if it's not already
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')
        
        # Check for holidays on target date and upcoming days
        date_range = [target_date + timedelta(days=i) for i in range(look_ahead_days + 1)]
        
        impact_analysis = {
            'has_holiday': False,
            'holiday_details': [],
            'hour_adjustment': 0.0,
            'duration_multiplier': 1.0,
            'impact_level': 'none',
            'preparation_needed': False
        }
        
        max_impact = 0.0
        cumulative_hour_adjustment = 0.0
        cumulative_duration_multiplier = 1.0
        
        for i, check_date in enumerate(date_range):
            holidays_on_date = self._get_holidays_for_date(check_date)
            
            if holidays_on_date:
                for holiday in holidays_on_date:
                    impact_info = self._analyze_holiday_impact(holiday, days_ahead=i)
                    impact_analysis['holiday_details'].append(impact_info)
                    
                    # Calculate cumulative impact
                    if impact_info['impact_weight'] > max_impact:
                        max_impact = impact_info['impact_weight']
                        impact_analysis['impact_level'] = impact_info['impact_level']
                    
                    # Adjust factors based on proximity
                    proximity_factor = 1.0 - (i * 0.3)  # Reduce impact for future days
                    cumulative_hour_adjustment += impact_info['hour_adjustment'] * proximity_factor
                    cumulative_duration_multiplier *= (1 + (impact_info['duration_multiplier'] - 1) * proximity_factor)
        
        if impact_analysis['holiday_details']:
            impact_analysis['has_holiday'] = True
            impact_analysis['hour_adjustment'] = cumulative_hour_adjustment
            impact_analysis['duration_multiplier'] = cumulative_duration_multiplier
            impact_analysis['preparation_needed'] = max_impact >= 0.6  # High impact holidays
        
        return impact_analysis
    
    def _get_holidays_for_date(self, check_date):
        """Get all holidays for a specific date"""
        if self.holiday_data is None:
            return []
        
        # Filter holidays for the specific date
        date_holidays = self.holiday_data[
            self.holiday_data['date'].dt.date == check_date.date()
        ]
        
        return date_holidays.to_dict('records') if not date_holidays.empty else []
    
    def _analyze_holiday_impact(self, holiday_record, days_ahead=0):
        """Analyze the impact of a specific holiday"""
        event_name = holiday_record['event']
        event_type = holiday_record['type']
        
        # Determine impact level based on festival name matching
        impact_level = 'low_demand'
        impact_weight = 0.3
        
        # Check for high impact festivals
        for keyword in HOLIDAY_IMPACT_FACTORS['high_demand']['festivals']:
            if keyword.lower() in event_name.lower():
                impact_level = 'high_demand'
                impact_weight = 1.0
                break
        
        # Check for medium impact if not high
        if impact_level != 'high_demand':
            for keyword in HOLIDAY_IMPACT_FACTORS['medium_demand']['festivals']:
                if keyword.lower() in event_name.lower():
                    impact_level = 'medium_demand'
                    impact_weight = 0.6
                    break
        
        # Get impact factors
        factors = HOLIDAY_IMPACT_FACTORS[impact_level]
        
        return {
            'event_name': event_name,
            'event_type': event_type,
            'impact_level': impact_level,
            'impact_weight': impact_weight,
            'hour_adjustment': factors['hour_adjustment'],
            'duration_multiplier': factors['duration_multiplier'],
            'days_ahead': days_ahead,
            'description': factors['description']
        }
    
    def _get_default_impact(self):
        """Return default impact when no holiday data is available"""
        return {
            'has_holiday': False,
            'holiday_details': [],
            'hour_adjustment': 0.0,
            'duration_multiplier': 1.0,
            'impact_level': 'none',
            'preparation_needed': False
        }
    
    def get_weekend_adjustment(self, target_date):
        """Get adjustment factors for weekends"""
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')
        
        if target_date.weekday() >= 5:  # Saturday or Sunday
            return {
                'is_weekend': True,
                'hour_adjustment': -0.5,  # Start 30 minutes earlier
                'duration_multiplier': 1.15,  # 15% longer duration
                'reason': 'Weekend increased usage'
            }
        
        return {
            'is_weekend': False,
            'hour_adjustment': 0.0,
            'duration_multiplier': 1.0,
            'reason': 'Regular weekday'
        }
    
    def get_comprehensive_prediction_adjustment(self, target_date, base_hour, base_duration):
        """
        Get comprehensive prediction adjustments considering holidays and weekends.
        
        Args:
            target_date (datetime): Date to analyze
            base_hour (float): Base predicted start hour
            base_duration (float): Base predicted duration
            
        Returns:
            dict: Comprehensive adjustment information
        """
        holiday_impact = self.get_holiday_impact(target_date)
        weekend_impact = self.get_weekend_adjustment(target_date)
        
        # Calculate total adjustments
        total_hour_adjustment = holiday_impact['hour_adjustment'] + weekend_impact['hour_adjustment']
        total_duration_multiplier = holiday_impact['duration_multiplier'] * weekend_impact['duration_multiplier']
        
        # Apply adjustments
        adjusted_hour = max(0.0, min(23.99, base_hour + total_hour_adjustment))
        adjusted_duration = base_duration * total_duration_multiplier
        
        return {
            'original': {
                'start_hour': base_hour,
                'duration': base_duration
            },
            'adjusted': {
                'start_hour': adjusted_hour,
                'duration': adjusted_duration
            },
            'adjustments': {
                'hour_change': total_hour_adjustment,
                'duration_multiplier': total_duration_multiplier,
                'hour_change_minutes': total_hour_adjustment * 60,
                'duration_change_minutes': (adjusted_duration - base_duration)
            },
            'factors': {
                'holiday_impact': holiday_impact,
                'weekend_impact': weekend_impact
            },
            'explanation': self._generate_explanation(holiday_impact, weekend_impact)
        }
    
    def _generate_explanation(self, holiday_impact, weekend_impact):
        """Generate human-readable explanation for adjustments"""
        explanations = []
        
        if holiday_impact['has_holiday']:
            for holiday in holiday_impact['holiday_details']:
                explanations.append(f"Upcoming {holiday['event_name']} ({holiday['impact_level']} impact)")
        
        if weekend_impact['is_weekend']:
            explanations.append("Weekend increased usage pattern")
        
        if not explanations:
            explanations.append("Standard weekday operation")
        
        return "; ".join(explanations)

# Global instance for easy access
holiday_predictor = HolidayPredictor()
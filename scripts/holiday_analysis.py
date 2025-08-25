#!/usr/bin/env python3
"""
Holiday Analysis Utility for Wilo Water Pump Automation System

This utility demonstrates how the holiday prediction system works and shows
upcoming holidays that may affect water demand patterns.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from datetime import datetime, timedelta
from src.utils.holiday_predictor import holiday_predictor
from src.dashboard.terminal_ui import (
    print_header, print_section, print_info, print_warning, 
    Colors, print_success
)

def analyze_holiday_impact_demo():
    """Demonstrate holiday impact analysis"""
    print_header("HOLIDAY IMPACT ANALYSIS DEMO")
    
    # Analyze next 30 days
    today = datetime.now()
    
    print_section("ANALYZING NEXT 30 DAYS FOR HOLIDAY IMPACTS")
    
    significant_holidays = []
    
    for days_ahead in range(30):
        check_date = today + timedelta(days=days_ahead)
        holiday_impact = holiday_predictor.get_holiday_impact(check_date, look_ahead_days=1)
        
        if holiday_impact['has_holiday']:
            for holiday in holiday_impact['holiday_details']:
                if holiday['impact_weight'] >= 0.6:  # Medium to high impact
                    significant_holidays.append({
                        'date': check_date,
                        'days_ahead': days_ahead,
                        'holiday': holiday
                    })
    
    if significant_holidays:
        print_info("FOUND", f"Found {len(significant_holidays)} significant holidays in next 30 days", Colors.OKGREEN)
        
        for item in significant_holidays:
            date_str = item['date'].strftime('%Y-%m-%d (%A)')
            days_text = "today" if item['days_ahead'] == 0 else f"in {item['days_ahead']} days"
            
            impact_color = Colors.FAIL if item['holiday']['impact_level'] == 'high_demand' else Colors.WARNING
            print_info("HOLIDAY", f"{item['holiday']['event_name']} - {date_str} ({days_text})", impact_color)
            print(f"   Impact: {item['holiday']['impact_level']} | Weight: {item['holiday']['impact_weight']:.1f}")
            print(f"   Adjustments: Start {item['holiday']['hour_adjustment']:+.1f}h, Duration ×{item['holiday']['duration_multiplier']:.1f}")
    else:
        print_info("INFO", "No significant holidays found in next 30 days", Colors.OKCYAN)

def test_prediction_adjustments():
    """Test prediction adjustments for specific scenarios"""
    print_section("PREDICTION ADJUSTMENT TESTING")
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Regular weekday',
            'date': datetime(2025, 8, 27),  # Wednesday
            'base_hour': 7.0,
            'base_duration': 90
        },
        {
            'name': 'Weekend day',
            'date': datetime(2025, 8, 30),  # Saturday
            'base_hour': 7.0,
            'base_duration': 90
        },
        {
            'name': 'Major festival (hypothetical Diwali)',
            'date': datetime(2025, 11, 1),  # Check actual Diwali date
            'base_hour': 7.0,
            'base_duration': 90
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{Colors.OKBLUE}Testing: {test_case['name']}{Colors.ENDC}")
        print(f"Date: {test_case['date'].strftime('%Y-%m-%d (%A)')}")
        
        adjustment_info = holiday_predictor.get_comprehensive_prediction_adjustment(\n            test_case['date'], test_case['base_hour'], test_case['base_duration']\n        )\n        \n        print(f\"Original: {test_case['base_hour']:.1f}h start, {test_case['base_duration']:.0f}min duration\")\n        print(f\"Adjusted: {adjustment_info['adjusted']['start_hour']:.1f}h start, {adjustment_info['adjusted']['duration']:.0f}min duration\")\n        print(f\"Changes: {adjustment_info['adjustments']['hour_change_minutes']:+.0f}min start, {adjustment_info['adjustments']['duration_change_minutes']:+.0f}min duration\")\n        print(f\"Reason: {adjustment_info['explanation']}\")\n\ndef show_holiday_calendar():\n    \"\"\"Show upcoming holidays in calendar format\"\"\"\n    print_section(\"UPCOMING HOLIDAYS CALENDAR\")\n    \n    today = datetime.now()\n    \n    # Group holidays by month\n    monthly_holidays = {}\n    \n    for days_ahead in range(90):  # Next 3 months\n        check_date = today + timedelta(days=days_ahead)\n        holidays = holiday_predictor._get_holidays_for_date(check_date)\n        \n        if holidays:\n            month_key = check_date.strftime('%Y-%m')\n            if month_key not in monthly_holidays:\n                monthly_holidays[month_key] = []\n            \n            for holiday in holidays:\n                monthly_holidays[month_key].append({\n                    'date': check_date,\n                    'holiday': holiday\n                })\n    \n    for month_key in sorted(monthly_holidays.keys()):\n        month_name = datetime.strptime(month_key, '%Y-%m').strftime('%B %Y')\n        print(f\"\\n{Colors.HEADER}{month_name}{Colors.ENDC}\")\n        print(\"-\" * 40)\n        \n        for item in monthly_holidays[month_key]:\n            date_str = item['date'].strftime('%d %a')\n            event_type_color = {\n                'Govt': Colors.OKBLUE,\n                'Hindu': Colors.PURPLE,\n                'Islamic': Colors.OKCYAN,\n                'Christian': Colors.OKGREEN,\n                'Modern': Colors.YELLOW\n            }.get(item['holiday']['type'], Colors.WHITE)\n            \n            print(f\"{date_str} - {event_type_color}{item['holiday']['event']} ({item['holiday']['type']}){Colors.ENDC}\")\n\ndef main():\n    \"\"\"Main function to run holiday analysis demos\"\"\"\n    print_header(\"WILO PUMP HOLIDAY ANALYSIS UTILITY\")\n    \n    if len(sys.argv) > 1:\n        command = sys.argv[1].lower()\n        \n        if command == 'impact':\n            analyze_holiday_impact_demo()\n        elif command == 'test':\n            test_prediction_adjustments()\n        elif command == 'calendar':\n            show_holiday_calendar()\n        else:\n            print_warning(\"ERROR\", f\"Unknown command: {command}\")\n            show_usage()\n    else:\n        # Run all demos\n        analyze_holiday_impact_demo()\n        test_prediction_adjustments()\n        show_holiday_calendar()\n\ndef show_usage():\n    \"\"\"Show usage information\"\"\"\n    print_section(\"USAGE\")\n    print(\"python scripts/holiday_analysis.py [command]\")\n    print(\"\\nCommands:\")\n    print(\"  impact   - Analyze holiday impacts for next 30 days\")\n    print(\"  test     - Test prediction adjustments for scenarios\")\n    print(\"  calendar - Show upcoming holidays calendar\")\n    print(\"  (no args) - Run all demos\")\n\nif __name__ == \"__main__\":\n    main()
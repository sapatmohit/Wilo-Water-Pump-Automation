"""
Professional Terminal Dashboard for Wilo Water Pump Automation System

This module provides a comprehensive set of styling and display functions
for creating a professional terminal-based dashboard interface.
"""

import warnings
from datetime import datetime

# Suppress warnings
warnings.filterwarnings('ignore')

# ANSI Color codes for terminal styling
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    # Additional colors
    PURPLE = '\033[35m'
    YELLOW = '\033[33m'
    WHITE = '\033[37m'
    GREY = '\033[90m'

def print_header(text, width=70):
    """Print a styled header with borders"""
    print(f"\n{Colors.OKCYAN}{'┌' + '─' * (width-2) + '┐'}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}│{Colors.BOLD}{text:^{width-2}}{Colors.ENDC}{Colors.OKCYAN}│{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'└' + '─' * (width-2) + '┘'}{Colors.ENDC}")

def print_section(title, width=70):
    """Print a styled section header"""
    print(f"\n{Colors.OKBLUE}{'╭' + '─' * (width-2) + '╮'}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}│{Colors.BOLD} {title:<{width-4}} {Colors.ENDC}{Colors.OKBLUE}│{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'╰' + '─' * (width-2) + '╯'}{Colors.ENDC}")

def print_info(tag, message, color=Colors.OKGREEN):
    """Print styled info message"""
    print(f"{color}[{tag}]{Colors.ENDC} {message}")

def print_warning(tag, message):
    """Print styled warning message"""
    print(f"{Colors.WARNING}[{tag}]{Colors.ENDC} {Colors.YELLOW}{message}{Colors.ENDC}")

def print_error(tag, message):
    """Print styled error message"""
    print(f"{Colors.FAIL}[{tag}]{Colors.ENDC} {Colors.FAIL}{message}{Colors.ENDC}")

def print_success(tag, message):
    """Print styled success message"""
    print(f"{Colors.OKGREEN}[{tag}]{Colors.ENDC} {Colors.OKGREEN}{message}{Colors.ENDC}")

def print_sensor_data(sensor_data, cycle_count):
    """Print beautifully formatted sensor data"""
    print(f"\n{Colors.PURPLE}{'╔' + '═' * 68 + '╗'}{Colors.ENDC}")
    print(f"{Colors.PURPLE}║{Colors.BOLD} CYCLE {cycle_count:04d} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {Colors.ENDC}{Colors.PURPLE}║{Colors.ENDC}")
    print(f"{Colors.PURPLE}{'╠' + '═' * 68 + '╣'}{Colors.ENDC}")
    print(f"{Colors.PURPLE}║{Colors.ENDC} {Colors.OKCYAN}Water Level:{Colors.ENDC} {Colors.BOLD}{sensor_data[0][0]:.1f}%{Colors.ENDC}  {Colors.OKCYAN}Flow Rate:{Colors.ENDC} {Colors.BOLD}{sensor_data[0][1]:.1f}L/min{Colors.ENDC}  {Colors.OKCYAN}Temp:{Colors.ENDC} {Colors.BOLD}{sensor_data[0][4]:.1f}°C{Colors.ENDC} {Colors.PURPLE}║{Colors.ENDC}")
    print(f"{Colors.PURPLE}║{Colors.ENDC} {Colors.OKCYAN}Voltage:{Colors.ENDC} {Colors.BOLD}{sensor_data[0][2]:.1f}V{Colors.ENDC}     {Colors.OKCYAN}Current:{Colors.ENDC} {Colors.BOLD}{sensor_data[0][3]:.2f}A{Colors.ENDC}      {Colors.OKCYAN}Humidity:{Colors.ENDC} {Colors.BOLD}{sensor_data[0][5]:.1f}%{Colors.ENDC} {Colors.PURPLE}║{Colors.ENDC}")
    print(f"{Colors.PURPLE}{'╚' + '═' * 68 + '╝'}{Colors.ENDC}")

def print_historical_analysis(patterns):
    """Print formatted historical analysis"""
    if patterns is None:
        print_warning("WARNING", "No historical pump run data found.")
        return
    
    print_section("HISTORICAL DATA ANALYSIS (2-YEAR DATASET)")
    print(f"{Colors.OKCYAN}   Average start time:{Colors.ENDC} {Colors.BOLD}{patterns['avg_start_hour']:.2f}h{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Average duration:{Colors.ENDC} {Colors.BOLD}{patterns['avg_duration']:.2f} minutes{Colors.ENDC}")
    
    print(f"\n{Colors.OKBLUE}Most Common Start Times:{Colors.ENDC}")
    print(f"{Colors.GREY}{'─' * 40}{Colors.ENDC}")
    for hour, count in patterns['common_start_hours'].items():
        print(f"{Colors.OKCYAN}   {hour}:00{Colors.ENDC} - {Colors.BOLD}{count} times{Colors.ENDC}")
    
    print(f"\n{Colors.OKBLUE}Weekday Patterns:{Colors.ENDC}")
    print(f"{Colors.GREY}{'─' * 40}{Colors.ENDC}")
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for weekday, stats in patterns['weekday_patterns']['Hour'].items():
        duration = patterns['weekday_patterns']['Duration'][weekday]
        print(f"{Colors.OKCYAN}   {weekday_names[weekday]}:{Colors.ENDC} {Colors.BOLD}{stats:.2f}h{Colors.ENDC} start, {Colors.BOLD}{duration:.2f}min{Colors.ENDC} duration")
    
    print(f"\n{Colors.OKBLUE}Temperature Effects:{Colors.ENDC}")
    print(f"{Colors.GREY}{'─' * 40}{Colors.ENDC}")
    for temp_range, stats in patterns['temperature_effects']['Hour'].items():
        duration = patterns['temperature_effects']['Duration'][temp_range]
        print(f"{Colors.OKCYAN}   {temp_range}:{Colors.ENDC} {Colors.BOLD}{stats:.2f}h{Colors.ENDC} start, {Colors.BOLD}{duration:.2f}min{Colors.ENDC} duration")

def print_trends_analysis(avg_hour, avg_duration):
    """Print formatted trends analysis"""
    print_section("RECENT TRENDS ANALYSIS")
    print(f"{Colors.OKCYAN}   Average start time:{Colors.ENDC} {Colors.BOLD}{avg_hour:.2f}h{Colors.ENDC}")
    print(f"{Colors.OKCYAN}   Average duration:{Colors.ENDC} {Colors.BOLD}{avg_duration:.2f}min{Colors.ENDC}")

def print_pump_status(turn_on):
    """Print formatted pump status"""
    if turn_on:
        print_info("CONTROL", f"{Colors.OKGREEN}PUMP STATUS: {Colors.BOLD}ACTIVE{Colors.ENDC}", Colors.OKGREEN)
    else:
        print_info("CONTROL", f"{Colors.FAIL}PUMP STATUS: {Colors.BOLD}INACTIVE{Colors.ENDC}", Colors.FAIL)

def print_prediction(predicted_hour, predicted_duration):
    """Print formatted prediction results"""
    print(f"\n{Colors.HEADER}PREDICTION:{Colors.ENDC} Start at {Colors.BOLD}{predicted_hour:.2f}h{Colors.ENDC} ({Colors.BOLD}{predicted_hour:.0f}:{int((predicted_hour % 1) * 60):02d}{Colors.ENDC}) | Duration: {Colors.BOLD}{predicted_duration:.2f} min{Colors.ENDC}")

def print_activation_alert():
    """Print pump activation alert"""
    print(f"\n{Colors.OKGREEN}{'-' * 60}{Colors.ENDC}")
    print_info("ACTION", f"{Colors.BOLD}PUMP ACTIVATION TRIGGERED{Colors.ENDC}", Colors.OKGREEN)
    print(f"{Colors.OKGREEN}{'-' * 60}{Colors.ENDC}")

def print_schedule_info(time_diff):
    """Print scheduling information"""
    if time_diff > 0:
        print_info("SCHEDULE", f"Next pump cycle scheduled in {Colors.BOLD}{time_diff:.2f} hours{Colors.ENDC}", Colors.PURPLE)
    else:
        print_info("SCHEDULE", f"Next pump cycle scheduled in {Colors.BOLD}{24 + time_diff:.2f} hours{Colors.ENDC}", Colors.PURPLE)

def print_holiday_impact(holiday_info):
    """Print holiday impact information"""
    if not holiday_info['has_holiday']:
        return
    
    print_section("HOLIDAY IMPACT ANALYSIS")
    
    for holiday in holiday_info['holiday_details']:
        days_text = "today" if holiday['days_ahead'] == 0 else f"in {holiday['days_ahead']} days"
        impact_color = {
            'high_demand': Colors.FAIL,
            'medium_demand': Colors.WARNING,
            'low_demand': Colors.OKCYAN
        }.get(holiday['impact_level'], Colors.WHITE)
        
        print_info("HOLIDAY", f"{holiday['event_name']} {days_text}", impact_color)
        print(f"   Impact Level: {holiday['impact_level']} | Weight: {holiday['impact_weight']:.1f}")
        print(f"   Adjustments: Start {holiday['hour_adjustment']:+.1f}h, Duration ×{holiday['duration_multiplier']:.1f}")
    
    if holiday_info['preparation_needed']:
        print_info("ALERT", "High impact holiday detected - increased water demand expected", Colors.WARNING)

def print_prediction_details(prediction_result):
    """Print detailed prediction information including holiday adjustments"""
    method_color = Colors.OKGREEN if prediction_result.get('method') == 'machine_learning' else Colors.OKCYAN
    
    print_info("METHOD", f"Using {prediction_result.get('method', 'unknown')} (confidence: {prediction_result.get('confidence', 'unknown')})", method_color)
    
    # Show base vs adjusted predictions if available
    adjustment_info = prediction_result.get('adjustment_info')
    if adjustment_info:
        original = adjustment_info['original']
        adjusted = adjustment_info['adjusted']
        
        if adjustment_info['adjustments']['hour_change'] != 0 or adjustment_info['adjustments']['duration_multiplier'] != 1.0:
            print(f"{Colors.GREY}   Base prediction: {original['start_hour']:.2f}h, {original['duration']:.0f}min{Colors.ENDC}")
            print(f"{Colors.OKGREEN}   Adjusted prediction: {adjusted['start_hour']:.2f}h, {adjusted['duration']:.0f}min{Colors.ENDC}")
            
            if adjustment_info['factors']['holiday_impact']['has_holiday']:
                print(f"{Colors.PURPLE}   Holiday factor: {adjustment_info['explanation']}{Colors.ENDC}")
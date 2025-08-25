"""
Configuration file for Wilo Water Pump Automation System
"""

import os

# File paths configuration
LOG_FILE = 'logs/pump/pump_usage_log.csv'
HISTORICAL_DATA_FILE = 'data/raw/synthetic_water_data.csv'
SIMULATION_OUTPUT_FILE = 'data/processed/simulation_results.csv'

# Model paths
START_HOUR_MODEL_PATH = 'models/trained/start_hour_model.pkl'
DURATION_MODEL_PATH = 'models/trained/duration_model.pkl'

# System configuration
CYCLE_CHECK_INTERVAL = 60  # seconds
PUMP_ACTIVATION_TOLERANCE = 0.08  # hours (~5 minutes)
MAX_DEMO_RUNTIME = 300  # seconds (5 minutes max for demo)

# Simulation configuration
DEFAULT_SIMULATION_SPEED = 60  # 1 minute = 1 hour
DEFAULT_SIMULATION_DAYS = 7

# Sensor configuration
SENSOR_UPDATE_INTERVAL = 1  # seconds
SENSOR_ERROR_THRESHOLD = 0.1

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '[%(levelname)s] %(message)s'

# Dashboard configuration
DASHBOARD_WIDTH = 70
SECTION_WIDTH = 70
SUBSECTION_WIDTH = 40

# Data validation
MIN_WATER_LEVEL = 0
MAX_WATER_LEVEL = 100
MIN_TEMPERATURE = -10
MAX_TEMPERATURE = 50
MIN_VOLTAGE = 200
MAX_VOLTAGE = 250
MIN_CURRENT = 0
MAX_CURRENT = 10

# Historical data configuration
HISTORICAL_LOOKBACK_DAYS = 730  # 2 years
PATTERN_ANALYSIS_MIN_SAMPLES = 10

# Prediction configuration
FALLBACK_START_HOUR = 7.0  # 7 AM
FALLBACK_DURATION = 90  # 90 minutes
WEEKEND_HOUR_ADJUSTMENT = 0.5
WEEKEND_DURATION_ADJUSTMENT = 10

def get_project_root():
    """Get the project root directory"""
    # Go up from config/ to project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_absolute_path(relative_path):
    """Convert relative path to absolute path based on project root"""
    return os.path.join(get_project_root(), relative_path)

# Update paths to be absolute
LOG_FILE = get_absolute_path(LOG_FILE)
HISTORICAL_DATA_FILE = get_absolute_path(HISTORICAL_DATA_FILE)
SIMULATION_OUTPUT_FILE = get_absolute_path(SIMULATION_OUTPUT_FILE)
START_HOUR_MODEL_PATH = get_absolute_path(START_HOUR_MODEL_PATH)
DURATION_MODEL_PATH = get_absolute_path(DURATION_MODEL_PATH)
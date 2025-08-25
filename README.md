# Wilo Water Pump Automation System

A professional water pump automation system with predictive control, historical pattern analysis, and intelligent scheduling capabilities.

## 🏗️ Project Structure

```
Wilo Water Pump Automation/
├── config/                     # Configuration files
│   └── settings.py             # Main configuration settings
├── data/                       # Data storage
│   ├── raw/                    # Raw data files (CSV, logs)
│   └── processed/              # Processed data outputs
├── docs/                       # Documentation
│   ├── api/                    # API documentation
│   └── user/                   # User guides
├── logs/                       # Application logs
│   ├── pump/                   # Pump operation logs
│   └── simulation/             # Simulation logs
├── models/                     # Machine learning models
│   └── trained/                # Trained model files (.pkl)
├── scripts/                    # Utility scripts
│   ├── deploy/                 # Deployment scripts
│   └── maintenance/            # Maintenance utilities
├── src/                        # Source code
│   ├── core/                   # Core application logic
│   │   └── main.py             # Main application file
│   ├── dashboard/              # Terminal UI components
│   │   └── terminal_ui.py      # Professional dashboard styling
│   ├── models/                 # ML model handlers
│   │   └── prediction.py       # Prediction algorithms
│   ├── simulation/             # Simulation modules
│   │   ├── run_simulation.py   # Basic simulation
│   │   └── simulation_30days.py # Extended simulation
│   └── utils/                  # Utility modules
│       ├── data_handler.py     # Data processing utilities
│       └── sensors.py          # Sensor data handling
├── tests/                      # Test files
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── .gitignore                  # Git ignore rules
├── requirements.txt            # Python dependencies
└── run.py                      # Main entry point
```

## 🚀 Features

### Core Functionality

- **Predictive Pump Control**: AI-powered prediction of optimal pump operation times
- **Historical Pattern Analysis**: 2-year historical data analysis for pattern recognition
- **Intelligent Scheduling**: Smart scheduling based on usage patterns and environmental factors
- **Professional Dashboard**: Beautiful terminal-based monitoring interface

### Advanced Capabilities

- **Fallback Mechanisms**: Robust fallback systems for sensor failures
- **Environmental Adaptation**: Adaptive algorithms based on temperature, humidity, and seasonal patterns
- **Real-time Monitoring**: Continuous sensor data monitoring and analysis
- **Comprehensive Logging**: Detailed operation logging for trend analysis

### Simulation Features

- **Fast-Forward Simulation**: 30-day simulation with 60x speed
- **Basic Simulation**: Real-time simulation for testing
- **Pattern Validation**: Historical pattern validation through simulation

## 📋 Requirements

### System Requirements

- Python 3.8 or higher
- Windows/Linux/macOS
- Minimum 4GB RAM
- 1GB free disk space

### Python Dependencies

```
joblib>=1.3.0
numpy>=1.21.0
pandas>=1.3.0
scikit-learn>=1.0.0
```

## 🔧 Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd "Wilo Water Pump Automation"
   ```

2. **Create virtual environment**

   ```bash
   python -m venv env
   source env/bin/activate  # Linux/macOS
   # or
   env\Scripts\activate  # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**

   ```bash
   python run.py --help
   ```

## 🏃 Quick Start

### Basic Usage

```bash
# Run the main application
python run.py

# Run simulation
python src/simulation/run_simulation.py

# Run 30-day simulation
python src/simulation/simulation_30days.py

# Run tests
python tests/unit/test_analysis.py
```

### Configuration

Edit `config/settings.py` to customize:

- File paths
- System parameters
- Simulation settings
- Dashboard preferences

## 📊 Data Structure

### Historical Data Format

- **Date**: YYYY-MM-DD format
- **Hour**: Hour of operation (0-23)
- **Duration**: Operation duration in minutes
- **TopTankLevel**: Water level percentage (0-100)
- **Voltage**: System voltage (V)
- **Current**: System current (A)
- **Temperature**: Ambient temperature (°C)
- **Humidity**: Relative humidity (%)

### Log Data Format

- **date**: Operation date
- **start_hour**: Predicted start hour
- **duration**: Predicted duration
- **sensor_data**: Real-time sensor readings

## 🎛️ Dashboard Interface

The professional terminal dashboard provides:

### Visual Elements

- **Color-coded status indicators**
- **Real-time sensor data display**
- **Historical analysis summaries**
- **Prediction results**
- **System alerts and notifications**

### Information Panels

- **System Header**: Application title and version
- **Configuration Panel**: Current settings and file paths
- **Historical Analysis**: 2-year pattern analysis
- **Real-time Monitoring**: Live sensor data and predictions
- **Status Updates**: Operation logs and alerts

## 🔮 Prediction Algorithms

### Machine Learning Models

- **Start Hour Prediction**: Predicts optimal pump start time
- **Duration Prediction**: Predicts optimal operation duration
- **Pattern Recognition**: Identifies historical usage patterns

### Fallback Systems

1. **Historical Pattern Matching**: Uses similar historical conditions
2. **Statistical Averages**: Falls back to statistical patterns
3. **Default Parameters**: Final fallback with safe defaults

## 🧪 Testing

### Unit Tests

```bash
# Run all unit tests
python -m pytest tests/unit/

# Run specific test
python tests/unit/test_analysis.py
```

### Integration Tests

```bash
# Run integration tests
python -m pytest tests/integration/
```

## 📈 Monitoring & Logging

### Log Files

- **Pump Operations**: `logs/pump/pump_usage_log.csv`
- **System Events**: Console output with timestamps
- **Simulation Results**: `data/processed/simulation_results.csv`

### Dashboard Tags

- `[INFO]`: General information
- `[SUCCESS]`: Successful operations
- `[WARNING]`: Warning messages
- `[ERROR]`: Error conditions
- `[CONFIG]`: Configuration information
- `[CONTROL]`: Pump control operations
- `[SENSORS]`: Sensor data
- `[PREDICT]`: Prediction results

## 🔧 Customization

### Adding New Sensors

1. Modify `src/utils/sensors.py`
2. Update data structure in `src/utils/data_handler.py`
3. Adjust prediction models if needed

### Custom Prediction Algorithms

1. Create new module in `src/models/`
2. Implement prediction interface
3. Update main application to use new algorithm

### Dashboard Customization

1. Modify `src/dashboard/terminal_ui.py`
2. Adjust colors, layouts, and formatting
3. Add new display components

## 🚨 Troubleshooting

### Common Issues

**Model Loading Errors**

- Ensure model files exist in `models/trained/`
- Check file permissions
- Verify Python dependencies

**Data Loading Issues**

- Verify CSV file format
- Check file paths in configuration
- Ensure sufficient disk space

**Permission Errors**

- Run with appropriate permissions
- Check directory write access
- Verify log directory exists

### Debug Mode

Set `LOG_LEVEL = 'DEBUG'` in `config/settings.py` for detailed logging.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For support and questions:

- Create an issue in the repository
- Check the documentation in `docs/`
- Review the troubleshooting section

## 🔄 Version History

### v1.0.0

- Initial release
- Core pump automation functionality
- Professional terminal dashboard
- Historical pattern analysis
- Simulation capabilities
- Comprehensive documentation

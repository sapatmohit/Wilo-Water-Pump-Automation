# Project Structure Documentation

## Directory Organization

The Wilo Water Pump Automation System follows a professional, modular architecture:

### 📁 Root Level

```
Wilo Water Pump Automation/
├── run.py                      # Main entry point
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── .git/                       # Git repository
```

### 📁 Configuration (`config/`)

```
config/
├── settings.py                 # Main configuration file
└── models/                     # Model-specific configurations
```

**Purpose**: Centralized configuration management

- System parameters
- File paths
- Dashboard settings
- Prediction algorithms

### 📁 Source Code (`src/`)

```
src/
├── __init__.py                 # Package initialization
├── core/                       # Core application logic
│   ├── __init__.py
│   └── main.py                 # Main application
├── dashboard/                  # User interface components
│   ├── __init__.py
│   └── terminal_ui.py          # Professional terminal UI
├── models/                     # Machine learning components
│   ├── __init__.py
│   └── prediction.py           # Prediction algorithms
├── simulation/                 # Simulation modules
│   ├── __init__.py
│   ├── run_simulation.py       # Basic simulation
│   └── simulation_30days.py    # Extended simulation
└── utils/                      # Utility modules
    ├── __init__.py
    ├── data_handler.py         # Data processing
    └── sensors.py              # Sensor management
```

**Purpose**: Modular, maintainable source code

- Separation of concerns
- Reusable components
- Easy testing and debugging

### 📁 Data Storage (`data/`)

```
data/
├── raw/                        # Raw input data
│   ├── synthetic_water_data.csv
│   ├── pump_usage_log.csv
│   └── simulation_30days.csv
└── processed/                  # Processed outputs
    └── simulation_results.csv
```

**Purpose**: Organized data management

- Input data isolation
- Output data tracking
- Data lineage maintenance

### 📁 Models (`models/`)

```
models/
├── trained/                    # Trained ML models
│   ├── start_hour_model.pkl
│   └── duration_model.pkl
└── config/                     # Model configurations
```

**Purpose**: Machine learning assets

- Trained model storage
- Model versioning
- Configuration management

### 📁 Logging (`logs/`)

```
logs/
├── pump/                       # Pump operation logs
│   └── pump_usage_log.csv
└── simulation/                 # Simulation logs
    └── simulation_results.log
```

**Purpose**: Operation monitoring

- Audit trails
- Performance tracking
- Debugging information

### 📁 Testing (`tests/`)

```
tests/
├── unit/                       # Unit tests
│   └── test_analysis.py
└── integration/                # Integration tests
    └── test_full_system.py
```

**Purpose**: Quality assurance

- Code validation
- Regression testing
- System verification

### 📁 Documentation (`docs/`)

```
docs/
├── api/                        # API documentation
│   └── functions.md
├── user/                       # User guides
│   └── user_manual.md
└── PROJECT_STRUCTURE.md       # This file
```

**Purpose**: Knowledge management

- Technical documentation
- User guides
- Architecture documentation

### 📁 Scripts (`scripts/`)

```
scripts/
├── deploy/                     # Deployment scripts
│   ├── install.sh
│   └── setup.bat
└── maintenance/                # Maintenance utilities
    ├── backup.py
    └── cleanup.py
```

**Purpose**: Automation and maintenance

- Deployment automation
- System maintenance
- Utility functions

## Module Dependencies

### Core Dependencies

```
src.core.main → config.settings
             → src.dashboard.terminal_ui
             → src.utils.data_handler
             → src.utils.sensors
             → src.models.prediction
```

### Dashboard Dependencies

```
src.dashboard.terminal_ui → warnings (built-in)
                          → datetime (built-in)
```

### Utility Dependencies

```
src.utils.data_handler → pandas
                       → numpy
                       → csv (built-in)
                       → os (built-in)
                       → config.settings

src.utils.sensors → numpy
                  → random (built-in)
                  → datetime (built-in)
                  → src.utils.data_handler
```

### Model Dependencies

```
src.models.prediction → pandas
                      → numpy
                      → datetime (built-in)
                      → joblib
                      → config.settings
                      → src.utils.data_handler
```

## Design Principles

### 1. Separation of Concerns

- Each module has a single responsibility
- Clear interfaces between components
- Minimal coupling between modules

### 2. Configuration Management

- Centralized configuration in `config/`
- Environment-specific settings
- Easy parameter adjustment

### 3. Data Flow

```
Raw Data → Data Handler → Sensors → Prediction → Dashboard
    ↓           ↓            ↓          ↓          ↓
 Storage    Processing   Real-time   ML Models  Display
```

### 4. Error Handling

- Graceful degradation
- Fallback mechanisms
- Comprehensive logging

### 5. Extensibility

- Plugin architecture for new sensors
- Modular prediction algorithms
- Customizable dashboard components

## File Naming Conventions

### Python Files

- `snake_case` for all Python files
- Descriptive names indicating purpose
- `__init__.py` for package initialization

### Data Files

- `snake_case` with descriptive names
- Version numbers for datasets
- Clear format indicators (`.csv`, `.json`)

### Configuration Files

- Singular names (`settings.py`)
- Clear purpose indication
- Consistent structure

### Documentation Files

- `UPPERCASE` for major documentation
- `Title_Case` for specific guides
- `.md` extension for Markdown files

## Adding New Components

### New Utility Module

1. Create file in `src/utils/`
2. Add `__init__.py` if needed
3. Update imports in dependent modules
4. Add tests in `tests/unit/`

### New Prediction Algorithm

1. Create file in `src/models/`
2. Implement standard interface
3. Update configuration settings
4. Add integration tests

### New Dashboard Component

1. Add functions to `src/dashboard/terminal_ui.py`
2. Follow existing styling patterns
3. Update main application
4. Test visual output

This modular structure ensures maintainability, scalability, and professional development practices.

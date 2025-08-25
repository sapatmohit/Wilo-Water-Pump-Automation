import React, { createContext, useContext, useReducer, useEffect } from 'react';

// Define types for our dashboard data
export interface TankLevel {
  level: number; // 0-100 percentage
  volume: number; // current volume in liters
  capacity: number; // total capacity in liters
}

export interface PumpStatus {
  isRunning: boolean;
  remainingDuration: number; // in minutes
  currentPower: number; // in watts
  totalRuntime: number; // in hours
  lastStartTime: Date;
}

export interface FlowRates {
  inflow: number; // L/min
  outflow: number; // L/min
  netFlow: number; // L/min (inflow - outflow)
}

export interface BatteryStatus {
  isOnBattery: boolean;
  chargeLevel: number; // 0-100 percentage
  estimatedRuntime: number; // in minutes
}

export interface AIPredictions {
  nextFillTime: Date;
  estimatedDuration: number; // in minutes
  confidence: number; // 0-100 percentage
  canOverride: boolean;
}

export interface Alert {
  id: string;
  type: 'emergency' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  isAcknowledged: boolean;
  priority: 'high' | 'medium' | 'low';
}

export interface Fault {
  id: string;
  type: 'sensor_failure' | 'valve_stuck' | 'dry_run' | 'overflow_risk';
  description: string;
  severity: 'critical' | 'major' | 'minor';
  timestamp: Date;
  isResolved: boolean;
}

export interface UsageData {
  date: Date;
  usage: number; // in liters
  predicted: number; // in liters
  events?: string[]; // special events like "Holiday", "High Usage"
}

export interface EnvironmentalData {
  temperature: number; // in Celsius
  humidity: number; // percentage
  timestamp: Date;
}

export interface WaterDashboardState {
  tankLevels: {
    topTank: TankLevel;
    bottomTank: TankLevel;
  };
  pumpStatus: PumpStatus;
  flowRates: FlowRates;
  batteryStatus: BatteryStatus;
  aiPredictions: AIPredictions;
  alerts: Alert[];
  faults: Fault[];
  usageData: UsageData[];
  environmentalData: EnvironmentalData[];
  isSimulationRunning: boolean;
  simulationSpeed: number; // 1 = normal, 2 = 2x speed, etc.
  currentScenario: 'normal' | 'leakage' | 'power_failure' | 'sensor_failure';
}

// Define action types
type ActionType =
  | { type: 'UPDATE_TANK_LEVELS'; payload: { topTank?: Partial<TankLevel>; bottomTank?: Partial<TankLevel> } }
  | { type: 'UPDATE_PUMP_STATUS'; payload: Partial<PumpStatus> }
  | { type: 'UPDATE_FLOW_RATES'; payload: Partial<FlowRates> }
  | { type: 'UPDATE_BATTERY_STATUS'; payload: Partial<BatteryStatus> }
  | { type: 'UPDATE_AI_PREDICTIONS'; payload: Partial<AIPredictions> }
  | { type: 'ADD_ALERT'; payload: Alert }
  | { type: 'ACKNOWLEDGE_ALERT'; payload: string }
  | { type: 'DISMISS_ALERT'; payload: string }
  | { type: 'ADD_FAULT'; payload: Fault }
  | { type: 'RESOLVE_FAULT'; payload: string }
  | { type: 'UPDATE_USAGE_DATA'; payload: UsageData[] }
  | { type: 'UPDATE_ENVIRONMENTAL_DATA'; payload: EnvironmentalData[] }
  | { type: 'START_SIMULATION' }
  | { type: 'PAUSE_SIMULATION' }
  | { type: 'SET_SIMULATION_SPEED'; payload: number }
  | { type: 'SET_SCENARIO'; payload: 'normal' | 'leakage' | 'power_failure' | 'sensor_failure' };

// Initial state
const initialState: WaterDashboardState = {
  tankLevels: {
    topTank: {
      level: 75,
      volume: 750,
      capacity: 1000
    },
    bottomTank: {
      level: 30,
      volume: 300,
      capacity: 1000
    }
  },
  pumpStatus: {
    isRunning: false,
    remainingDuration: 0,
    currentPower: 0,
    totalRuntime: 120.5,
    lastStartTime: new Date()
  },
  flowRates: {
    inflow: 0,
    outflow: 2.5,
    netFlow: -2.5
  },
  batteryStatus: {
    isOnBattery: false,
    chargeLevel: 100,
    estimatedRuntime: 120
  },
  aiPredictions: {
    nextFillTime: new Date(Date.now() + 3600000), // 1 hour from now
    estimatedDuration: 45,
    confidence: 94,
    canOverride: true
  },
  alerts: [],
  faults: [],
  usageData: [],
  environmentalData: [],
  isSimulationRunning: true,
  simulationSpeed: 1,
  currentScenario: 'normal'
};

// Create context
interface WaterDashboardContextType {
  state: WaterDashboardState;
  dispatch: React.Dispatch<ActionType>;
}

const WaterDashboardContext = createContext<WaterDashboardContextType | undefined>(undefined);

// Reducer function
function waterDashboardReducer(state: WaterDashboardState, action: ActionType): WaterDashboardState {
  switch (action.type) {
    case 'UPDATE_TANK_LEVELS':
      return {
        ...state,
        tankLevels: {
          topTank: {
            ...state.tankLevels.topTank,
            ...action.payload.topTank
          },
          bottomTank: {
            ...state.tankLevels.bottomTank,
            ...action.payload.bottomTank
          }
        }
      };
    case 'UPDATE_PUMP_STATUS':
      return {
        ...state,
        pumpStatus: {
          ...state.pumpStatus,
          ...action.payload
        }
      };
    case 'UPDATE_FLOW_RATES':
      return {
        ...state,
        flowRates: {
          ...state.flowRates,
          ...action.payload
        }
      };
    case 'UPDATE_BATTERY_STATUS':
      return {
        ...state,
        batteryStatus: {
          ...state.batteryStatus,
          ...action.payload
        }
      };
    case 'UPDATE_AI_PREDICTIONS':
      return {
        ...state,
        aiPredictions: {
          ...state.aiPredictions,
          ...action.payload
        }
      };
    case 'ADD_ALERT':
      return {
        ...state,
        alerts: [action.payload, ...state.alerts]
      };
    case 'ACKNOWLEDGE_ALERT':
      return {
        ...state,
        alerts: state.alerts.map(alert =>
          alert.id === action.payload ? { ...alert, isAcknowledged: true } : alert
        )
      };
    case 'DISMISS_ALERT':
      return {
        ...state,
        alerts: state.alerts.filter(alert => alert.id !== action.payload)
      };
    case 'ADD_FAULT':
      return {
        ...state,
        faults: [action.payload, ...state.faults]
      };
    case 'RESOLVE_FAULT':
      return {
        ...state,
        faults: state.faults.map(fault =>
          fault.id === action.payload ? { ...fault, isResolved: true } : fault
        )
      };
    case 'UPDATE_USAGE_DATA':
      return {
        ...state,
        usageData: action.payload
      };
    case 'UPDATE_ENVIRONMENTAL_DATA':
      return {
        ...state,
        environmentalData: action.payload
      };
    case 'START_SIMULATION':
      return {
        ...state,
        isSimulationRunning: true
      };
    case 'PAUSE_SIMULATION':
      return {
        ...state,
        isSimulationRunning: false
      };
    case 'SET_SIMULATION_SPEED':
      return {
        ...state,
        simulationSpeed: action.payload
      };
    case 'SET_SCENARIO':
      return {
        ...state,
        currentScenario: action.payload
      };
    default:
      return state;
  }
}

// Provider component
export const WaterDashboardProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(waterDashboardReducer, initialState);

  return (
    <WaterDashboardContext.Provider value={{ state, dispatch }}>
      {children}
    </WaterDashboardContext.Provider>
  );
};

// Custom hook to use the context
export const useWaterDashboard = () => {
  const context = useContext(WaterDashboardContext);
  if (context === undefined) {
    throw new Error('useWaterDashboard must be used within a WaterDashboardProvider');
  }
  return context;
};
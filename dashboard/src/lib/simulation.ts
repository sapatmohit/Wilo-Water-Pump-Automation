import { 
  TankLevel, 
  PumpStatus, 
  FlowRates, 
  BatteryStatus, 
  AIPredictions, 
  Alert, 
  Fault, 
  UsageData, 
  EnvironmentalData 
} from '@/contexts/WaterDashboardContext';

// Helper function to generate random number within a range
export const randomInRange = (min: number, max: number): number => {
  return Math.random() * (max - min) + min;
};

// Helper function to generate random integer within a range
export const randomIntInRange = (min: number, max: number): number => {
  return Math.floor(randomInRange(min, max));
};

// Helper function to add random fluctuation to a value
export const addFluctuation = (value: number, percentage: number): number => {
  const fluctuation = value * (randomInRange(-percentage, percentage) / 100);
  return value + fluctuation;
};

// Generate tank level data
export const generateTankLevel = (
  baseLevel: number,
  capacity: number,
  isPumpRunning: boolean,
  isTopTank: boolean
): TankLevel => {
  // If pump is running, top tank fills up, bottom tank drains
  // If pump is not running, top tank drains, bottom tank may fill up from external source
  let levelChange = 0;
  
  if (isPumpRunning) {
    levelChange = isTopTank ? randomInRange(0.2, 0.5) : randomInRange(-0.5, -0.2);
  } else {
    levelChange = isTopTank ? randomInRange(-0.3, -0.1) : randomInRange(0.1, 0.3);
  }
  
  // Calculate new level with constraints
  let newLevel = Math.max(0, Math.min(100, baseLevel + levelChange));
  
  // Calculate volume based on level percentage
  const volume = (newLevel / 100) * capacity;
  
  return {
    level: newLevel,
    volume: Math.round(volume),
    capacity
  };
};

// Generate pump status data
export const generatePumpStatus = (
  currentStatus: PumpStatus,
  shouldRun: boolean,
  remainingDuration: number
): PumpStatus => {
  // If pump should run but isn't running, start it
  if (shouldRun && !currentStatus.isRunning) {
    return {
      isRunning: true,
      remainingDuration,
      currentPower: randomInRange(1800, 2200),
      totalRuntime: currentStatus.totalRuntime,
      lastStartTime: new Date()
    };
  }
  
  // If pump is running, update remaining duration and maybe stop it
  if (currentStatus.isRunning) {
    const newRemainingDuration = Math.max(0, currentStatus.remainingDuration - 1);
    
    if (newRemainingDuration <= 0 || !shouldRun) {
      return {
        isRunning: false,
        remainingDuration: 0,
        currentPower: 0,
        totalRuntime: currentStatus.totalRuntime + (currentStatus.remainingDuration / 60),
        lastStartTime: currentStatus.lastStartTime
      };
    }
    
    return {
      ...currentStatus,
      remainingDuration: newRemainingDuration,
      currentPower: addFluctuation(currentStatus.currentPower, 5)
    };
  }
  
  // Pump is not running and should not run
  return currentStatus;
};

// Generate flow rate data
export const generateFlowRates = (isPumpRunning: boolean): FlowRates => {
  let inflow = 0;
  let outflow = randomInRange(1.8, 3.2); // Constant outflow from top tank
  
  if (isPumpRunning) {
    inflow = randomInRange(12, 15); // Pump running creates inflow to top tank
  }
  
  return {
    inflow,
    outflow,
    netFlow: inflow - outflow
  };
};

// Generate battery status data
export const generateBatteryStatus = (
  current: BatteryStatus,
  isOnBattery: boolean
): BatteryStatus => {
  if (isOnBattery) {
    // Discharge battery
    const newChargeLevel = Math.max(0, current.chargeLevel - randomInRange(0.1, 0.3));
    const newEstimatedRuntime = Math.max(0, (newChargeLevel / 100) * 120);
    
    return {
      isOnBattery: true,
      chargeLevel: newChargeLevel,
      estimatedRuntime: Math.round(newEstimatedRuntime)
    };
  } else if (current.chargeLevel < 100) {
    // Charge battery
    const newChargeLevel = Math.min(100, current.chargeLevel + randomInRange(0.05, 0.2));
    const newEstimatedRuntime = (newChargeLevel / 100) * 120;
    
    return {
      isOnBattery: false,
      chargeLevel: newChargeLevel,
      estimatedRuntime: Math.round(newEstimatedRuntime)
    };
  }
  
  // Battery fully charged and not in use
  return current;
};

// Generate AI predictions
export const generateAIPredictions = (
  topTankLevel: number,
  usagePattern: UsageData[],
  confidence: number = 94
): AIPredictions => {
  // Calculate next fill time based on current level and usage pattern
  const hoursUntilFill = (topTankLevel > 70) 
    ? randomInRange(8, 12) 
    : (topTankLevel > 40)
      ? randomInRange(4, 8)
      : randomInRange(0.5, 4);
  
  const nextFillTime = new Date(Date.now() + hoursUntilFill * 3600000);
  
  // Estimate duration based on tank level
  const estimatedDuration = Math.round(
    (100 - topTankLevel) * 0.6 + randomInRange(-5, 5)
  );
  
  return {
    nextFillTime,
    estimatedDuration: Math.max(10, estimatedDuration),
    confidence,
    canOverride: confidence < 90
  };
};

// Generate alerts
export const generateRandomAlert = (): Alert => {
  const types: Array<'emergency' | 'warning' | 'info'> = ['emergency', 'warning', 'info'];
  const priorities: Array<'high' | 'medium' | 'low'> = ['high', 'medium', 'low'];
  
  const alertTemplates = [
    {
      type: 'info',
      title: 'System Update',
      message: 'System firmware updated to version 2.3.4',
      priority: 'low'
    },
    {
      type: 'warning',
      title: 'High Water Usage',
      message: 'Water usage is 30% higher than average for this time period',
      priority: 'medium'
    },
    {
      type: 'warning',
      title: 'Low Tank Level',
      message: 'Top tank level below 25%. Scheduling emergency fill cycle',
      priority: 'medium'
    },
    {
      type: 'emergency',
      title: 'Possible Leak Detected',
      message: 'Unusual flow pattern detected. Please check system for leaks',
      priority: 'high'
    },
    {
      type: 'emergency',
      title: 'Pump Overheating',
      message: 'Pump temperature exceeding normal operating range',
      priority: 'high'
    },
    {
      type: 'info',
      title: 'Maintenance Due',
      message: 'Scheduled maintenance due in 5 days',
      priority: 'low'
    },
    {
      type: 'warning',
      title: 'Battery Low',
      message: 'UPS battery below 20%. Connect to power source',
      priority: 'medium'
    }
  ];
  
  const template = alertTemplates[randomIntInRange(0, alertTemplates.length)];
  
  return {
    id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    type: template.type as 'emergency' | 'warning' | 'info',
    title: template.title,
    message: template.message,
    timestamp: new Date(),
    isAcknowledged: false,
    priority: template.priority as 'high' | 'medium' | 'low'
  };
};

// Generate faults
export const generateRandomFault = (): Fault => {
  const faultTemplates = [
    {
      type: 'sensor_failure',
      description: 'Top tank level sensor failure',
      severity: 'major'
    },
    {
      type: 'sensor_failure',
      description: 'Bottom tank level sensor failure',
      severity: 'major'
    },
    {
      type: 'sensor_failure',
      description: 'Flow meter calibration error',
      severity: 'minor'
    },
    {
      type: 'valve_stuck',
      description: 'Inlet valve stuck in open position',
      severity: 'critical'
    },
    {
      type: 'valve_stuck',
      description: 'Outlet valve stuck in closed position',
      severity: 'major'
    },
    {
      type: 'dry_run',
      description: 'Pump running with insufficient water in bottom tank',
      severity: 'critical'
    },
    {
      type: 'overflow_risk',
      description: 'Top tank approaching overflow threshold',
      severity: 'critical'
    }
  ];
  
  const template = faultTemplates[randomIntInRange(0, faultTemplates.length)];
  
  return {
    id: `fault-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    type: template.type as 'sensor_failure' | 'valve_stuck' | 'dry_run' | 'overflow_risk',
    description: template.description,
    severity: template.severity as 'critical' | 'major' | 'minor',
    timestamp: new Date(),
    isResolved: false
  };
};

// Generate usage data for a week
export const generateWeeklyUsageData = (): UsageData[] => {
  const data: UsageData[] = [];
  const now = new Date();
  const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
  
  // Special events
  const events = [
    { date: new Date(startDate.getTime() + 2 * 86400000), event: 'Holiday' },
    { date: new Date(startDate.getTime() + 5 * 86400000), event: 'High Usage' }
  ];
  
  for (let i = 0; i < 7; i++) {
    const currentDate = new Date(startDate.getTime() + i * 86400000);
    const isWeekend = currentDate.getDay() === 0 || currentDate.getDay() === 6;
    
    // Base usage is higher on weekends
    let baseUsage = isWeekend ? randomInRange(800, 1200) : randomInRange(500, 900);
    
    // Check if there's a special event on this day
    const dayEvents = events
      .filter(e => e.date.toDateString() === currentDate.toDateString())
      .map(e => e.event);
    
    // Adjust usage based on events
    if (dayEvents.includes('Holiday')) {
      baseUsage *= 1.5;
    } else if (dayEvents.includes('High Usage')) {
      baseUsage *= 1.3;
    }
    
    // Add some prediction error
    const predicted = baseUsage * randomInRange(0.9, 1.1);
    
    data.push({
      date: currentDate,
      usage: Math.round(baseUsage),
      predicted: Math.round(predicted),
      events: dayEvents.length > 0 ? dayEvents : undefined
    });
  }
  
  return data;
};

// Generate environmental data
export const generateEnvironmentalData = (hours: number = 24): EnvironmentalData[] => {
  const data: EnvironmentalData[] = [];
  const now = new Date();
  const startTime = new Date(now.getTime() - hours * 3600000);
  
  for (let i = 0; i <= hours; i++) {
    const time = new Date(startTime.getTime() + i * 3600000);
    const hourOfDay = time.getHours();
    
    // Temperature varies throughout the day
    let baseTemp = 22; // Base temperature in Celsius
    
    if (hourOfDay >= 6 && hourOfDay < 12) {
      // Morning: rising temperature
      baseTemp += (hourOfDay - 6) * 0.5;
    } else if (hourOfDay >= 12 && hourOfDay < 18) {
      // Afternoon: peak temperature
      baseTemp += 3 + (hourOfDay - 12) * 0.2;
    } else if (hourOfDay >= 18) {
      // Evening: falling temperature
      baseTemp += 4 - (hourOfDay - 18) * 0.5;
    }
    
    // Add some random variation
    const temperature = baseTemp + randomInRange(-1, 1);
    
    // Humidity is somewhat inversely related to temperature
    const humidity = 60 - (temperature - 22) * 2 + randomInRange(-5, 5);
    
    data.push({
      temperature,
      humidity: Math.max(30, Math.min(90, humidity)),
      timestamp: time
    });
  }
  
  return data;
};

// Scenario generators
export const generateNormalScenario = (currentState: any) => {
  return {
    ...currentState,
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
    }
  };
};

export const generateLeakageScenario = (currentState: any) => {
  return {
    ...currentState,
    tankLevels: {
      topTank: {
        level: 45,
        volume: 450,
        capacity: 1000
      },
      bottomTank: {
        level: 20,
        volume: 200,
        capacity: 1000
      }
    },
    flowRates: {
      inflow: 0,
      outflow: 8.5, // Higher outflow due to leak
      netFlow: -8.5
    },
    aiPredictions: {
      nextFillTime: new Date(Date.now() + 1800000), // 30 minutes from now (more urgent)
      estimatedDuration: 60, // Longer duration needed
      confidence: 78, // Lower confidence due to unusual pattern
      canOverride: true
    },
    alerts: [
      {
        id: `alert-leak-${Date.now()}`,
        type: 'emergency',
        title: 'Possible Leak Detected',
        message: 'Unusual flow pattern detected. Water loss rate is 240% above normal.',
        timestamp: new Date(),
        isAcknowledged: false,
        priority: 'high'
      }
    ],
    faults: [
      {
        id: `fault-leak-${Date.now()}`,
        type: 'overflow_risk',
        description: 'Abnormal water loss detected in main distribution line',
        severity: 'critical',
        timestamp: new Date(),
        isResolved: false
      }
    ]
  };
};

export const generatePowerFailureScenario = (currentState: any) => {
  return {
    ...currentState,
    tankLevels: {
      topTank: {
        level: 60,
        volume: 600,
        capacity: 1000
      },
      bottomTank: {
        level: 25,
        volume: 250,
        capacity: 1000
      }
    },
    pumpStatus: {
      isRunning: false,
      remainingDuration: 0,
      currentPower: 0,
      totalRuntime: currentState.pumpStatus.totalRuntime,
      lastStartTime: currentState.pumpStatus.lastStartTime
    },
    batteryStatus: {
      isOnBattery: true,
      chargeLevel: 68,
      estimatedRuntime: 82
    },
    aiPredictions: {
      nextFillTime: new Date(Date.now() + 7200000), // 2 hours from now (delayed due to power)
      estimatedDuration: 50,
      confidence: 82, // Lower confidence due to power situation
      canOverride: true
    },
    alerts: [
      {
        id: `alert-power-${Date.now()}`,
        type: 'warning',
        title: 'Running on Battery Power',
        message: 'Main power supply interrupted. System running on UPS battery.',
        timestamp: new Date(),
        isAcknowledged: false,
        priority: 'medium'
      }
    ]
  };
};

export const generateSensorFailureScenario = (currentState: any) => {
  return {
    ...currentState,
    tankLevels: {
      topTank: {
        level: 65,
        volume: 650,
        capacity: 1000
      },
      bottomTank: {
        level: 35,
        volume: 350,
        capacity: 1000
      }
    },
    aiPredictions: {
      nextFillTime: new Date(Date.now() + 3600000), // 1 hour from now
      estimatedDuration: 40,
      confidence: 62, // Much lower confidence due to sensor issues
      canOverride: true
    },
    alerts: [
      {
        id: `alert-sensor-${Date.now()}`,
        type: 'warning',
        title: 'Sensor Failure Detected',
        message: 'Top tank level sensor providing inconsistent readings. Using backup estimation.',
        timestamp: new Date(),
        isAcknowledged: false,
        priority: 'medium'
      }
    ],
    faults: [
      {
        id: `fault-sensor-${Date.now()}`,
        type: 'sensor_failure',
        description: 'Top tank level sensor failure',
        severity: 'major',
        timestamp: new Date(),
        isResolved: false
      }
    ]
  };
};
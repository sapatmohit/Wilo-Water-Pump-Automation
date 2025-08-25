import { useEffect, useRef } from 'react';
import { useWaterDashboard } from '@/contexts/WaterDashboardContext';
import {
  generateTankLevel,
  generatePumpStatus,
  generateFlowRates,
  generateBatteryStatus,
  generateAIPredictions,
  generateRandomAlert,
  generateRandomFault,
  generateWeeklyUsageData,
  generateEnvironmentalData
} from '@/lib/simulation';

export const useSimulation = () => {
  const { state, dispatch } = useWaterDashboard();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const alertIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Main simulation loop
  useEffect(() => {
    if (!state.isSimulationRunning) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    const updateInterval = 5000 / state.simulationSpeed; // Base 5 seconds, adjusted by speed

    intervalRef.current = setInterval(() => {
      // Update tank levels
      const newTopTank = generateTankLevel(
        state.tankLevels.topTank.level,
        state.tankLevels.topTank.capacity,
        state.pumpStatus.isRunning,
        true
      );
      
      const newBottomTank = generateTankLevel(
        state.tankLevels.bottomTank.level,
        state.tankLevels.bottomTank.capacity,
        state.pumpStatus.isRunning,
        false
      );

      dispatch({
        type: 'UPDATE_TANK_LEVELS',
        payload: {
          topTank: newTopTank,
          bottomTank: newBottomTank
        }
      });

      // Determine if pump should run based on tank levels
      const shouldPumpRun = newTopTank.level < 30 || (state.pumpStatus.isRunning && newTopTank.level < 90);
      const remainingDuration = shouldPumpRun ? 45 : 0;

      // Update pump status
      const newPumpStatus = generatePumpStatus(
        state.pumpStatus,
        shouldPumpRun,
        remainingDuration
      );

      dispatch({
        type: 'UPDATE_PUMP_STATUS',
        payload: newPumpStatus
      });

      // Update flow rates
      const newFlowRates = generateFlowRates(newPumpStatus.isRunning);
      dispatch({
        type: 'UPDATE_FLOW_RATES',
        payload: newFlowRates
      });

      // Update battery status (simulate power outage occasionally)
      const isOnBattery = state.currentScenario === 'power_failure' || Math.random() < 0.01;
      const newBatteryStatus = generateBatteryStatus(state.batteryStatus, isOnBattery);
      dispatch({
        type: 'UPDATE_BATTERY_STATUS',
        payload: newBatteryStatus
      });

      // Update AI predictions
      const newAIPredictions = generateAIPredictions(
        newTopTank.level,
        state.usageData,
        state.currentScenario === 'sensor_failure' ? 62 : 94
      );
      dispatch({
        type: 'UPDATE_AI_PREDICTIONS',
        payload: newAIPredictions
      });

    }, updateInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [state.isSimulationRunning, state.simulationSpeed, state.tankLevels, state.pumpStatus, state.batteryStatus, state.usageData, state.currentScenario, dispatch]);

  // Generate periodic alerts and faults
  useEffect(() => {
    if (!state.isSimulationRunning) {
      if (alertIntervalRef.current) {
        clearInterval(alertIntervalRef.current);
        alertIntervalRef.current = null;
      }
      return;
    }

    alertIntervalRef.current = setInterval(() => {
      // Generate random alerts (less frequent)
      if (Math.random() < 0.1) { // 10% chance every interval
        const alert = generateRandomAlert();
        dispatch({ type: 'ADD_ALERT', payload: alert });
      }

      // Generate random faults (even less frequent)
      if (Math.random() < 0.05) { // 5% chance every interval
        const fault = generateRandomFault();
        dispatch({ type: 'ADD_FAULT', payload: fault });
      }
    }, 30000); // Check every 30 seconds

    return () => {
      if (alertIntervalRef.current) {
        clearInterval(alertIntervalRef.current);
      }
    };
  }, [state.isSimulationRunning, dispatch]);

  // Initialize usage and environmental data
  useEffect(() => {
    if (state.usageData.length === 0) {
      const weeklyData = generateWeeklyUsageData();
      dispatch({ type: 'UPDATE_USAGE_DATA', payload: weeklyData });
    }

    if (state.environmentalData.length === 0) {
      const envData = generateEnvironmentalData(24);
      dispatch({ type: 'UPDATE_ENVIRONMENTAL_DATA', payload: envData });
    }
  }, [state.usageData.length, state.environmentalData.length, dispatch]);

  // Control functions
  const startSimulation = () => {
    dispatch({ type: 'START_SIMULATION' });
  };

  const pauseSimulation = () => {
    dispatch({ type: 'PAUSE_SIMULATION' });
  };

  const setSimulationSpeed = (speed: number) => {
    dispatch({ type: 'SET_SIMULATION_SPEED', payload: speed });
  };

  const setScenario = (scenario: 'normal' | 'leakage' | 'power_failure' | 'sensor_failure') => {
    dispatch({ type: 'SET_SCENARIO', payload: scenario });
  };

  return {
    isRunning: state.isSimulationRunning,
    speed: state.simulationSpeed,
    scenario: state.currentScenario,
    startSimulation,
    pauseSimulation,
    setSimulationSpeed,
    setScenario
  };
};
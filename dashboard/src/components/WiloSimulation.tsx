import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Progress } from "@/components/ui/progress";
import { SystemDashboard } from "./SystemDashboard";
import { TimelineSimulation } from "./TimelineSimulation";
import { Card } from "@/components/ui/card";
import { RotateCcw, FastForward, SkipBack, Activity, Zap, AlertTriangle, Settings } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";

export function WiloSimulation() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [currentDay, setCurrentDay] = useState(1);

  // System status state

  const [systemStatus, setSystemStatus] = useState({
    pumpStatus: "STANDBY",
    aiConfidence: "94%",
    sensorHealth: "7/7 Active",
    uptime: "0.0 days",
    networkStatus: "Connected"
  });

  const [aiPredictions, setAiPredictions] = useState({
    nextStart: "06:00 AM",
    duration: "45 min",
    dataSource: "Real",
    reliability: "High"
  });

  const timelineEvents = [
    {
      id: "day1",
      day: 1,
      title: "Day 1: Sensor Degradation Begins",
      status: "optimal" as const,
      sensorStatus: "6/7 Active",
      startTime: "06:00 AM",
      duration: "45 min",
      aiDecision: "Water level sensor failed. Compensating using usage pattern analysis and temperature correlation. Confidence: 98%"
    },
    {
      id: "day10",
      day: 10,
      title: "Day 10: Multiple Sensor Failures",
      status: "degraded" as const,
      sensorStatus: "4/7 Failed",
      startTime: "05:50 AM",
      duration: "38 min",
      aiDecision: "Hybrid mode activated. Blending synthetic patterns with remaining sensor data. Adjusting for historical peak usage. Confidence: 85%"
    },
    {
      id: "day20",
      day: 20,
      title: "Day 20: Critical Sensor Failure",
      status: "critical" as const,
      sensorStatus: "Only Date/Time",
      startTime: "06:00 AM",
      duration: "35 min",
      aiDecision: "Fallback to hardcoded safe daily cycle. Conservative approach ensuring no overflow. System remains operational. Confidence: 75%"
    },
    {
      id: "day30",
      day: 30,
      title: "Day 30: Maintenance & Recovery",
      status: "restored" as const,
      sensorStatus: "7/7 Active",
      startTime: "05:45 AM",
      duration: "42 min",
      aiDecision: "All sensors restored. AI recalibrating with fresh data. Improved predictions using 30-day learning cycle. Confidence: 96%"
    }
  ];

  const updateDashboard = () => {
    if (currentDay <= 5) {
      setSystemStatus({
        pumpStatus: "RUNNING",
        aiConfidence: "98%",
        sensorHealth: "6/7 Active",
        uptime: `${currentDay - 1}.${Math.floor(Math.random() * 10)} days`,
        networkStatus: "Connected"
      });
      setAiPredictions({
        nextStart: "06:00 AM",
        duration: "45 min",
        dataSource: "Real+Synthetic",
        reliability: "High"
      });
    } else if (currentDay <= 15) {
      setSystemStatus({
        pumpStatus: "RUNNING",
        aiConfidence: "85%",
        sensorHealth: "4/7 Active",
        uptime: `${currentDay - 1}.${Math.floor(Math.random() * 10)} days`,
        networkStatus: "Connected"
      });
      setAiPredictions({
        nextStart: `${5 + Math.floor(Math.random() * 2)}:${30 + Math.floor(Math.random() * 30)} AM`,
        duration: `${35 + Math.floor(Math.random() * 15)} min`,
        dataSource: "Hybrid",
        reliability: "Medium"
      });
    } else if (currentDay <= 25) {
      setSystemStatus({
        pumpStatus: "RUNNING",
        aiConfidence: "75%",
        sensorHealth: "2/7 Active",
        uptime: `${currentDay - 1}.${Math.floor(Math.random() * 10)} days`,
        networkStatus: "Disconnected"
      });
      setAiPredictions({
        nextStart: "06:00 AM",
        duration: "35 min",
        dataSource: "Synthetic",
        reliability: "Conservative"
      });
    } else {
      setSystemStatus({
        pumpStatus: "RUNNING",
        aiConfidence: "96%",
        sensorHealth: "7/7 Active",
        uptime: `${currentDay - 1}.${Math.floor(Math.random() * 10)} days`,
        networkStatus: "Connected"
      });
      setAiPredictions({
        nextStart: "05:45 AM",
        duration: "42 min",
        dataSource: "Real",
        reliability: "High"
      });
    }
  };

  const handleDayChange = (value: number[]) => {
    const newDay = value[0];
    setCurrentDay(newDay);
    toast({
      title: `Day ${newDay}`,
      description: `Switched to day ${newDay}`,
    });
  };

  const resetDemo = () => {
    setCurrentDay(1);
    setSystemStatus({
      pumpStatus: "STANDBY",
      aiConfidence: "94%",
      sensorHealth: "7/7 Active",
      uptime: "0.0 days",
      networkStatus: "Connected"
    });
    setAiPredictions({
      nextStart: "06:00 AM",
      duration: "45 min",
      dataSource: "Real",
      reliability: "High"
    });

    toast({
      title: "Demo Reset",
      description: "System returned to Day 1",
    });
  };

  // Filter events to only show those that have been reached

  // Filter events to only show those that have been reached
  const visibleEvents = timelineEvents.filter(event => {
    if (currentDay >= 30) return true;
    if (currentDay >= 20) return event.day <= 20;
    if (currentDay >= 10) return event.day <= 10;
    return event.day <= 1;
  });

  useEffect(() => {
    updateDashboard();
  }, [currentDay]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto px-4 py-4 max-w-7xl">
        <Card className="p-6 mb-6 bg-gradient-primary text-white border-0 shadow-xl">
          <div className="relative">
            <Button
              onClick={() => navigate('/admin')}
              variant="secondary"
              size="sm"
              className="absolute top-0 right-0 flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white border-white/30"
            >
              <Settings className="h-4 w-4" />
              Admin
            </Button>
            <div className="text-center">
              <div className="flex items-center justify-center gap-3 mb-3">
                <h1 className="text-3xl font-bold">Wilo AI Water Transfer System - Demo Dashboard</h1>
              </div>
              <div className="mt-3 text-base">
                <span className="bg-white/20 px-4 py-2 rounded-full">
                  Day {currentDay} of 30
                </span>
              </div>
            </div>
          </div>
        </Card>

        {/* Visual Progress Indicators */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <Card className="p-6 bg-card border-border">
            <div className="flex items-center gap-3 mb-4">
              <Activity className="h-6 w-6 text-primary" />
              <h3 className="text-lg font-semibold">System Health</h3>
            </div>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>AI Confidence</span>
                  <span>{systemStatus.aiConfidence}</span>
                </div>
                <Progress
                  value={parseInt(systemStatus.aiConfidence)}
                  className="h-2"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Sensor Health</span>
                  <span>{systemStatus.sensorHealth.split('/')[0]}/7</span>
                </div>
                <Progress
                  value={(parseInt(systemStatus.sensorHealth.split('/')[0]) / 7) * 100}
                  className="h-2"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Simulation Progress</span>
                  <span>{Math.round((currentDay / 30) * 100)}%</span>
                </div>
                <Progress
                  value={(currentDay / 30) * 100}
                  className="h-2"
                />
              </div>
            </div>
          </Card>

          <Card className="p-6 bg-card border-border">
            <div className="flex items-center gap-3 mb-4">
              <Zap className="h-6 w-6 text-primary" />
              <h3 className="text-lg font-semibold">System Status</h3>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Pump Status</span>
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${systemStatus.pumpStatus === "RUNNING" ? "bg-green-500 animate-pulse" : "bg-gray-400"}`} />
                  <span className="text-sm font-medium">{systemStatus.pumpStatus}</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Network</span>
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${systemStatus.networkStatus === "Connected" ? "bg-green-500" : "bg-red-500"}`} />
                  <span className="text-sm font-medium">{systemStatus.networkStatus}</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Uptime</span>
                <span className="text-sm font-medium">{systemStatus.uptime}</span>
              </div>
            </div>
          </Card>

          <Card className="p-6 bg-card border-border">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle className="h-6 w-6 text-primary" />
              <h3 className="text-lg font-semibold">Alert Level</h3>
            </div>
            <div className="text-center">
              <div className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center text-2xl font-bold mb-3 ${currentDay <= 5 ? "bg-green-100 text-green-700" :
                currentDay <= 15 ? "bg-yellow-100 text-yellow-700" :
                  currentDay <= 25 ? "bg-red-100 text-red-700" :
                    "bg-blue-100 text-blue-700"
                }`}>
                {currentDay <= 5 ? "✓" : currentDay <= 15 ? "!" : currentDay <= 25 ? "⚠" : "✓"}
              </div>
              <p className="text-sm font-medium">
                {currentDay <= 5 ? "Optimal" :
                  currentDay <= 15 ? "Degraded" :
                    currentDay <= 25 ? "Critical" : "Restored"}
              </p>
            </div>
          </Card>
        </div>

        <SystemDashboard
          systemStatus={systemStatus}
          aiPredictions={aiPredictions}
        />

        <TimelineSimulation
          events={visibleEvents}
          currentDay={currentDay}
        />

        {/* Enhanced Controls */}
        <div className="mt-8 max-w-2xl mx-auto">
          <Card className="p-6 bg-card border-border">
            <div className="text-center mb-6">
              <h3 className="text-lg font-semibold mb-2">Simulation Controls</h3>
              <p className="text-sm text-muted-foreground">Navigate through the 30-day simulation timeline</p>
            </div>

            {/* Quick Jump Buttons */}
            <div className="flex justify-center gap-2 mb-6">
              <Button
                onClick={() => handleDayChange([1])}
                variant={currentDay <= 5 ? "default" : "outline"}
                size="sm"
                className="flex items-center gap-2"
              >
                <SkipBack className="h-4 w-4" />
                Day 1-5
              </Button>
              <Button
                onClick={() => handleDayChange([10])}
                variant={currentDay > 5 && currentDay <= 15 ? "default" : "outline"}
                size="sm"
                className="flex items-center gap-2"
              >
                Day 10-15
              </Button>
              <Button
                onClick={() => handleDayChange([20])}
                variant={currentDay > 15 && currentDay <= 25 ? "default" : "outline"}
                size="sm"
                className="flex items-center gap-2"
              >
                Day 20-25
              </Button>
              <Button
                onClick={() => handleDayChange([30])}
                variant={currentDay > 25 ? "default" : "outline"}
                size="sm"
                className="flex items-center gap-2"
              >
                <FastForward className="h-4 w-4" />
                Day 30
              </Button>
            </div>

            {/* Day Slider */}
            <div className="mb-6">
              <div className="flex justify-between items-center mb-4">
                <label className="text-sm font-medium text-muted-foreground">
                  Day Selection
                </label>
                <div className="bg-primary/10 px-3 py-1 rounded-full">
                  <span className="text-sm font-bold text-primary">Day {currentDay}</span>
                </div>
              </div>
              <div className="px-4">
                <Slider
                  value={[currentDay]}
                  onValueChange={handleDayChange}
                  max={30}
                  min={1}
                  step={1}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-2">
                  <span>Day 1</span>
                  <span>Day 10</span>
                  <span>Day 20</span>
                  <span>Day 30</span>
                </div>
              </div>
            </div>

            {/* Control Buttons */}
            <div className="flex justify-center gap-3">
              <Button
                onClick={() => handleDayChange([Math.max(1, currentDay - 1)])}
                variant="outline"
                size="sm"
                disabled={currentDay === 1}
                className="flex items-center gap-2"
              >
                <SkipBack className="h-4 w-4" />
                Previous
              </Button>
              <Button
                onClick={resetDemo}
                variant="outline"
                size="sm"
                className="flex items-center gap-2"
              >
                <RotateCcw className="h-4 w-4" />
                Reset
              </Button>
              <Button
                onClick={() => handleDayChange([Math.min(30, currentDay + 1)])}
                variant="outline"
                size="sm"
                disabled={currentDay === 30}
                className="flex items-center gap-2"
              >
                Next
                <FastForward className="h-4 w-4" />
              </Button>
            </div>
          </Card>
        </div>


      </div>
    </div>
  );
}
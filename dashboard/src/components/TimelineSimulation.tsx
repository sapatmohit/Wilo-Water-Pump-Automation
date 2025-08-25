import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle, Clock, AlertTriangle, Cpu } from "lucide-react";

interface TimelineEvent {
  id: string;
  day: number;
  title: string;
  status: "optimal" | "degraded" | "critical" | "restored";
  sensorStatus: string;
  startTime: string;
  duration: string;
  aiDecision: string;
  isActive?: boolean;
}

interface TimelineSimulationProps {
  events: TimelineEvent[];
  currentDay: number;
}

export function TimelineSimulation({ events, currentDay }: TimelineSimulationProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "optimal":
      case "restored":
        return <CheckCircle className="h-5 w-5 text-green-success" />;
      case "degraded":
        return <AlertTriangle className="h-5 w-5 text-orange-warning" />;
      case "critical":
        return <AlertCircle className="h-5 w-5 text-red-error" />;
      default:
        return <Clock className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "optimal":
        return <Badge variant="default" className="bg-green-success text-white">Optimal</Badge>;
      case "degraded":
        return <Badge variant="default" className="bg-orange-warning text-white">Degraded</Badge>;
      case "critical":
        return <Badge variant="default" className="bg-red-error text-white">Critical</Badge>;
      case "restored":
        return <Badge variant="default" className="bg-green-success text-white">Restored</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  const getEventVariant = (status: string) => {
    switch (status) {
      case "critical":
        return "border-red-error/50 bg-red-error/5";
      case "degraded":
        return "border-orange-warning/50 bg-orange-warning/5";
      default:
        return "border-green-success/50 bg-green-success/5";
    }
  };

  // Get the current active event based on the day
  const getCurrentEvent = () => {
    if (currentDay <= 5) return events.find(e => e.day === 1);
    if (currentDay <= 15) return events.find(e => e.day === 10);
    if (currentDay <= 25) return events.find(e => e.day === 20);
    return events.find(e => e.day === 30);
  };

  const currentEvent = getCurrentEvent();

  if (!currentEvent) return null;

  return (
    <Card className="p-6 bg-card border-border">
      <div className="flex items-center gap-3 mb-6">
        <Clock className="h-6 w-6 text-primary" />
        <h2 className="text-xl font-semibold text-foreground">Current System Status</h2>
      </div>

      <div className="relative">
        <div
          className={cn(
            "relative p-6 rounded-lg border-2 transition-all duration-500 shadow-lg ring-2 ring-primary/50",
            getEventVariant(currentEvent.status)
          )}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {getStatusIcon(currentEvent.status)}
              <h3 className="text-lg font-semibold text-foreground">{currentEvent.title}</h3>
            </div>
            {getStatusBadge(currentEvent.status)}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="p-3 bg-muted/50 rounded-lg">
              <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                Sensor Status
              </h5>
              <div className="flex items-center gap-2">
                <div className={cn(
                  "w-3 h-3 rounded-full",
                  currentEvent.sensorStatus.includes("7/7") ? "bg-green-success" :
                    currentEvent.sensorStatus.includes("Active") ? "bg-orange-warning" : "bg-red-error"
                )} />
                <span className="font-semibold text-foreground">{currentEvent.sensorStatus}</span>
              </div>
            </div>

            <div className="p-3 bg-muted/50 rounded-lg">
              <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                Start Time
              </h5>
              <span className="font-semibold text-foreground">{currentEvent.startTime}</span>
            </div>

            <div className="p-3 bg-muted/50 rounded-lg">
              <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                Duration
              </h5>
              <span className="font-semibold text-foreground">{currentEvent.duration}</span>
            </div>
          </div>

          <div className="p-4 bg-primary/10 rounded-lg border border-primary/20">
            <h5 className="font-semibold text-primary mb-2 flex items-center gap-2">
              <Cpu className="h-4 w-4" />
              AI Decision:
            </h5>
            <p className="text-sm text-foreground/80 leading-relaxed">{currentEvent.aiDecision}</p>
          </div>

          <div className="absolute -top-1 -right-1">
            <div className="w-4 h-4 bg-primary rounded-full animate-pulse shadow-lg" />
          </div>
        </div>
      </div>
    </Card>
  );
}
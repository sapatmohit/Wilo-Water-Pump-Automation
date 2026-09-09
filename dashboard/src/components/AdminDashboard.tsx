import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
    Settings,
    Power,
    AlertTriangle,
    Activity,
    Droplets,
    Gauge,
    Thermometer,
    Wifi,
    Calendar,
    Play,
    Pause,
    Trash2,
    RotateCcw,
    Plus,
    Clock,
    Zap,
    Cpu,
    Radio,
    CheckCircle,
    XCircle,
    Info,
    ShieldAlert,
    RefreshCw
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import { AuthIndicator } from "./AuthDialog";
import { FestivalPolicySection } from "./FestivalPolicySection";

interface HardwareComponentStatus {
    connected: boolean;
    status: string;
    reason?: string | null;
    [key: string]: any;
}

interface HardwareStatusPayload {
    master_motor: {
        connected: boolean;
        status: string;
        raspberry_pi: HardwareComponentStatus;
        current_sensor: HardwareComponentStatus;
        relay: HardwareComponentStatus;
    };
    slave_motor: {
        connected: boolean;
        status: string;
        esp32: HardwareComponentStatus;
        pressure_sensor: HardwareComponentStatus;
        lora: HardwareComponentStatus;
    };
    tank: {
        level_percent: number | null;
        level_liters: number | null;
        state: string;
        color: string;
        source: string;
        pressure_kpa: number | null;
        net_pressure_kpa: number | null;
        height_cm: number | null;
        max_height_cm: number;
        capacity_liters: number;
        is_empty: boolean;
        stale: boolean;
        verification_note: string;
    };
    system_connected: boolean;
    timestamp: string;
}

function AdminDashboard() {
    const { toast } = useToast();
    const navigate = useNavigate();

    // System Override States
    const [systemOverride, setSystemOverride] = useState(false);
    const [pumpOverride, setPumpOverride] = useState(false);
    const [emergencyStop, setEmergencyStop] = useState(false);

    // Hardware Connectivity State
    const [activeHardwareTab, setActiveHardwareTab] = useState<'master' | 'slave'>('master');
    const [hardwareData, setHardwareData] = useState<HardwareStatusPayload | null>(null);

    // Pump Status
    const [pumpData, setPumpData] = useState({
        mainPump: { status: "standby", health: 95, pressure: 0, flow: 0 }
    });

    // Energy consumption tracking
    const [energyData, setEnergyData] = useState({
        currentUsage: 0,        // kW
        dailyConsumption: 45.2, // kWh
        weeklyConsumption: 312.5, // kWh
        efficiency: 92          // %
    });

    // Manual Scheduling State
    const [isManualMode, setIsManualMode] = useState(false);
    const [scheduleDate, setScheduleDate] = useState(() => {
        const today = new Date();
        return today.toISOString().split('T')[0];
    });
    const [scheduleTime, setScheduleTime] = useState(() => {
        const now = new Date();
        now.setMinutes(now.getMinutes() + 1);
        return now.toTimeString().slice(0, 5);
    });
    const [scheduleDuration, setScheduleDuration] = useState("30");
    const [scheduledTasks, setScheduledTasks] = useState<Array<{
        id: string;
        date: string;
        time: string;
        duration: string;
        status: "scheduled" | "running" | "completed" | "expired";
        type: "manual" | "routine" | "maintenance" | "emergency";
        timeoutId?: NodeJS.Timeout;
        endTimeoutId?: NodeJS.Timeout;
    }>>([]);

    // Water Cut Management
    const [waterCuts, setWaterCuts] = useState<Array<{
        id: number;
        area: string;
        startTime: string;
        endTime: string;
        reason: string;
        status: string;
    }>>([]);

    const [showWaterCutForm, setShowWaterCutForm] = useState(false);
    const [newWaterCut, setNewWaterCut] = useState({
        area: "",
        reason: "",
        startTime: "10:00",
        endTime: "14:00"
    });

    // Backend API Sync
    useEffect(() => {
        let mounted = true;

        const fetchWaterCuts = () => {
            fetch("/api/water-cuts")
                .then(res => res.json())
                .then(data => {
                    if (mounted && data.ok && Array.isArray(data.water_cuts)) {
                        setWaterCuts(data.water_cuts);
                    }
                })
                .catch(() => {});
        };

        const fetchSchedule = () => {
            fetch("/api/schedule")
                .then(res => res.json())
                .then(data => {
                    if (mounted && data.ok && Array.isArray(data.tasks)) {
                        setScheduledTasks(data.tasks);
                    }
                })
                .catch(() => {});
        };

        const fetchHardware = () => {
            fetch("/api/hardware/status")
                .then(res => res.json())
                .then(data => {
                    if (mounted && data.ok) {
                        setHardwareData(data);
                    }
                })
                .catch(() => {});
        };

        const syncStatus = () => {
            fetch("/api/dashboard/status")
                .then(res => res.json())
                .then(data => {
                    if (!mounted || !data.ok) return;
                    if (data.system_mode) {
                        setSystemOverride(data.system_mode === "manual");
                    }
                    if (typeof data.emergency_stop === "boolean") {
                        setEmergencyStop(data.emergency_stop);
                    }
                    if (data.pump && typeof data.pump.pump_relay_on === "boolean") {
                        const isRelayOn = Boolean(data.pump.pump_relay_on);
                        setPumpOverride(isRelayOn);
                        setPumpData({
                            mainPump: {
                                status: isRelayOn ? "running" : "standby",
                                health: 95,
                                pressure: isRelayOn ? 2.8 : 0,
                                flow: isRelayOn ? 100 : 0
                            }
                        });
                        setEnergyData(prev => ({
                            ...prev,
                            currentUsage: isRelayOn ? 2.85 : 0.0
                        }));
                    }
                })
                .catch(() => {});
        };

        fetchWaterCuts();
        fetchSchedule();
        fetchHardware();
        syncStatus();

        const pollTimer = setInterval(() => {
            fetchHardware();
            syncStatus();
        }, 3500);

        return () => {
            mounted = false;
            clearInterval(pollTimer);
        };
    }, []);

    const handleSystemOverrideChange = async (checked: boolean) => {
        setSystemOverride(checked);
        try {
            const res = await fetch("/api/mode", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode: checked ? "manual" : "auto" })
            });
            const data = await res.json();
            if (data.ok) {
                toast({
                    title: `Switched to ${checked ? "Manual" : "Automated"} Mode`,
                    description: `Controller is now in ${data.mode} mode.`
                });
            }
        } catch (err) {
            toast({
                title: "Error switching mode",
                description: String(err),
                variant: "destructive"
            });
        }
    };

    const handlePumpOverrideChange = async (checked: boolean) => {
        setPumpOverride(checked);
        const endpoint = checked ? "/api/pump/on" : "/api/pump/off";
        try {
            const res = await fetch(endpoint, { method: "POST" });
            const data = await res.json();
            if (data.ok) {
                setPumpData(prev => ({
                    ...prev,
                    mainPump: {
                        ...prev.mainPump,
                        status: checked ? "running" : "standby",
                        pressure: checked ? 2.8 : 0,
                        flow: checked ? 100 : 0
                    }
                }));
                toast({
                    title: checked ? "Pump Started" : "Pump Stopped",
                    description: data.message || `Pump relay set to ${checked ? "ON" : "OFF"}`
                });
            } else {
                toast({
                    title: "Pump action blocked",
                    description: data.error || "Action failed",
                    variant: "destructive"
                });
            }
        } catch (err) {
            toast({
                title: "Pump control failed",
                description: String(err),
                variant: "destructive"
            });
        }
    };

    const handleEmergencyStop = async () => {
        const targetState = !emergencyStop;
        setEmergencyStop(targetState);
        try {
            if (targetState) {
                const res = await fetch("/api/emergency-stop", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ reason: "Emergency Stop triggered by operator in Admin view" })
                });
                const data = await res.json();
                if (data.ok) {
                    setPumpOverride(false);
                    setPumpData(prev => ({
                        ...prev,
                        mainPump: { ...prev.mainPump, status: "standby", flow: 0, pressure: 0 }
                    }));
                    toast({
                        title: "EMERGENCY STOP ACTIVATED",
                        description: "All pump operations halted immediately. Safety lock engaged.",
                        variant: "destructive"
                    });
                }
            } else {
                const res = await fetch("/api/emergency-stop/reset", { method: "POST" });
                const data = await res.json();
                if (data.ok) {
                    toast({
                        title: "Emergency Stop Cleared",
                        description: "Safety lock released. Normal operations may resume.",
                        variant: "default"
                    });
                }
            }
        } catch (err) {
            toast({
                title: "Emergency stop failed",
                description: String(err),
                variant: "destructive"
            });
        }
    };

    const handlePumpToggle = (pumpName: string) => {
        const isRunning = pumpData.mainPump.status === 'running';
        handlePumpOverrideChange(!isRunning);
    };

    const handleScheduleTask = () => {
        if (!scheduleDate || !scheduleTime || !scheduleDuration) {
            toast({
                title: "Invalid Schedule",
                description: "Please fill in all schedule fields",
                variant: "destructive"
            });
            return;
        }

        const newTask = {
            id: `task-${Date.now()}`,
            date: scheduleDate,
            time: scheduleTime,
            duration: scheduleDuration,
            status: "scheduled" as const,
            type: "manual" as const
        };

        fetch("/api/schedule", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newTask)
        })
            .then(res => res.json())
            .then(() => {
                setScheduledTasks(prev => [...prev, newTask]);
                toast({
                    title: "Task Scheduled",
                    description: `Pump run scheduled for ${scheduleDate} at ${scheduleTime} (${scheduleDuration} min)`
                });
            })
            .catch(err => {
                toast({
                    title: "Schedule failed",
                    description: String(err),
                    variant: "destructive"
                });
            });
    };

    const handleDeleteTask = (taskId: string) => {
        fetch(`/api/schedule/${taskId}`, { method: "DELETE" })
            .then(res => res.json())
            .then(() => {
                setScheduledTasks(prev => prev.filter(t => t.id !== taskId));
                toast({ title: "Task Deleted", description: "Scheduled task removed." });
            })
            .catch(() => {});
    };

    const handleDeleteWaterCut = (cutId: number) => {
        fetch(`/api/water-cuts/${cutId}`, { method: "DELETE" })
            .then(res => res.json())
            .then(() => {
                setWaterCuts(prev => prev.filter(c => c.id !== cutId));
                toast({ title: "Water Cut Removed", description: "Municipal schedule updated." });
            })
            .catch(() => {});
    };

    // Derived tank data from hardware status
    const tankInfo = hardwareData?.tank || {
        level_percent: null,
        level_liters: null,
        state: "SENSOR OFFLINE",
        color: "gray",
        source: "ESP32 (PR12P210) → LoRa 433MHz → Raspberry Pi",
        pressure_kpa: null,
        net_pressure_kpa: null,
        height_cm: null,
        max_height_cm: 200,
        capacity_liters: 25000,
        is_empty: false,
        stale: true,
        verification_note: "Tank level requires live hydrostatic pressure. Pump OFF does NOT imply empty."
    };

    const getTankLevelColor = (state: string, level: number | null) => {
        if (state === "CRITICAL LOW" || (level !== null && level <= 10)) return "bg-red-500 text-white";
        if (state === "LOW" || (level !== null && level <= 25)) return "bg-amber-500 text-white";
        if (state === "NORMAL" || (level !== null && level < 85)) return "bg-blue-600 text-white";
        if (state === "HIGH" || (level !== null && level < 95)) return "bg-emerald-500 text-white";
        if (state === "FULL" || (level !== null && level >= 95)) return "bg-green-600 text-white";
        return "bg-slate-400 text-white";
    };

    const isMasterConnected = Boolean(hardwareData?.master_motor?.connected);
    const isSlaveConnected = Boolean(hardwareData?.slave_motor?.connected);

    return (
        <div className="min-h-screen bg-background text-foreground p-6">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-6">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <h1 className="text-3xl font-bold tracking-tight text-foreground">Wilo Admin Engineering Console</h1>
                            <Badge variant={isMasterConnected && isSlaveConnected ? "default" : "secondary"}>
                                {isMasterConnected && isSlaveConnected ? "SYSTEM ONLINE" : "PARTIAL / OFFLINE"}
                            </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            Hardware connectivity inspection, real sensor-based hydrostatic tank state, and system overrides.
                        </p>
                    </div>
                    <div className="flex items-center gap-3">
                        <Button
                            onClick={() => navigate("/")}
                            variant="outline"
                            size="sm"
                        >
                            Operations Dashboard
                        </Button>
                        <AuthIndicator />
                    </div>
                </div>

                {/* Emergency Stop & System Overrides */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Emergency Stop Banner Card */}
                    <Card className={`p-5 border-2 transition-all ${emergencyStop ? 'border-red-600 bg-red-50' : 'border-border bg-card'}`}>
                        <div className="flex items-start justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <ShieldAlert className={`h-5 w-5 ${emergencyStop ? 'text-red-600 animate-pulse' : 'text-muted-foreground'}`} />
                                    <h3 className="font-semibold text-lg">Emergency Stop</h3>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    {emergencyStop ? "CRITICAL: PUMPS LOCKED OFF" : "Instantly cuts relay outputs"}
                                </p>
                            </div>
                            <Button
                                onClick={handleEmergencyStop}
                                variant={emergencyStop ? "outline" : "destructive"}
                                size="sm"
                                className="font-bold uppercase tracking-wider"
                            >
                                {emergencyStop ? "Clear Lock" : "E-STOP 🔴"}
                            </Button>
                        </div>
                    </Card>

                    {/* Mode Control Card */}
                    <Card className="p-5 border-border bg-card">
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <Settings className="h-5 w-5 text-primary" />
                                    <h3 className="font-semibold text-lg">System Mode</h3>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    {systemOverride ? "Manual operator control" : "Automated ML & threshold loop"}
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Label htmlFor="system-override" className="text-sm font-medium">
                                    {systemOverride ? "MANUAL" : "AUTO"}
                                </Label>
                                <Switch
                                    id="system-override"
                                    checked={systemOverride}
                                    onCheckedChange={handleSystemOverrideChange}
                                />
                            </div>
                        </div>
                    </Card>

                    {/* Direct Relay Override Card */}
                    <Card className="p-5 border-border bg-card">
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <Power className="h-5 w-5 text-primary" />
                                    <h3 className="font-semibold text-lg">Pump Relay</h3>
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    GPIO 17 State: <span className="font-bold">{pumpOverride ? "ON" : "OFF"}</span>
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <Label htmlFor="pump-override" className="text-sm font-medium">
                                    {pumpOverride ? "ON" : "OFF"}
                                </Label>
                                <Switch
                                    id="pump-override"
                                    checked={pumpOverride}
                                    disabled={!systemOverride || emergencyStop}
                                    onCheckedChange={handlePumpOverrideChange}
                                />
                            </div>
                        </div>
                    </Card>
                </div>

                {/* REAL SENSOR-BASED TANK STATE & VISUALIZATION */}
                <Card className="p-6 border-border bg-card">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6 border-b pb-4">
                        <div>
                            <div className="flex items-center gap-3 mb-1">
                                <Droplets className="h-6 w-6 text-primary" />
                                <h3 className="text-xl font-bold text-foreground">Rooftop Upper Tank — Real Sensor-Based Visualization</h3>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                Water level calculated strictly from hydrostatic pressure sensor readings. Zero synthetic numbers.
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-muted-foreground">Tank Status:</span>
                            <Badge className={`px-3 py-1 font-semibold text-xs ${getTankLevelColor(tankInfo.state, tankInfo.level_percent)}`}>
                                {tankInfo.state}
                            </Badge>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
                        {/* 3D Cylindrical Tank Visualizer */}
                        <div className="lg:col-span-5 flex flex-col items-center justify-center p-4 bg-muted/20 rounded-xl">
                            <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
                                Upper Tank (25,000 Liters)
                            </div>

                            <div className="relative w-44 h-64 border-4 border-slate-400 rounded-2xl bg-slate-100 overflow-hidden shadow-inner">
                                {/* Tank Cap / Flange */}
                                <div className="absolute top-0 left-0 right-0 h-4 bg-slate-300 border-b border-slate-400 z-10 opacity-70"></div>

                                {/* Water Level Fill */}
                                <div
                                    className={`absolute bottom-0 left-0 right-0 transition-all duration-700 ${getTankLevelColor(tankInfo.state, tankInfo.level_percent)}`}
                                    style={{ height: `${tankInfo.level_percent !== null ? Math.max(0, Math.min(100, tankInfo.level_percent)) : 0}%` }}
                                >
                                    {/* Water Surface Wave Effect */}
                                    <div className="absolute top-0 left-0 right-0 h-2 bg-white/30 animate-pulse"></div>
                                </div>

                                {/* Center Water Level Badge */}
                                <div className="absolute inset-0 flex flex-col items-center justify-center z-10 pointer-events-none">
                                    <span className="text-3xl font-extrabold text-slate-900 drop-shadow-sm">
                                        {tankInfo.level_percent !== null ? `${tankInfo.level_percent}%` : "--%"}
                                    </span>
                                    <span className="text-xs font-semibold text-slate-700 bg-white/70 px-2 py-0.5 rounded mt-1">
                                        {tankInfo.level_liters !== null ? `${tankInfo.level_liters.toLocaleString()} L` : "Offline"}
                                    </span>
                                </div>

                                {/* Graduation Markers */}
                                <div className="absolute top-0 bottom-0 left-2 flex flex-col justify-between text-[9px] font-mono text-slate-500 py-2 pointer-events-none">
                                    <span>- 100%</span>
                                    <span>- 75%</span>
                                    <span>- 50%</span>
                                    <span>- 25%</span>
                                    <span>- 0%</span>
                                </div>
                            </div>

                            <div className="mt-4 text-center">
                                <p className="text-xs text-muted-foreground">
                                    Water Column: <span className="font-semibold text-foreground">{tankInfo.height_cm !== null ? `${tankInfo.height_cm} cm` : "-- cm"} / 200 cm</span>
                                </p>
                            </div>
                        </div>

                        {/* Physics & Sensor Traceability Breakdown */}
                        <div className="lg:col-span-7 space-y-4">
                            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
                                <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
                                    <Info className="h-4 w-4 text-primary" />
                                    Data Source & Telemetry Pipeline
                                </h4>
                                <div className="flex items-center gap-2 text-xs font-mono bg-white p-2.5 rounded border border-slate-200">
                                    <span className="text-primary font-bold">ESP32 (PR12P210)</span>
                                    <span className="text-muted-foreground">──[LoRa 433MHz]──&gt;</span>
                                    <span className="text-primary font-bold">RPi Receiver</span>
                                    <span className="text-muted-foreground">──&gt;</span>
                                    <span className="text-green-700 font-bold">Dashboard</span>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                                <div className="p-3 bg-card border rounded-lg">
                                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Raw Pressure</p>
                                    <p className="text-lg font-bold text-foreground">
                                        {tankInfo.pressure_kpa !== null ? `${tankInfo.pressure_kpa} kPa` : "--"}
                                    </p>
                                </div>
                                <div className="p-3 bg-card border rounded-lg">
                                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Calibrated Offset</p>
                                    <p className="text-lg font-bold text-foreground">-23.00 kPa</p>
                                </div>
                                <div className="p-3 bg-card border rounded-lg">
                                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Net Hydrostatic</p>
                                    <p className="text-lg font-bold text-primary">
                                        {tankInfo.net_pressure_kpa !== null ? `${tankInfo.net_pressure_kpa} kPa` : "--"}
                                    </p>
                                </div>
                                <div className="p-3 bg-card border rounded-lg">
                                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Water Height</p>
                                    <p className="text-lg font-bold text-foreground">
                                        {tankInfo.height_cm !== null ? `${tankInfo.height_cm} cm` : "--"}
                                    </p>
                                </div>
                                <div className="p-3 bg-card border rounded-lg">
                                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Volume</p>
                                    <p className="text-lg font-bold text-foreground">
                                        {tankInfo.level_liters !== null ? `${tankInfo.level_liters.toLocaleString()} L` : "--"}
                                    </p>
                                </div>
                                <div className="p-3 bg-card border rounded-lg">
                                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Capacity</p>
                                    <p className="text-lg font-bold text-foreground">25,000 L</p>
                                </div>
                            </div>

                            {/* STRICT RULE VERIFICATION CALLOUT */}
                            <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3">
                                <Info className="h-5 w-5 text-blue-600 mt-0.5 shrink-0" />
                                <div className="text-xs leading-relaxed text-blue-900">
                                    <span className="font-bold">Strict Rule Verification:</span> {tankInfo.verification_note}
                                    <div className="mt-1 font-mono text-[11px] text-blue-700">
                                        Formula: h = (P_net · 1000) / (ρ · g) | Level % = (h_cm / 200) · 100
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </Card>

                {/* SYSTEM HARDWARE & SENSOR CONNECTIVITY TABS */}
                <Card className="p-6 border-border bg-card">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6 border-b pb-4">
                        <div>
                            <div className="flex items-center gap-3 mb-1">
                                <Activity className="h-6 w-6 text-primary" />
                                <h3 className="text-xl font-bold text-foreground">System Hardware &amp; Sensor Connectivity</h3>
                            </div>
                            <p className="text-sm text-muted-foreground">
                                Zero-fake evidence-based hardware status. Shows <span className="font-semibold text-red-600">NO 🔴</span> when physical hardware is not present.
                            </p>
                        </div>

                        {/* Structured Tabs */}
                        <div className="flex items-center gap-2 bg-muted/40 p-1 rounded-lg border">
                            <button
                                onClick={() => setActiveHardwareTab('master')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-all ${
                                    activeHardwareTab === 'master'
                                        ? "bg-card text-foreground shadow-sm"
                                        : "text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                <Cpu className="h-4 w-4 text-primary" />
                                Master Motor
                                <span className={`h-2.5 w-2.5 rounded-full ${isMasterConnected ? "bg-green-500" : "bg-red-500"}`}></span>
                            </button>
                            <button
                                onClick={() => setActiveHardwareTab('slave')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-all ${
                                    activeHardwareTab === 'slave'
                                        ? "bg-card text-foreground shadow-sm"
                                        : "text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                <Radio className="h-4 w-4 text-primary" />
                                Slave Motor
                                <span className={`h-2.5 w-2.5 rounded-full ${isSlaveConnected ? "bg-green-500" : "bg-red-500"}`}></span>
                            </button>
                        </div>
                    </div>

                    {/* TAB 1: MASTER MOTOR (RPi, Current Sensor, Relay) */}
                    {activeHardwareTab === 'master' && (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between p-3 bg-muted/20 rounded-lg">
                                <span className="text-sm font-semibold">Master Motor Connectivity:</span>
                                <Badge variant={isMasterConnected ? "default" : "destructive"}>
                                    {isMasterConnected ? "YES 🟢 (CONNECTED)" : "NO 🔴 (OFFLINE)"}
                                </Badge>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {/* Raspberry Pi Controller Card */}
                                <Card className="p-4 border">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <Cpu className="h-5 w-5 text-primary" />
                                            <h4 className="font-semibold text-sm">Raspberry Pi Controller</h4>
                                        </div>
                                        <Badge variant={hardwareData?.master_motor?.raspberry_pi?.connected ? "default" : "destructive"}>
                                            {hardwareData?.master_motor?.raspberry_pi?.connected ? "YES 🟢" : "NO 🔴"}
                                        </Badge>
                                    </div>
                                    <div className="space-y-2 text-xs">
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Hardware:</span>
                                            <span className="font-medium">{hardwareData?.master_motor?.raspberry_pi?.hardware || "Non-RPi Host"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Model:</span>
                                            <span className="font-medium">{hardwareData?.master_motor?.raspberry_pi?.model || "--"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Hostname:</span>
                                            <span className="font-mono">{hardwareData?.master_motor?.raspberry_pi?.hostname || "--"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">GPIO Driver:</span>
                                            <span className="font-medium">
                                                {hardwareData?.master_motor?.raspberry_pi?.gpio_available ? "RPi.GPIO Native" : "MockGPIO Fallback"}
                                            </span>
                                        </div>
                                        {hardwareData?.master_motor?.raspberry_pi?.reason && (
                                            <div className="pt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded">
                                                ⚠️ {hardwareData.master_motor.raspberry_pi.reason}
                                            </div>
                                        )}
                                    </div>
                                </Card>

                                {/* Current Sensor Card (ADS1115 + ACS712) */}
                                <Card className="p-4 border">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <Zap className="h-5 w-5 text-primary" />
                                            <h4 className="font-semibold text-sm">Current Sensor (ACS712)</h4>
                                        </div>
                                        <Badge variant={hardwareData?.master_motor?.current_sensor?.connected ? "default" : "destructive"}>
                                            {hardwareData?.master_motor?.current_sensor?.connected ? "YES 🟢" : "NO 🔴"}
                                        </Badge>
                                    </div>
                                    <div className="space-y-2 text-xs">
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">ADC Interface:</span>
                                            <span className="font-medium">{hardwareData?.master_motor?.current_sensor?.sensor_type || "ADS1115 ADC"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Live Current:</span>
                                            <span className="font-bold text-foreground">
                                                {hardwareData?.master_motor?.current_sensor?.current_amps !== null
                                                    ? `${hardwareData?.master_motor?.current_sensor?.current_amps} A`
                                                    : "-- A"}
                                            </span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">I2C Address:</span>
                                            <span className="font-mono">{hardwareData?.master_motor?.current_sensor?.i2c_address || "0x48"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Signal Status:</span>
                                            <span className="font-medium text-amber-600">
                                                {hardwareData?.master_motor?.current_sensor?.last_reading_age_text || "No records"}
                                            </span>
                                        </div>
                                        {hardwareData?.master_motor?.current_sensor?.reason && (
                                            <div className="pt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded">
                                                ⚠️ {hardwareData.master_motor.current_sensor.reason}
                                            </div>
                                        )}
                                    </div>
                                </Card>

                                {/* Pump Relay Card (GPIO 17) */}
                                <Card className="p-4 border">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <Power className="h-5 w-5 text-primary" />
                                            <h4 className="font-semibold text-sm">Pump Relay (GPIO 17)</h4>
                                        </div>
                                        <Badge variant={hardwareData?.master_motor?.relay?.connected ? "default" : "destructive"}>
                                            {hardwareData?.master_motor?.relay?.connected ? "YES 🟢" : "NO 🔴"}
                                        </Badge>
                                    </div>
                                    <div className="space-y-2 text-xs">
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Control Pin:</span>
                                            <span className="font-mono">BCM GPIO 17</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">State:</span>
                                            <span className={`font-bold ${pumpOverride ? "text-green-600" : "text-muted-foreground"}`}>
                                                {pumpOverride ? "RELAY ON" : "RELAY OFF"}
                                            </span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Relay Mode:</span>
                                            <span className="font-medium">{systemOverride ? "MANUAL" : "AUTO"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Spare Valve Pin:</span>
                                            <span className="font-mono">BCM GPIO 27</span>
                                        </div>
                                        {hardwareData?.master_motor?.relay?.reason && (
                                            <div className="pt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded">
                                                ⚠️ {hardwareData.master_motor.relay.reason}
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            </div>
                        </div>
                    )}

                    {/* TAB 2: SLAVE MOTOR (ESP32, Pressure Sensor, LoRa Link) */}
                    {activeHardwareTab === 'slave' && (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between p-3 bg-muted/20 rounded-lg">
                                <span className="text-sm font-semibold">Slave Motor &amp; LoRa Link Status:</span>
                                <Badge variant={isSlaveConnected ? "default" : "destructive"}>
                                    {isSlaveConnected ? "YES 🟢 (CONNECTED)" : "NO 🔴 (TIMEOUT / OFFLINE)"}
                                </Badge>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {/* ESP32 Microcontroller Card */}
                                <Card className="p-4 border">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <Radio className="h-5 w-5 text-primary" />
                                            <h4 className="font-semibold text-sm">ESP32 Node</h4>
                                        </div>
                                        <Badge variant={hardwareData?.slave_motor?.esp32?.connected ? "default" : "destructive"}>
                                            {hardwareData?.slave_motor?.esp32?.connected ? "YES 🟢" : "NO 🔴"}
                                        </Badge>
                                    </div>
                                    <div className="space-y-2 text-xs">
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Device ID:</span>
                                            <span className="font-mono font-medium">{hardwareData?.slave_motor?.esp32?.device_id || "esp32"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Status:</span>
                                            <span className="font-medium text-amber-600">{hardwareData?.slave_motor?.esp32?.status || "TIMEOUT"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Last Packet:</span>
                                            <span className="font-medium">{hardwareData?.slave_motor?.esp32?.last_packet_age_text || "No signal"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Timestamp:</span>
                                            <span className="font-mono text-[11px]">{hardwareData?.slave_motor?.esp32?.last_packet_timestamp || "--"}</span>
                                        </div>
                                        {hardwareData?.slave_motor?.esp32?.reason && (
                                            <div className="pt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded">
                                                ⚠️ {hardwareData.slave_motor.esp32.reason}
                                            </div>
                                        )}
                                    </div>
                                </Card>

                                {/* Pressure Sensor Card (PR12P210) */}
                                <Card className="p-4 border">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <Gauge className="h-5 w-5 text-primary" />
                                            <h4 className="font-semibold text-sm">Pressure Sensor (PR12P210)</h4>
                                        </div>
                                        <Badge variant={hardwareData?.slave_motor?.pressure_sensor?.connected ? "default" : "destructive"}>
                                            {hardwareData?.slave_motor?.pressure_sensor?.connected ? "YES 🟢" : "NO 🔴"}
                                        </Badge>
                                    </div>
                                    <div className="space-y-2 text-xs">
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Sensor Model:</span>
                                            <span className="font-medium">{hardwareData?.slave_motor?.pressure_sensor?.sensor_model || "PR12P210"}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Live Pressure:</span>
                                            <span className="font-bold text-foreground">
                                                {hardwareData?.slave_motor?.pressure_sensor?.pressure_kpa !== null
                                                    ? `${hardwareData?.slave_motor?.pressure_sensor?.pressure_kpa} kPa`
                                                    : "-- kPa"}
                                            </span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Last Recorded:</span>
                                            <span className="font-mono">
                                                {hardwareData?.slave_motor?.pressure_sensor?.last_recorded_kpa !== null
                                                    ? `${hardwareData?.slave_motor?.pressure_sensor?.last_recorded_kpa} kPa`
                                                    : "--"}
                                            </span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Zero Offset:</span>
                                            <span className="font-medium">23.0 kPa (Calibrated)</span>
                                        </div>
                                        {hardwareData?.slave_motor?.pressure_sensor?.reason && (
                                            <div className="pt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded">
                                                ⚠️ {hardwareData.slave_motor.pressure_sensor.reason}
                                            </div>
                                        )}
                                    </div>
                                </Card>

                                {/* LoRa SX1278 Card */}
                                <Card className="p-4 border">
                                    <div className="flex items-center justify-between mb-3">
                                        <div className="flex items-center gap-2">
                                            <Wifi className="h-5 w-5 text-primary" />
                                            <h4 className="font-semibold text-sm">LoRa Link (SX1278)</h4>
                                        </div>
                                        <Badge variant={hardwareData?.slave_motor?.lora?.connected ? "default" : "destructive"}>
                                            {hardwareData?.slave_motor?.lora?.connected ? "YES 🟢" : "NO 🔴"}
                                        </Badge>
                                    </div>
                                    <div className="space-y-2 text-xs">
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Frequency / Sync:</span>
                                            <span className="font-mono">433 MHz (0xF3)</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Total Packets:</span>
                                            <span className="font-bold">{hardwareData?.slave_motor?.lora?.total_packets || 0}</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Packet Rate:</span>
                                            <span className="font-bold">{hardwareData?.slave_motor?.lora?.packet_rate_per_sec || 0.0} pkt/s</span>
                                        </div>
                                        <div className="flex justify-between border-b pb-1">
                                            <span className="text-muted-foreground">Timeout Threshold:</span>
                                            <span className="font-medium">60 seconds</span>
                                        </div>
                                        {hardwareData?.slave_motor?.lora?.reason && (
                                            <div className="pt-2 text-[11px] text-amber-700 bg-amber-50 p-2 rounded">
                                                ⚠️ {hardwareData.slave_motor.lora.reason}
                                            </div>
                                        )}
                                    </div>
                                </Card>
                            </div>
                        </div>
                    )}
                </Card>

                {/* Manual Scheduling Controls */}
                <Card className="p-6 mb-6 border-border bg-card">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <Settings className="h-6 w-6 text-primary" />
                            <h3 className="text-xl font-semibold text-foreground">Manual Scheduling</h3>
                        </div>
                        <div className="flex items-center gap-2">
                            <Label htmlFor="manual-mode" className="text-sm font-medium">
                                Manual Mode
                            </Label>
                            <Switch
                                id="manual-mode"
                                checked={isManualMode}
                                onCheckedChange={setIsManualMode}
                            />
                        </div>
                    </div>

                    {isManualMode && (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
                                <div className="space-y-2">
                                    <Label htmlFor="schedule-date" className="text-sm font-medium flex items-center gap-2">
                                        <Calendar className="h-4 w-4" />
                                        Date
                                    </Label>
                                    <Input
                                        id="schedule-date"
                                        type="date"
                                        value={scheduleDate}
                                        onChange={(e) => setScheduleDate(e.target.value)}
                                        className="w-full"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="schedule-time" className="text-sm font-medium flex items-center gap-2">
                                        <Clock className="h-4 w-4" />
                                        Time
                                    </Label>
                                    <Input
                                        id="schedule-time"
                                        type="time"
                                        value={scheduleTime}
                                        onChange={(e) => setScheduleTime(e.target.value)}
                                        className="w-full"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="schedule-duration" className="text-sm font-medium flex items-center gap-2">
                                        <Activity className="h-4 w-4" />
                                        Duration (min)
                                    </Label>
                                    <Input
                                        id="schedule-duration"
                                        type="number"
                                        min="1"
                                        max="180"
                                        value={scheduleDuration}
                                        onChange={(e) => setScheduleDuration(e.target.value)}
                                        className="w-full"
                                        placeholder="30"
                                    />
                                </div>

                                <div className="flex items-end">
                                    <Button
                                        onClick={handleScheduleTask}
                                        className="w-full flex items-center gap-2"
                                    >
                                        <Play className="h-4 w-4" />
                                        Schedule Run
                                    </Button>
                                </div>
                            </div>

                            {scheduledTasks.length > 0 && (
                                <div className="space-y-3">
                                    <h4 className="text-md font-semibold text-foreground">Scheduled Tasks</h4>
                                    <div className="space-y-2">
                                        {scheduledTasks.map((task) => (
                                            <div
                                                key={task.id}
                                                className="flex items-center justify-between p-3 rounded-lg border bg-card"
                                            >
                                                <div className="flex items-center gap-4">
                                                    <div className={`w-3 h-3 rounded-full ${
                                                        task.status === "running" ? "bg-green-500 animate-pulse" : "bg-blue-500"
                                                    }`} />
                                                    <div className="text-sm">
                                                        <span className="font-medium">{task.date}</span> at{" "}
                                                        <span className="font-medium">{task.time}</span> ({task.duration} min)
                                                    </div>
                                                </div>
                                                <Button
                                                    onClick={() => handleDeleteTask(task.id)}
                                                    size="sm"
                                                    variant="outline"
                                                    className="text-red-600 hover:text-red-700"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </Card>

                {/* Water Cut Management */}
                <Card className="p-6 border-border bg-card">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <Calendar className="h-6 w-6 text-primary" />
                            <h3 className="text-xl font-semibold text-foreground">Municipal Water Cut Policy</h3>
                        </div>
                        <Button
                            className="flex items-center gap-2"
                            onClick={() => setShowWaterCutForm(!showWaterCutForm)}
                        >
                            <Plus className="h-4 w-4" />
                            Schedule Water Cut
                        </Button>
                    </div>

                    {showWaterCutForm && (
                        <div className="mb-6 p-4 bg-muted/30 rounded-lg border">
                            <h4 className="text-md font-semibold mb-4">Declare Municipal Water Cut</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="area">Area / Sector</Label>
                                    <Input
                                        id="area"
                                        placeholder="Sector C"
                                        value={newWaterCut.area}
                                        onChange={(e) => setNewWaterCut({ ...newWaterCut, area: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="reason">Reason</Label>
                                    <Input
                                        id="reason"
                                        placeholder="Municipal Pipeline Maintenance"
                                        value={newWaterCut.reason}
                                        onChange={(e) => setNewWaterCut({ ...newWaterCut, reason: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="startTime">Start Time</Label>
                                    <Input
                                        id="startTime"
                                        type="time"
                                        value={newWaterCut.startTime}
                                        onChange={(e) => setNewWaterCut({ ...newWaterCut, startTime: e.target.value })}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="endTime">End Time</Label>
                                    <Input
                                        id="endTime"
                                        type="time"
                                        value={newWaterCut.endTime}
                                        onChange={(e) => setNewWaterCut({ ...newWaterCut, endTime: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="flex justify-end mt-4 gap-2">
                                <Button variant="outline" onClick={() => setShowWaterCutForm(false)}>
                                    Cancel
                                </Button>
                                <Button
                                    onClick={() => {
                                        if (!newWaterCut.area) return;
                                        fetch("/api/water-cuts", {
                                            method: "POST",
                                            headers: { "Content-Type": "application/json" },
                                            body: JSON.stringify(newWaterCut)
                                        })
                                            .then(res => res.json())
                                            .then(data => {
                                                if (data.ok) {
                                                    setWaterCuts(prev => [...prev, {
                                                        id: data.id || Date.now(),
                                                        ...newWaterCut,
                                                        status: "scheduled"
                                                    }]);
                                                    setShowWaterCutForm(false);
                                                    toast({
                                                        title: "Water Cut Added",
                                                        description: `Water cut scheduled for ${newWaterCut.area}`
                                                    });
                                                }
                                            })
                                            .catch(() => {});
                                    }}
                                >
                                    Save Schedule
                                </Button>
                            </div>
                        </div>
                    )}

                    <div className="space-y-3">
                        {waterCuts.map((cut) => (
                            <Card key={cut.id} className="p-4 border bg-card flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="h-3 w-3 rounded-full bg-amber-500" />
                                    <div>
                                        <p className="font-semibold text-sm">{cut.area}</p>
                                        <p className="text-xs text-muted-foreground">{cut.startTime} – {cut.endTime} • {cut.reason}</p>
                                    </div>
                                </div>
                                <Button
                                    onClick={() => handleDeleteWaterCut(cut.id)}
                                    variant="outline"
                                    size="sm"
                                    className="text-red-600 hover:text-red-700"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            </Card>
                        ))}
                    </div>
                </Card>

                {/* Festival & Holiday Pump Policy */}
                <FestivalPolicySection />
            </div>
        </div>
    );
}

export default AdminDashboard;
import { useState, useEffect, useMemo, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
    Calendar as CalendarIcon,
    Clock,
    Sparkles,
    ChevronLeft,
    ChevronRight,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Shield,
    Play,
    RotateCcw,
    RefreshCw,
    Sliders,
    Info,
    Check
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface FestivalRecord {
    year: number;
    date_str: string;
    display_date: string;
    name: string;
    type: string;
    policy: "RANG_PANCHAMI" | "NORMAL" | string;
    release_time?: string | null;
    release_hour?: number | null;
    release_minute?: number | null;
    is_special_policy: boolean;
    description: string;
}

interface FestivalStatusPayload {
    ok: boolean;
    festival_mode: boolean;
    today_is_festival: boolean;
    festival_name: string;
    festival_date?: string | null;
    policy: string;
    automatic_start_allowed: boolean;
    automatic_start_blocked: boolean;
    release_time?: string | null;
    status: "RESTRICTED" | "RELEASED" | "NORMAL" | "MODE_OFF" | string;
    reason: string;
    timezone: string;
    current_time_ist: string;
    release_countdown_text?: string | null;
    seconds_until_release?: number | null;
    config?: {
        festival_mode: boolean;
        selected_festival: string;
        updated_at?: string | null;
    };
    today_festival?: FestivalRecord | null;
}

interface SimulationResult {
    simulated: boolean;
    simulated_datetime_ist: string;
    festival_mode: boolean;
    today_is_festival: boolean;
    festival_name: string;
    festival_date: string;
    policy: string;
    automatic_start_allowed: boolean;
    automatic_start_blocked: boolean;
    release_time?: string | null;
    status: string;
    reason: string;
    timezone: string;
    current_time_ist: string;
    release_countdown_text?: string | null;
    seconds_until_release?: number | null;
}

export const FestivalPolicySection = () => {
    const { toast } = useToast();

    // State
    const [status, setStatus] = useState<FestivalStatusPayload | null>(null);
    const [loading, setLoading] = useState(true);
    const [updatingMode, setUpdatingMode] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Calendar state
    const [currentMonth, setCurrentMonth] = useState(() => new Date(2026, 2, 1)); // Default: March 2026
    const [monthFestivals, setMonthFestivals] = useState<FestivalRecord[]>([]);
    const [loadingMonth, setLoadingMonth] = useState(false);

    // Selected festival / date
    const [selectedDateStr, setSelectedDateStr] = useState<string>("2026-03-08");
    const [selectedFestival, setSelectedFestival] = useState<FestivalRecord | null>(null);

    // Upcoming festivals
    const [upcomingFestivals, setUpcomingFestivals] = useState<FestivalRecord[]>([]);

    // Simulation tool state
    const [simDate, setSimDate] = useState("2026-03-08");
    const [simTime, setSimTime] = useState("18:59:00");
    const [simFestival, setSimFestival] = useState("Rang Panchami");
    const [simMode, setSimMode] = useState(true);
    const [simulating, setSimulating] = useState(false);
    const [simResult, setSimResult] = useState<SimulationResult | null>(null);

    // Fetch primary festival status
    const fetchFestivalStatus = useCallback(async () => {
        try {
            const res = await fetch("/api/festival/status");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data: FestivalStatusPayload = await res.json();
            if (data.ok) {
                setStatus(data);
                setError(null);
            }
        } catch (err: any) {
            setError(err.message || "Failed to reach festival service");
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch month calendar festivals
    const fetchMonthFestivals = useCallback(async (year: number, month: number) => {
        setLoadingMonth(true);
        try {
            const res = await fetch(`/api/festivals/calendar?year=${year}&month=${month}`);
            if (res.ok) {
                const data = await res.json();
                if (data.ok) {
                    setMonthFestivals(data.festivals || []);
                }
            }
        } catch (err) {
            console.error("Calendar fetch error:", err);
        } finally {
            setLoadingMonth(false);
        }
    }, []);

    // Fetch upcoming festivals
    const fetchUpcoming = useCallback(async () => {
        try {
            const res = await fetch("/api/festivals/upcoming?limit=8");
            if (res.ok) {
                const data = await res.json();
                if (data.ok) {
                    setUpcomingFestivals(data.upcoming || []);
                }
            }
        } catch (err) {
            console.error("Upcoming fetch error:", err);
        }
    }, []);

    // Initial load and periodic refresh
    useEffect(() => {
        fetchFestivalStatus();
        fetchUpcoming();
        const interval = setInterval(fetchFestivalStatus, 3000);
        return () => clearInterval(interval);
    }, [fetchFestivalStatus, fetchUpcoming]);

    // Load month festivals on month change
    useEffect(() => {
        const y = currentMonth.getFullYear();
        const m = currentMonth.getMonth() + 1;
        fetchMonthFestivals(y, m);
    }, [currentMonth, fetchMonthFestivals]);

    // Update selected festival when month festivals change or date picked
    useEffect(() => {
        if (!selectedDateStr) return;
        const match = monthFestivals.find((f) => f.date_str === selectedDateStr);
        if (match) {
            setSelectedFestival(match);
        } else if (selectedDateStr === "2026-03-08") {
            // Fallback for default Rang Panchami
            setSelectedFestival({
                year: 2026,
                date_str: "2026-03-08",
                display_date: "08 March 2026",
                name: "Rang Panchami",
                type: "Hindu",
                policy: "RANG_PANCHAMI",
                release_time: "19:00",
                release_hour: 19,
                release_minute: 0,
                is_special_policy: true,
                description: "Rang Panchami special water management policy: Automated start restricted until 07:00 PM IST."
            });
        }
    }, [selectedDateStr, monthFestivals]);

    // Toggle Festival Mode
    const handleToggleMode = async (enabled: boolean) => {
        setUpdatingMode(true);
        try {
            const res = await fetch("/api/festival/mode", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ enabled })
            });
            const data = await res.json();
            if (data.ok) {
                toast({
                    title: `Festival Mode ${enabled ? "Enabled 🟢" : "Disabled ⚪"}`,
                    description: enabled
                        ? "Festival policies and restrictions will be evaluated."
                        : "Festival restrictions bypassed. Safety guards remain 100% active."
                });
                fetchFestivalStatus();
            }
        } catch (err) {
            toast({
                title: "Update Failed",
                description: "Could not update festival mode.",
                variant: "destructive"
            });
        } finally {
            setUpdatingMode(false);
        }
    };

    // Run Simulation
    const handleRunSimulation = async (customTime?: string) => {
        const timeToTest = customTime || simTime;
        setSimulating(true);
        try {
            const res = await fetch("/api/festival/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    sim_date: simDate,
                    sim_time: timeToTest,
                    festival_name: simFestival,
                    festival_mode: simMode,
                    pump_is_on: false
                })
            });
            const data = await res.json();
            if (data.ok && data.result) {
                setSimResult(data.result);
                toast({
                    title: `Simulation Executed (${timeToTest} IST)`,
                    description: data.result.automatic_start_blocked
                        ? "🔴 AUTOMATIC START: BLOCKED"
                        : "🟢 AUTOMATIC START: ALLOWED"
                });
            }
        } catch (err) {
            toast({
                title: "Simulation Failed",
                description: "Error communicating with simulation endpoint.",
                variant: "destructive"
            });
        } finally {
            setSimulating(false);
        }
    };

    // Calendar navigation
    const handlePrevMonth = () => {
        setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
    };

    const handleNextMonth = () => {
        setCurrentMonth(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
    };

    // Calendar grid calculations
    const calendarDays = useMemo(() => {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth(); // 0-indexed
        const firstDayOfMonth = new Date(year, month, 1);
        const lastDayOfMonth = new Date(year, month + 1, 0);

        // Day of week: 0 = Sun, 1 = Mon ... adjust to Mon = 0
        let startingDayIndex = firstDayOfMonth.getDay() - 1;
        if (startingDayIndex === -1) startingDayIndex = 6;

        const totalDays = lastDayOfMonth.getDate();
        const days = [];

        // Padding before
        for (let i = 0; i < startingDayIndex; i++) {
            days.push({ dayNumber: null, dateStr: null, festival: null });
        }

        // Days of current month
        for (let d = 1; d <= totalDays; d++) {
            const mm = String(month + 1).padStart(2, "0");
            const dd = String(d).padStart(2, "0");
            const dateStr = `${year}-${mm}-${dd}`;
            const fest = monthFestivals.find((f) => f.date_str === dateStr);
            days.push({ dayNumber: d, dateStr, festival: fest });
        }

        return days;
    }, [currentMonth, monthFestivals]);

    const monthLabel = currentMonth.toLocaleDateString("en-US", { month: "long", year: "numeric" });

    return (
        <Card className="p-6 border-border bg-card shadow-sm space-y-6">
            {/* Header with Title & Festival Mode Toggle */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
                <div className="flex items-start gap-3">
                    <div className="p-2.5 rounded-xl bg-primary/10 text-primary mt-0.5">
                        <Sparkles className="h-6 w-6" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
                            🎉 Festival & Holiday Pump Policy
                        </h3>
                        <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                            Deterministic, festival-aware automatic pump operation and evening release management
                        </p>
                    </div>
                </div>

                {/* Real Festival Mode Toggle */}
                <div className="flex items-center gap-3 bg-muted/40 p-2.5 px-4 rounded-xl border border-border">
                    <div className="text-right">
                        <Label htmlFor="festival-mode-toggle" className="text-xs font-semibold cursor-pointer block">
                            Festival Mode
                        </Label>
                        <span className="text-[11px] text-muted-foreground block">
                            {status?.festival_mode ? "Enforcing Policies" : "Bypassed"}
                        </span>
                    </div>
                    <Switch
                        id="festival-mode-toggle"
                        checked={status?.festival_mode ?? true}
                        disabled={updatingMode || loading}
                        onCheckedChange={handleToggleMode}
                    />
                    <Badge variant={status?.festival_mode ? "default" : "secondary"} className="font-mono text-[11px]">
                        {status?.festival_mode ? "ON" : "OFF"}
                    </Badge>
                </div>
            </div>

            {/* Error banner if backend disconnects */}
            {error && (
                <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-3 text-destructive text-sm">
                    <AlertTriangle className="h-5 w-5 shrink-0" />
                    <span>Festival policy service unavailable: {error}. Backend connection lost.</span>
                </div>
            )}

            {/* Top Grid: Today's Festival Status & Active Policy Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 1. Today's Festival Card */}
                <Card className="p-5 border border-border bg-muted/20 relative overflow-hidden flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                <Clock className="h-3.5 w-3.5" />
                                Today's Operational Status
                            </span>
                            <Badge variant="outline" className="text-[11px] font-mono border-primary/30 text-primary">
                                Asia/Kolkata (IST)
                            </Badge>
                        </div>

                        {loading ? (
                            <div className="py-8 text-center text-sm text-muted-foreground flex items-center justify-center gap-2">
                                <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                                Checking festival status...
                            </div>
                        ) : status?.today_is_festival ? (
                            <div className="space-y-3">
                                <div>
                                    <h4 className="text-2xl font-extrabold text-foreground tracking-tight">
                                        {status.festival_name}
                                    </h4>
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                        Festival Date: {status.festival_date || "Today"} • Current IST: {status.current_time_ist}
                                    </p>
                                </div>

                                <div className="grid grid-cols-2 gap-3 pt-2">
                                    <div className="p-3 rounded-lg bg-card border border-border">
                                        <p className="text-[11px] font-medium text-muted-foreground uppercase">Automatic Start</p>
                                        <div className="flex items-center gap-1.5 mt-1 font-bold text-sm">
                                            {status.automatic_start_blocked ? (
                                                <span className="text-red-500 flex items-center gap-1">
                                                    <XCircle className="h-4 w-4" /> BLOCKED
                                                </span>
                                            ) : (
                                                <span className="text-emerald-500 flex items-center gap-1">
                                                    <CheckCircle2 className="h-4 w-4" /> ALLOWED
                                                </span>
                                            )}
                                        </div>
                                    </div>

                                    <div className="p-3 rounded-lg bg-card border border-border">
                                        <p className="text-[11px] font-medium text-muted-foreground uppercase">Release Time</p>
                                        <p className="text-sm font-bold text-foreground mt-1">
                                            {status.release_time ? `${status.release_time} IST` : "Immediate"}
                                        </p>
                                    </div>
                                </div>

                                {/* Status banner */}
                                <div className={`p-3 rounded-lg border text-xs leading-relaxed flex items-start gap-2.5 ${
                                    status.status === "RESTRICTED"
                                        ? "bg-amber-500/10 border-amber-500/30 text-amber-800 dark:text-amber-300"
                                        : "bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-300"
                                }`}>
                                    <Shield className="h-4 w-4 shrink-0 mt-0.5" />
                                    <div>
                                        <span className="font-semibold uppercase tracking-wide">
                                            {status.status === "RESTRICTED" ? "ACTIVE RESTRICTION" : "RESTRICTION RELEASED"}:
                                        </span>{" "}
                                        {status.reason}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="py-4 space-y-2">
                                <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold text-base">
                                    <CheckCircle2 className="h-5 w-5" />
                                    No Festival Restrictions Active Today
                                </div>
                                <p className="text-xs text-muted-foreground leading-relaxed">
                                    Normal automatic schedule and closed-loop hysteresis pumping are fully active.
                                    Festival mode is currently{" "}
                                    <span className="font-semibold text-foreground">
                                        {status?.festival_mode ? "ENABLED (Standing by)" : "DISABLED"}
                                    </span>
                                    .
                                </p>
                                <div className="mt-3 inline-flex items-center gap-2 p-2 px-3 rounded-md bg-card border border-border text-xs text-muted-foreground">
                                    <Clock className="h-3.5 w-3.5 text-primary" />
                                    System Time (IST): <span className="font-mono text-foreground font-semibold">{status?.current_time_ist || "--:--:--"}</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Live countdown footer for Rang Panchami restriction */}
                    {status?.today_is_festival && status.policy === "RANG_PANCHAMI" && status.automatic_start_blocked && (
                        <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs">
                            <span className="text-muted-foreground flex items-center gap-1.5">
                                <Clock className="h-3.5 w-3.5 text-amber-500 animate-pulse" />
                                Release in:
                            </span>
                            <span className="font-mono font-bold text-amber-600 dark:text-amber-400 text-sm">
                                {status.release_countdown_text || "Approaching 19:00 IST"}
                            </span>
                        </div>
                    )}
                </Card>

                {/* 2. Selected Festival / Policy Inspector Card */}
                <Card className="p-5 border border-border bg-card flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                                <Sliders className="h-3.5 w-3.5 text-primary" />
                                Festival Policy Inspector
                            </span>
                            {selectedFestival?.is_special_policy ? (
                                <Badge variant="destructive" className="text-[10px] font-semibold">
                                    SPECIAL RESTRICTION
                                </Badge>
                            ) : (
                                <Badge variant="secondary" className="text-[10px] font-semibold">
                                    STANDARD POLICY
                                </Badge>
                            )}
                        </div>

                        <div className="space-y-3">
                            <div>
                                <h4 className="text-xl font-bold text-foreground">
                                    {selectedFestival ? selectedFestival.name : "Select a festival from calendar"}
                                </h4>
                                <p className="text-xs text-muted-foreground">
                                    {selectedFestival?.display_date} • Category: {selectedFestival?.type}
                                </p>
                            </div>

                            <div className="p-3 bg-muted/30 rounded-lg border border-border space-y-2 text-xs">
                                <div className="flex justify-between items-center">
                                    <span className="text-muted-foreground">Policy Identifier:</span>
                                    <span className="font-mono font-bold text-foreground">
                                        {selectedFestival?.policy || "RANG_PANCHAMI"}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-muted-foreground">Automatic Start:</span>
                                    <span className={`font-semibold ${selectedFestival?.is_special_policy ? "text-amber-600" : "text-emerald-600"}`}>
                                        {selectedFestival?.is_special_policy ? "Restricted before 19:00 IST" : "Allowed (Normal)"}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-muted-foreground">Evening Release Window:</span>
                                    <span className="font-mono text-foreground font-semibold">
                                        {selectedFestival?.release_time ? `${selectedFestival.release_time} IST (07:00 PM)` : "No restriction"}
                                    </span>
                                </div>
                            </div>

                            <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                                {selectedFestival?.description}
                            </p>
                        </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
                        <span className="flex items-center gap-1">
                            <Info className="h-3 w-3 text-primary" /> Click any date on the calendar below to inspect
                        </span>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs text-primary"
                            onClick={() => {
                                setSelectedDateStr("2026-03-08");
                                setSimDate("2026-03-08");
                                setSimFestival("Rang Panchami");
                            }}
                        >
                            Select Rang Panchami
                        </Button>
                    </div>
                </Card>
            </div>

            {/* Middle Section: Calendar & Upcoming Festivals */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Interactive Calendar (2 cols) */}
                <Card className="p-5 border border-border bg-card lg:col-span-2 space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <CalendarIcon className="h-5 w-5 text-primary" />
                            <h4 className="text-base font-bold text-foreground">Festival Calendar</h4>
                            <span className="text-xs text-muted-foreground">({monthLabel})</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={handlePrevMonth}>
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={handleNextMonth}>
                                <ChevronRight className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>

                    {/* Day Headers */}
                    <div className="grid grid-cols-7 gap-1 text-center font-semibold text-xs text-muted-foreground pb-1 border-b">
                        <span>Mon</span>
                        <span>Tue</span>
                        <span>Wed</span>
                        <span>Thu</span>
                        <span>Fri</span>
                        <span>Sat</span>
                        <span>Sun</span>
                    </div>

                    {/* Days Grid */}
                    {loadingMonth ? (
                        <div className="h-48 flex items-center justify-center text-xs text-muted-foreground">
                            <RefreshCw className="h-4 w-4 animate-spin text-primary mr-2" /> Loading calendar dates...
                        </div>
                    ) : (
                        <div className="grid grid-cols-7 gap-1.5 text-xs">
                            {calendarDays.map((item, idx) => {
                                if (!item.dayNumber) {
                                    return <div key={`empty-${idx}`} className="h-14 rounded-lg bg-muted/10" />;
                                }

                                const isSelected = item.dateStr === selectedDateStr;
                                const isRangPanchami = item.festival?.policy === "RANG_PANCHAMI";
                                const hasFestival = Boolean(item.festival);

                                return (
                                    <button
                                        key={item.dateStr}
                                        type="button"
                                        onClick={() => {
                                            if (item.dateStr) {
                                                setSelectedDateStr(item.dateStr);
                                                setSimDate(item.dateStr);
                                                if (item.festival) {
                                                    setSimFestival(item.festival.name);
                                                }
                                            }
                                        }}
                                        className={`h-14 p-1.5 rounded-lg border text-left flex flex-col justify-between transition-all duration-150 relative ${
                                            isSelected
                                                ? "border-primary ring-2 ring-primary/20 bg-primary/5"
                                                : "border-border hover:bg-muted/40 bg-card"
                                        }`}
                                    >
                                        <div className="flex items-center justify-between w-full">
                                            <span className={`font-mono text-xs ${isSelected ? "font-bold text-primary" : "text-foreground"}`}>
                                                {item.dayNumber}
                                            </span>
                                            {isRangPanchami && (
                                                <span className="text-[10px]" title="Rang Panchami Special Restriction">🎉</span>
                                            )}
                                        </div>

                                        {hasFestival ? (
                                            <div className="w-full">
                                                <div
                                                    className={`truncate text-[9px] px-1 py-0.5 rounded font-medium ${
                                                        isRangPanchami
                                                            ? "bg-red-500/15 text-red-700 dark:text-red-300 font-bold"
                                                            : "bg-primary/10 text-primary"
                                                    }`}
                                                    title={item.festival?.name}
                                                >
                                                    {item.festival?.name}
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="h-2" />
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    )}

                    <div className="flex items-center justify-between pt-2 text-[11px] text-muted-foreground border-t border-border">
                        <div className="flex items-center gap-4">
                            <span className="flex items-center gap-1.5">
                                <span className="h-2.5 w-2.5 rounded-full bg-red-500" /> Special Policy (Rang Panchami)
                            </span>
                            <span className="flex items-center gap-1.5">
                                <span className="h-2.5 w-2.5 rounded-full bg-primary" /> Normal Holiday
                            </span>
                        </div>
                        <span>Click date to test policy</span>
                    </div>
                </Card>

                {/* Upcoming Festivals List (1 col) */}
                <Card className="p-5 border border-border bg-card space-y-4 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="text-base font-bold text-foreground flex items-center gap-2">
                                <Sparkles className="h-4 w-4 text-primary" /> Upcoming Festivals
                            </h4>
                            <Badge variant="outline" className="text-[10px]">Verified Dataset</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mb-3">
                            Chronological schedule loaded from <code className="text-[11px] font-mono">Holidays_2020_2030.csv</code>
                        </p>

                        <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
                            {upcomingFestivals.map((fest, idx) => (
                                <div
                                    key={`${fest.date_str}-${idx}`}
                                    onClick={() => {
                                        setSelectedDateStr(fest.date_str);
                                        setSelectedFestival(fest);
                                        setSimDate(fest.date_str);
                                        setSimFestival(fest.name);
                                    }}
                                    className="p-2.5 rounded-lg border border-border bg-muted/20 hover:bg-muted/50 cursor-pointer transition-colors flex items-center justify-between text-xs"
                                >
                                    <div>
                                        <p className="font-semibold text-foreground flex items-center gap-1">
                                            {fest.is_special_policy ? "🎉" : "•"} {fest.name}
                                        </p>
                                        <p className="text-[11px] text-muted-foreground">{fest.display_date}</p>
                                    </div>
                                    <Badge
                                        variant={fest.is_special_policy ? "destructive" : "secondary"}
                                        className="text-[9px] font-mono"
                                    >
                                        {fest.policy}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="pt-3 border-t border-border text-[11px] text-muted-foreground text-center">
                        Total holidays in database: 1,163 (2020–2030)
                    </div>
                </Card>
            </div>

            {/* Bottom Tool: Safe Policy Simulation & Boundary Verification */}
            <Card className="p-5 border border-border bg-muted/10 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
                    <div className="flex items-center gap-2">
                        <Sliders className="h-5 w-5 text-primary" />
                        <div>
                            <h4 className="text-base font-bold text-foreground">
                                Festival Policy Simulation & Boundary Verification
                            </h4>
                            <p className="text-xs text-muted-foreground">
                                Test exact time boundaries (18:59:59 blocked vs 19:00:00 released) in-memory without physical relay triggers
                            </p>
                        </div>
                    </div>
                    <Badge variant="outline" className="font-mono text-xs w-fit">
                        Safe In-Memory Simulator
                    </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="space-y-1.5">
                        <Label htmlFor="sim-festival" className="text-xs">Festival Name</Label>
                        <Input
                            id="sim-festival"
                            value={simFestival}
                            onChange={(e) => setSimFestival(e.target.value)}
                            className="h-9 text-xs"
                        />
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="sim-date" className="text-xs">Simulated Date (YYYY-MM-DD)</Label>
                        <Input
                            id="sim-date"
                            value={simDate}
                            onChange={(e) => setSimDate(e.target.value)}
                            className="h-9 text-xs font-mono"
                        />
                    </div>

                    <div className="space-y-1.5">
                        <Label htmlFor="sim-time" className="text-xs">Simulated Time IST (HH:MM:SS)</Label>
                        <Input
                            id="sim-time"
                            value={simTime}
                            onChange={(e) => setSimTime(e.target.value)}
                            className="h-9 text-xs font-mono"
                        />
                    </div>

                    <div className="flex items-end gap-2">
                        <Button
                            onClick={() => handleRunSimulation()}
                            disabled={simulating}
                            className="w-full h-9 text-xs flex items-center justify-center gap-1.5"
                        >
                            {simulating ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                            Test Policy
                        </Button>
                    </div>
                </div>

                {/* Quick Test Boundary Buttons */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                    <span className="text-muted-foreground text-[11px] font-medium mr-1">Quick Presets:</span>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs border-red-200 hover:bg-red-50 text-red-700 dark:border-red-800 dark:text-red-300"
                        onClick={() => {
                            setSimDate("2026-03-08");
                            setSimTime("18:59:59");
                            setSimFestival("Rang Panchami");
                            handleRunSimulation("18:59:59");
                        }}
                    >
                        🔴 18:59:59 IST (Blocked)
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs border-emerald-200 hover:bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:text-emerald-300"
                        onClick={() => {
                            setSimDate("2026-03-08");
                            setSimTime("19:00:00");
                            setSimFestival("Rang Panchami");
                            handleRunSimulation("19:00:00");
                        }}
                    >
                        🟢 19:00:00 IST (Released)
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs border-emerald-200 hover:bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:text-emerald-300"
                        onClick={() => {
                            setSimDate("2026-03-08");
                            setSimTime("19:05:00");
                            setSimFestival("Rang Panchami");
                            handleRunSimulation("19:05:00");
                        }}
                    >
                        🟢 19:05:00 IST (Allowed)
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => {
                            setSimDate("2026-11-08");
                            setSimTime("12:00:00");
                            setSimFestival("Diwali");
                            handleRunSimulation("12:00:00");
                        }}
                    >
                        Diwali (Normal Day)
                    </Button>
                </div>

                {/* Simulation Output Card */}
                {simResult && (
                    <div className={`p-4 rounded-xl border mt-3 transition-all ${
                        simResult.automatic_start_blocked
                            ? "bg-red-500/10 border-red-500/30 text-red-900 dark:text-red-200"
                            : "bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200"
                    }`}>
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2 pb-2 border-b border-current/20">
                            <div className="flex items-center gap-2">
                                {simResult.automatic_start_blocked ? (
                                    <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                                ) : (
                                    <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                                )}
                                <span className="font-extrabold text-sm uppercase tracking-wide">
                                    Simulation Result: AUTOMATIC START {simResult.automatic_start_blocked ? "BLOCKED 🔴" : "ALLOWED 🟢"}
                                </span>
                            </div>
                            <span className="font-mono text-xs">
                                Tested at {simResult.current_time_ist} IST • {simResult.festival_date}
                            </span>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-2">
                            <div>
                                <span className="opacity-75 block text-[10px]">Festival:</span>
                                <span className="font-bold">{simResult.festival_name}</span>
                            </div>
                            <div>
                                <span className="opacity-75 block text-[10px]">Policy:</span>
                                <span className="font-mono font-bold">{simResult.policy}</span>
                            </div>
                            <div>
                                <span className="opacity-75 block text-[10px]">Policy Status:</span>
                                <span className="font-bold">{simResult.status}</span>
                            </div>
                            <div>
                                <span className="opacity-75 block text-[10px]">Release Time:</span>
                                <span className="font-mono font-bold">{simResult.release_time || "None"}</span>
                            </div>
                        </div>

                        <p className="text-xs opacity-90 leading-relaxed font-medium">
                            <span className="font-bold">Evaluation Reason:</span> {simResult.reason}
                        </p>
                    </div>
                )}
            </Card>
        </Card>
    );
};

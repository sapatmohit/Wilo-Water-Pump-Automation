import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { User, LogIn, LogOut, ShieldCheck, UserPlus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

interface UserProfile {
  username: string;
  role: string;
}

interface AuthIndicatorProps {
  className?: string;
}

export function AuthIndicator({ className }: AuthIndicatorProps = {}) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("wilo_token");
    if (!token) return;

    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok && data.user) {
          setUser(data.user);
        } else {
          localStorage.removeItem("wilo_token");
        }
      })
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast({
        title: "Validation error",
        description: "Please enter both username and password.",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    const endpoint = isRegisterMode ? "/api/auth/register" : "/api/auth/login";

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();

      if (!res.ok || !data.ok) {
        toast({
          title: isRegisterMode ? "Registration failed" : "Login failed",
          description: data.error || "Please check your credentials.",
          variant: "destructive",
        });
        return;
      }

      if (isRegisterMode) {
        toast({
          title: "Registration successful",
          description: "Account created! Now logging you in...",
        });
        // Auto-login after registration
        const loginRes = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        const loginData = await loginRes.json();
        if (loginData.ok && loginData.token) {
          localStorage.setItem("wilo_token", loginData.token);
          setUser(loginData.user);
          setOpen(false);
          setUsername("");
          setPassword("");
        }
      } else {
        localStorage.setItem("wilo_token", data.token);
        setUser(data.user);
        toast({
          title: "Welcome back!",
          description: `Logged in as ${data.user.username} (${data.user.role}).`,
        });
        setOpen(false);
        setUsername("");
        setPassword("");
      }
    } catch (err) {
      toast({
        title: "Network error",
        description: "Failed to communicate with authentication service.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    const token = localStorage.getItem("wilo_token");
    if (token) {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {}
    }
    localStorage.removeItem("wilo_token");
    setUser(null);
    toast({
      title: "Logged out",
      description: "You have been securely signed out.",
    });
  };

  if (user) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 bg-white text-slate-800 border border-white/40 px-3 h-9 rounded-md text-xs font-medium shadow-sm",
          className
        )}
      >
        <ShieldCheck className="h-4 w-4 text-primary shrink-0" />
        <span className="font-semibold text-slate-900">{user.username}</span>
        <Badge variant="outline" className="text-[10px] px-1.5 py-0 capitalize bg-slate-100 text-slate-700 border-slate-300">
          {user.role}
        </Badge>
        <button
          onClick={handleLogout}
          title="Sign out"
          className="ml-1 text-slate-500 hover:text-destructive transition-colors p-0.5 rounded hover:bg-slate-100"
        >
          <LogOut className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "flex items-center gap-2 text-xs font-medium h-9 px-3.5 bg-white text-slate-800 border-white/40 hover:bg-slate-50 hover:text-primary shadow-sm transition-colors",
            className
          )}
        >
          <LogIn className="h-3.5 w-3.5 text-primary shrink-0" />
          <span>Operator Login</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="h-5 w-5 text-primary" />
            {isRegisterMode ? "Register Operator" : "Operator Authentication"}
          </DialogTitle>
          <DialogDescription>
            {isRegisterMode
              ? "Create a new operator account for SCADA operations."
              : "Sign in to authenticate telemetry and pump control actions."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="auth-username">Username</Label>
            <Input
              id="auth-username"
              placeholder="operator or admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="auth-password">Password</Label>
            <Input
              id="auth-password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={isRegisterMode ? "new-password" : "current-password"}
              required
            />
          </div>

          <div className="text-[11px] text-muted-foreground bg-muted p-2 rounded-md">
            Default credentials: <code className="text-primary font-mono">operator / operator123</code> or{" "}
            <code className="text-primary font-mono">admin / admin123</code>
          </div>

          <div className="flex items-center justify-between pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => setIsRegisterMode(!isRegisterMode)}
            >
              {isRegisterMode ? "Have an account? Login" : "New operator? Register"}
            </Button>
            <Button type="submit" disabled={loading} size="sm">
              {loading ? (
                "Processing..."
              ) : isRegisterMode ? (
                <span className="flex items-center gap-1.5">
                  <UserPlus className="h-3.5 w-3.5" /> Register
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <LogIn className="h-3.5 w-3.5" /> Sign In
                </span>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

"""
Central Festival & Holiday Policy Engine
========================================
Authoritative policy layer for the Wilo AI Water Transfer System.
Evaluates festival-aware pump automation policies strictly in the
Asia/Kolkata (IST) timezone.

Hierarchy:
  Emergency Stop (P0)
      ↓
  Manual Override (P1)
      ↓
  Deterministic Festival Policy (P2)
      ↓
  Municipal Water Cut Policy (P3)
      ↓
  Tank / Electrical Logic (P4)
      ↓
  Hardware Safety Guards (P5)
      ↓
  Final Pump Relay Action
"""

from __future__ import annotations

import os
import csv
import json
import logging
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List, Optional, Any

logger = logging.getLogger('wilo.festival')

IST = ZoneInfo('Asia/Kolkata')

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
HOLIDAY_CSV_PATH = os.path.join(_ROOT, 'data', 'raw', 'Holidays_2020_2030.csv')
CONFIG_PATH = os.path.join(_ROOT, 'data', 'festival_config.json')


class FestivalPolicyType:
    NORMAL = "NORMAL"
    RANG_PANCHAMI = "RANG_PANCHAMI"
    CUSTOM_RESTRICTION = "CUSTOM_RESTRICTION"


DEFAULT_CONFIG = {
    "festival_mode": True,
    "selected_festival": "Rang Panchami",
    "updated_at": None,
}


# ── Configuration & Persistence ───────────────────────────────────────────────

def get_festival_config() -> dict:
    """Read persistent festival configuration from disk, returning defaults if missing."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    "festival_mode": bool(data.get("festival_mode", True)),
                    "selected_festival": str(data.get("selected_festival", "Rang Panchami")),
                    "updated_at": data.get("updated_at"),
                }
        except Exception as exc:
            logger.warning(f"Failed to read festival config ({exc}); using defaults")
    return dict(DEFAULT_CONFIG)


def save_festival_config(cfg: dict) -> dict:
    """Atomically save festival configuration to disk."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    payload = {
        "festival_mode": bool(cfg.get("festival_mode", True)),
        "selected_festival": str(cfg.get("selected_festival", "Rang Panchami")),
        "updated_at": datetime.now(IST).isoformat(),
    }
    tmp_path = f"{CONFIG_PATH}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, CONFIG_PATH)
    logger.info(f"Updated festival config: mode={payload['festival_mode']} selected={payload['selected_festival']}")
    return payload


def set_festival_mode(enabled: bool) -> dict:
    cfg = get_festival_config()
    cfg["festival_mode"] = enabled
    return save_festival_config(cfg)


def set_selected_festival(festival_name: str) -> dict:
    cfg = get_festival_config()
    cfg["selected_festival"] = festival_name
    return save_festival_config(cfg)


def reset_festival_config() -> dict:
    return save_festival_config(DEFAULT_CONFIG)


# ── Festival Dataset Loader ───────────────────────────────────────────────────

_FESTIVAL_CACHE: Optional[List[dict]] = None


def load_all_festivals(force_reload: bool = False) -> List[dict]:
    """
    Load and parse all holidays from CSV.
    Each record contains:
      - year (int)
      - date_str (YYYY-MM-DD)
      - display_date (e.g. '08 March 2026')
      - name (str)
      - type (str, e.g. 'Hindu', 'Govt')
      - policy (RANG_PANCHAMI | NORMAL)
      - release_time ('19:00' for Rang Panchami, or None)
      - release_hour (19 or None)
      - release_minute (0 or None)
      - is_special_policy (bool)
      - description (str)
    """
    global _FESTIVAL_CACHE
    if _FESTIVAL_CACHE is not None and not force_reload:
        return _FESTIVAL_CACHE

    records = []
    if not os.path.exists(HOLIDAY_CSV_PATH):
        logger.error(f"Holidays CSV not found at {HOLIDAY_CSV_PATH}")
        _FESTIVAL_CACHE = []
        return _FESTIVAL_CACHE

    try:
        with open(HOLIDAY_CSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) < 3:
                    continue
                year_str, raw_date, event_name = row[0].strip(), row[1].strip(), row[2].strip()
                event_type = row[3].strip() if len(row) > 3 else "General"

                dt_obj = None
                for fmt in ('%B %d, %Y, %A', '%B %d, %Y', '%Y-%m-%d'):
                    try:
                        dt_obj = datetime.strptime(raw_date, fmt)
                        break
                    except ValueError:
                        pass

                if dt_obj is None:
                    continue

                iso_date = dt_obj.strftime('%Y-%m-%d')
                display_date = dt_obj.strftime('%d %B %Y')

                name_lower = event_name.lower()
                is_rang_panchami = 'rang panchami' in name_lower

                if is_rang_panchami:
                    policy = FestivalPolicyType.RANG_PANCHAMI
                    release_time = "19:00"
                    release_hour = 19
                    release_minute = 0
                    is_special = True
                    desc = "Rang Panchami special water management policy: Automated start restricted until 07:00 PM IST."
                else:
                    policy = FestivalPolicyType.NORMAL
                    release_time = None
                    release_hour = None
                    release_minute = None
                    is_special = False
                    desc = f"Standard holiday schedule for {event_name}: Normal automated pump operations permitted."

                records.append({
                    "year": int(year_str) if year_str.isdigit() else dt_obj.year,
                    "date_str": iso_date,
                    "display_date": display_date,
                    "name": event_name,
                    "type": event_type,
                    "policy": policy,
                    "release_time": release_time,
                    "release_hour": release_hour,
                    "release_minute": release_minute,
                    "is_special_policy": is_special,
                    "description": desc,
                })

        records.sort(key=lambda r: r["date_str"])
        _FESTIVAL_CACHE = records
        logger.info(f"Loaded {len(records)} festival entries from {HOLIDAY_CSV_PATH}")
    except Exception as exc:
        logger.error(f"Error loading holiday records: {exc}")
        _FESTIVAL_CACHE = []

    return _FESTIVAL_CACHE


def get_festivals_for_date(target_date: date | datetime | str) -> List[dict]:
    """Find all festivals scheduled for a given date."""
    if isinstance(target_date, datetime):
        date_str = target_date.strftime('%Y-%m-%d')
    elif isinstance(target_date, date):
        date_str = target_date.strftime('%Y-%m-%d')
    else:
        date_str = str(target_date)[:10]

    all_festivals = load_all_festivals()
    return [f for f in all_festivals if f["date_str"] == date_str]


def _ensure_ist(dt: Optional[datetime] = None) -> datetime:
    """Normalize datetime to timezone-aware Asia/Kolkata."""
    if dt is None:
        return datetime.now(IST)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def get_today_festival(now_dt: Optional[datetime] = None) -> Optional[dict]:
    """
    Get today's festival in Asia/Kolkata.
    Prioritizes special policy festivals (e.g. Rang Panchami).
    """
    now_ist = _ensure_ist(now_dt)
    festivals = get_festivals_for_date(now_ist.date())
    if not festivals:
        return None

    for f in festivals:
        if f["is_special_policy"]:
            return f
    return festivals[0]


def get_upcoming_festivals(limit: int = 6, now_dt: Optional[datetime] = None) -> List[dict]:
    """Get the next upcoming festivals starting from today in Asia/Kolkata."""
    now_ist = _ensure_ist(now_dt)
    today_str = now_ist.strftime('%Y-%m-%d')
    all_festivals = load_all_festivals()

    upcoming = [f for f in all_festivals if f["date_str"] >= today_str]
    return upcoming[:limit]


def get_calendar_festivals(year: int, month: int) -> List[dict]:
    """Get all festivals for a specified year and month."""
    all_festivals = load_all_festivals()
    month_str = f"{year:04d}-{month:02d}"
    return [f for f in all_festivals if f["date_str"].startswith(month_str)]


# ── Core Policy Evaluation Engine ─────────────────────────────────────────────

def evaluate_festival_policy(
    dt: Optional[datetime] = None,
    festival_name: Optional[str] = None,
    festival_mode: Optional[bool] = None,
    pump_is_on: bool = False,
    override_date: Optional[str] = None,
) -> dict:
    """
    Authoritative festival policy evaluation.
    
    Returns:
      {
        "festival_mode": bool,
        "today_is_festival": bool,
        "festival_name": str,
        "festival_date": str,
        "policy": "RANG_PANCHAMI" | "NORMAL",
        "automatic_start_allowed": bool,
        "automatic_start_blocked": bool,
        "release_time": "19:00" | None,
        "status": "RESTRICTED" | "RELEASED" | "NORMAL" | "MODE_OFF",
        "reason": str,
        "timezone": "Asia/Kolkata",
        "current_time_ist": "HH:MM:SS",
        "release_countdown_text": str | None,
        "seconds_until_release": int | None,
        "running_pump_shutdown": bool, # Always False for festival policy
      }
    """
    now_ist = _ensure_ist(dt)
    current_time_str = now_ist.strftime('%H:%M:%S')

    cfg = get_festival_config()
    is_mode_on = cfg["festival_mode"] if festival_mode is None else bool(festival_mode)
    check_date_str = override_date or now_ist.strftime('%Y-%m-%d')

    active_festival = None
    if festival_name:
        all_festivals = load_all_festivals()
        for f in all_festivals:
            if f["name"].lower() == festival_name.lower():
                active_festival = f
                break
        if not active_festival:
            is_rp = "rang panchami" in festival_name.lower()
            active_festival = {
                "name": festival_name,
                "date_str": check_date_str,
                "display_date": check_date_str,
                "policy": FestivalPolicyType.RANG_PANCHAMI if is_rp else FestivalPolicyType.NORMAL,
                "release_time": "19:00" if is_rp else None,
                "release_hour": 19 if is_rp else None,
                "release_minute": 0 if is_rp else None,
                "is_special_policy": is_rp,
                "description": "Dynamic festival policy evaluation",
            }
    else:
        festivals = get_festivals_for_date(check_date_str)
        if festivals:
            active_festival = next((f for f in festivals if f["is_special_policy"]), festivals[0])

    today_is_festival = active_festival is not None
    active_name = active_festival["name"] if active_festival else "None"
    active_policy = active_festival["policy"] if active_festival else FestivalPolicyType.NORMAL
    fest_date = active_festival["date_str"] if active_festival else check_date_str

    # 1. Mode is OFF -> Bypass all restrictions
    if not is_mode_on:
        return {
            "festival_mode": False,
            "today_is_festival": today_is_festival,
            "festival_name": active_name,
            "festival_date": fest_date,
            "policy": active_policy,
            "automatic_start_allowed": True,
            "automatic_start_blocked": False,
            "release_time": active_festival.get("release_time") if active_festival else None,
            "status": "MODE_OFF",
            "reason": "Festival Mode is OFF (Restrictions bypassed; all safety guards remain active)",
            "timezone": "Asia/Kolkata",
            "current_time_ist": current_time_str,
            "release_countdown_text": None,
            "seconds_until_release": None,
            "running_pump_shutdown": False,
        }

    # 2. No festival today -> Normal automatic operation
    if not today_is_festival:
        return {
            "festival_mode": True,
            "today_is_festival": False,
            "festival_name": "None",
            "festival_date": fest_date,
            "policy": FestivalPolicyType.NORMAL,
            "automatic_start_allowed": True,
            "automatic_start_blocked": False,
            "release_time": None,
            "status": "NORMAL",
            "reason": "No festival scheduled today: standard automated operation permitted",
            "timezone": "Asia/Kolkata",
            "current_time_ist": current_time_str,
            "release_countdown_text": None,
            "seconds_until_release": None,
            "running_pump_shutdown": False,
        }

    # 3. Special Policy: RANG_PANCHAMI
    if active_policy == FestivalPolicyType.RANG_PANCHAMI:
        cutoff_time = time(19, 0, 0)
        now_time = now_ist.time()

        if now_time < cutoff_time:
            # BEFORE 19:00:00 IST -> RESTRICTED
            release_dt = datetime.combine(now_ist.date(), cutoff_time, tzinfo=IST)
            sec_rem = max(0, int((release_dt - now_ist).total_seconds()))
            hrs = sec_rem // 3600
            mins = (sec_rem % 3600) // 60
            countdown_str = f"{hrs:02d}h {mins:02d}m"

            if pump_is_on:
                # If pump is ALREADY running, do NOT shut it down! (Section 11)
                reason_str = (
                    "Rang Panchami restriction active: new automated start blocked; "
                    "running pump permitted to complete cycle safely until 07:00 PM IST"
                )
            else:
                reason_str = (
                    f"Rang Panchami automatic-start restriction active until 07:00 PM IST "
                    f"(release in {countdown_str})"
                )

            return {
                "festival_mode": True,
                "today_is_festival": True,
                "festival_name": active_name,
                "festival_date": fest_date,
                "policy": FestivalPolicyType.RANG_PANCHAMI,
                "automatic_start_allowed": False,
                "automatic_start_blocked": True,
                "release_time": "19:00",
                "status": "RESTRICTED",
                "reason": reason_str,
                "timezone": "Asia/Kolkata",
                "current_time_ist": current_time_str,
                "release_countdown_text": countdown_str,
                "seconds_until_release": sec_rem,
                "running_pump_shutdown": False,
            }
        else:
            # AT OR AFTER 19:00:00 IST -> RELEASED
            return {
                "festival_mode": True,
                "today_is_festival": True,
                "festival_name": active_name,
                "festival_date": fest_date,
                "policy": FestivalPolicyType.RANG_PANCHAMI,
                "automatic_start_allowed": True,
                "automatic_start_blocked": False,
                "release_time": "19:00",
                "status": "RELEASED",
                "reason": "Rang Panchami restriction released: evening automated operation permitted (past 07:00 PM IST)",
                "timezone": "Asia/Kolkata",
                "current_time_ist": current_time_str,
                "release_countdown_text": "Released",
                "seconds_until_release": 0,
                "running_pump_shutdown": False,
            }

    # 4. Standard / NORMAL festival
    return {
        "festival_mode": True,
        "today_is_festival": True,
        "festival_name": active_name,
        "festival_date": fest_date,
        "policy": active_policy,
        "automatic_start_allowed": True,
        "automatic_start_blocked": False,
        "release_time": None,
        "status": "NORMAL",
        "reason": f"Standard holiday policy for {active_name}: normal automatic operation allowed",
        "timezone": "Asia/Kolkata",
        "current_time_ist": current_time_str,
        "release_countdown_text": None,
        "seconds_until_release": None,
        "running_pump_shutdown": False,
    }


# ── Simulation Function ───────────────────────────────────────────────────────

def simulate_festival_policy(
    sim_date: str,
    sim_time: str,
    festival_name: str = "Rang Panchami",
    festival_mode: bool = True,
    pump_is_on: bool = False,
) -> dict:
    """
    Pure policy simulation tool.
    Allows testing time boundaries (18:59:59, 19:00:00, 19:01:00, 19:05:00)
    strictly in memory without affecting physical relays or disk configuration.
    """
    parts = sim_time.strip().split(':')
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    s = int(parts[2]) if len(parts) > 2 else 0

    d_parts = sim_date.strip().split('-')
    year = int(d_parts[0])
    month = int(d_parts[1])
    day = int(d_parts[2])

    simulated_dt = datetime(year, month, day, h, m, s, tzinfo=IST)

    result = evaluate_festival_policy(
        dt=simulated_dt,
        festival_name=festival_name,
        festival_mode=festival_mode,
        pump_is_on=pump_is_on,
        override_date=sim_date,
    )
    result["simulated"] = True
    result["simulated_datetime_ist"] = simulated_dt.isoformat()
    return result

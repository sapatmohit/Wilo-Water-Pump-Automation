import os
import sys
import json
import pytest
from datetime import datetime, date
from zoneinfo import ZoneInfo

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'src', 'controller'))
sys.path.insert(0, os.path.join(_ROOT, 'src', 'dashboard'))

import festival_policy as fp
import pump_logic as pl
from server import app

IST = ZoneInfo('Asia/Kolkata')


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ── 1. Rang Panchami Date Verification ────────────────────────────────────────

def test_rang_panchami_dates_in_dataset():
    """Verify all 2020-2030 Rang Panchami dates exist with RANG_PANCHAMI policy."""
    expected = [
        "2020-03-14", "2021-04-02", "2022-03-22", "2023-03-12",
        "2024-03-30", "2025-03-19", "2026-03-08", "2027-03-27",
        "2028-03-16", "2029-04-03", "2030-03-24"
    ]
    all_festivals = fp.load_all_festivals(force_reload=True)
    rp_festivals = {f["date_str"]: f for f in all_festivals if f["policy"] == fp.FestivalPolicyType.RANG_PANCHAMI}

    for dt in expected:
        assert dt in rp_festivals, f"Missing Rang Panchami on {dt}"
        f = rp_festivals[dt]
        assert f["policy"] == "RANG_PANCHAMI"
        assert f["release_time"] == "19:00"
        assert f["is_special_policy"] is True


# ── 2. Time Boundary Tests (18:59, 19:00, 19:01, 19:05) ──────────────────────

def test_boundary_18_59_blocked():
    """At 18:59:59 IST on Rang Panchami, automatic start MUST be blocked."""
    res = fp.simulate_festival_policy("2026-03-08", "18:59:59", "Rang Panchami")
    assert res["automatic_start_allowed"] is False
    assert res["automatic_start_blocked"] is True
    assert res["status"] == "RESTRICTED"
    assert res["release_time"] == "19:00"
    assert "active until 07:00 PM IST" in res["reason"]


def test_boundary_19_00_released():
    """At exactly 19:00:00 IST on Rang Panchami, restriction MUST be released."""
    res = fp.simulate_festival_policy("2026-03-08", "19:00:00", "Rang Panchami")
    assert res["automatic_start_allowed"] is True
    assert res["automatic_start_blocked"] is False
    assert res["status"] == "RELEASED"
    assert "restriction released" in res["reason"].lower()


def test_boundary_19_01_allowed():
    """At 19:01:00 IST on Rang Panchami, normal automatic start is allowed."""
    res = fp.simulate_festival_policy("2026-03-08", "19:01:00", "Rang Panchami")
    assert res["automatic_start_allowed"] is True
    assert res["automatic_start_blocked"] is False
    assert res["status"] == "RELEASED"


def test_boundary_19_05_allowed():
    """At 19:05:00 IST on Rang Panchami, normal automatic start is allowed."""
    res = fp.simulate_festival_policy("2026-03-08", "19:05:00", "Rang Panchami")
    assert res["automatic_start_allowed"] is True
    assert res["automatic_start_blocked"] is False
    assert res["status"] == "RELEASED"


# ── 3. Running Pump Protection (Do NOT terminate active pump) ─────────────────

def test_running_pump_not_shut_down_by_festival():
    """If pump is already running at 18:30 on Rang Panchami, festival policy MUST NOT shut it down."""
    res = fp.simulate_festival_policy("2026-03-08", "18:30:00", "Rang Panchami", pump_is_on=True)
    assert res["running_pump_shutdown"] is False
    assert "permitted to complete cycle safely" in res["reason"]


# ── 4. Festival Mode Toggle ───────────────────────────────────────────────────

def test_festival_mode_off_bypasses_restriction():
    """When Festival Mode is OFF, restrictions are ignored, but safety remains active."""
    res = fp.simulate_festival_policy("2026-03-08", "18:30:00", "Rang Panchami", festival_mode=False)
    assert res["automatic_start_allowed"] is True
    assert res["automatic_start_blocked"] is False
    assert res["status"] == "MODE_OFF"


# ── 5. Standard Festivals (NORMAL Policy) ──────────────────────────────────────

def test_normal_festival_policy():
    """Festivals like Diwali, Holi, Ganesh Chaturthi use NORMAL policy and do not block start."""
    for fest in ["Diwali", "Ganesh Chaturthi", "Dussehra", "Holi"]:
        res = fp.simulate_festival_policy("2026-11-08", "14:00:00", fest)
        assert res["automatic_start_allowed"] is True
        assert res["status"] == "NORMAL"
        assert res["policy"] == "NORMAL"


# ── 6. ML Conflict & Decision Engine Tests ────────────────────────────────────

def test_ml_conflict_blocked_before_19_00():
    """ML says START NOW at 18:45 on Rang Panchami, but Festival Policy blocks it."""
    logic = pl.HybridPumpLogic(
        critical_low=10.0, low=25.0, high=85.0, critical_high=95.0,
        lora_timeout_s=60, max_run_min=120, dry_run_a=0.5, dry_run_enabled=True,
        power_delay_s=0, require_valid_lora_before_start=False,
        voltage_guard_enabled=False, min_voltage_ac=180.0, override_timeout_min=60,
        ml_enabled=True, ml_window_min=120
    )
    logic.set_ml_prediction({'start_hour': 18.75, 'duration': 60})

    sim_1845 = datetime(2026, 3, 8, 18, 45, 0, tzinfo=IST)
    dec = logic.decide(upper_pct=50.0, pump_is_on=False, now=sim_1845)
    assert dec.action == 'HOLD'
    assert 'BLOCKED by festival policy' in dec.reason


def test_critical_low_tank_blocked_on_rang_panchami_before_19_00():
    """Even if tank is critical low (5%), automated start is blocked before 19:00 on Rang Panchami."""
    logic = pl.HybridPumpLogic(
        critical_low=10.0, low=25.0, high=85.0, critical_high=95.0,
        lora_timeout_s=60, max_run_min=120, dry_run_a=0.5, dry_run_enabled=True,
        power_delay_s=0, require_valid_lora_before_start=False,
        voltage_guard_enabled=False, min_voltage_ac=180.0, override_timeout_min=60,
        ml_enabled=False, ml_window_min=60
    )
    sim_1859 = datetime(2026, 3, 8, 18, 59, 59, tzinfo=IST)
    dec = logic.decide(upper_pct=5.0, pump_is_on=False, now=sim_1859)
    assert dec.action == 'HOLD'
    assert 'BLOCKED by festival policy' in dec.reason


def test_after_19_00_automatic_start_proceeds():
    """At 19:01 on Rang Panchami, tank low trigger can start pump."""
    logic = pl.HybridPumpLogic(
        critical_low=10.0, low=25.0, high=85.0, critical_high=95.0,
        lora_timeout_s=60, max_run_min=120, dry_run_a=0.5, dry_run_enabled=True,
        power_delay_s=0, require_valid_lora_before_start=False,
        voltage_guard_enabled=False, min_voltage_ac=180.0, override_timeout_min=60,
        ml_enabled=False, ml_window_min=60
    )
    sim_1901 = datetime(2026, 3, 8, 19, 1, 0, tzinfo=IST)
    dec = logic.decide(upper_pct=20.0, pump_is_on=False, now=sim_1901)
    assert dec.action == 'ON'


def test_manual_override_bypasses_festival_restriction():
    """Manual override ON works even before 19:00 on Rang Panchami."""
    logic = pl.HybridPumpLogic(
        critical_low=10.0, low=25.0, high=85.0, critical_high=95.0,
        lora_timeout_s=60, max_run_min=120, dry_run_a=0.5, dry_run_enabled=True,
        power_delay_s=0, require_valid_lora_before_start=False,
        voltage_guard_enabled=False, min_voltage_ac=180.0, override_timeout_min=60,
        ml_enabled=False, ml_window_min=60
    )
    logic.set_override('ON')
    sim_1859 = datetime(2026, 3, 8, 18, 59, 59, tzinfo=IST)
    dec = logic.decide(upper_pct=50.0, pump_is_on=False, now=sim_1859)
    assert dec.action == 'ON'
    assert dec.state == pl.PumpState.ON_MANUAL


# ── 7. Flask API Endpoints ────────────────────────────────────────────────────

def test_api_festival_status(client):
    res = client.get('/api/festival/status')
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert 'festival_mode' in data
    assert 'automatic_start_allowed' in data
    assert 'timezone' in data
    assert data['timezone'] == 'Asia/Kolkata'


def test_api_festivals_calendar(client):
    res = client.get('/api/festivals/calendar?year=2026&month=3')
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert data['year'] == 2026
    assert data['month'] == 3
    fest_names = [f['name'] for f in data['festivals']]
    assert 'Rang Panchami' in fest_names


def test_api_festival_mode_toggle(client):
    res_off = client.post('/api/festival/mode', json={'enabled': False})
    assert res_off.status_code == 200
    assert res_off.get_json()['festival_mode'] is False

    res_on = client.post('/api/festival/mode', json={'enabled': True})
    assert res_on.status_code == 200
    assert res_on.get_json()['festival_mode'] is True


def test_api_festival_simulate(client):
    # Simulate blocked at 18:59:59
    res1 = client.post('/api/festival/simulate', json={
        'sim_date': '2026-03-08',
        'sim_time': '18:59:59',
        'festival_name': 'Rang Panchami'
    })
    assert res1.status_code == 200
    r1 = res1.get_json()['result']
    assert r1['automatic_start_blocked'] is True
    assert r1['status'] == 'RESTRICTED'

    # Simulate released at 19:00:00
    res2 = client.post('/api/festival/simulate', json={
        'sim_date': '2026-03-08',
        'sim_time': '19:00:00',
        'festival_name': 'Rang Panchami'
    })
    assert res2.status_code == 200
    r2 = res2.get_json()['result']
    assert r2['automatic_start_blocked'] is False
    assert r2['status'] == 'RELEASED'

import os
import sys
import json
import pytest

# Ensure paths
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'src', 'controller'))
sys.path.insert(0, os.path.join(_ROOT, 'src', 'dashboard'))

import db
import manual_pump_control
from server import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_db_init_and_seed():
    db.init_db()
    users = db._get_connection().execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    assert users >= 2, "Default users should be seeded"
    
    water_cuts = db.get_water_cuts()
    assert len(water_cuts) >= 2, "Default water cuts should be seeded"


def test_auth_flow():
    # 1. Valid login
    res = db.login_user('operator', 'operator123')
    assert res['ok'] is True
    assert 'token' in res
    token = res['token']
    
    # 2. Session validation
    session = db.validate_session(token)
    assert session is not None
    assert session['username'] == 'operator'
    
    # 3. Invalid login
    res_bad = db.login_user('operator', 'wrongpassword')
    assert res_bad['ok'] is False
    
    # 4. User registration
    import time
    uname = f"test_user_{int(time.time() * 1000)}"
    reg = db.register_user(uname, 'password123', 'operator')
    assert reg['ok'] is True
    
    # 5. Duplicate registration
    reg_dup = db.register_user(uname, 'password123')
    assert reg_dup['ok'] is False
    
    # 6. Logout
    assert db.logout_session(token) is True
    assert db.validate_session(token) is None


def test_schedule_crud():
    task_id = "test-task-101"
    # Create
    res = db.add_scheduled_task(task_id, "2026-09-10", "09:30", "45", "manual")
    assert res['ok'] is True
    
    # Read
    tasks = db.get_scheduled_tasks()
    found = any(t['id'] == task_id for t in tasks)
    assert found is True
    
    # Delete
    deleted = db.delete_scheduled_task(task_id)
    assert deleted is True


def test_water_cuts_crud():
    # Create
    res = db.add_water_cut("Sector Z", "11:00", "13:00", "Test Pipe Maintenance")
    assert res['ok'] is True
    cut_id = res['id']
    
    # Read
    cuts = db.get_water_cuts()
    assert any(c['id'] == cut_id for c in cuts)
    
    # Delete
    assert db.delete_water_cut(cut_id) is True


def test_manual_pump_control():
    on_res = manual_pump_control.set_pump(True, notify_controller=False)
    assert on_res['pump_relay_on'] is True
    status = manual_pump_control.read_status()
    assert status['pump_relay_on'] is True
    
    off_res = manual_pump_control.set_pump(False, notify_controller=False)
    assert off_res['pump_relay_on'] is False


def test_flask_health_and_status_endpoints(client):
    # Health endpoint
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'healthy'
    
    # Dashboard status
    res = client.get('/api/dashboard/status')
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert 'pump' in data
    assert 'telemetry' in data


def test_flask_auth_api(client):
    # Login via API
    res = client.post('/api/auth/login', json={
        'username': 'operator',
        'password': 'operator123'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    token = data['token']
    
    # /api/auth/me with token
    res = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert data['user']['username'] == 'operator'
    
    # /api/auth/logout
    res = client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200


def test_flask_pump_and_mode_endpoints(client):
    # Pump on
    res = client.post('/api/pump/on')
    assert res.status_code == 200
    assert res.get_json()['ok'] is True
    
    # Pump off
    res = client.post('/api/pump/off')
    assert res.status_code == 200
    assert res.get_json()['ok'] is True
    
    # Mode switch
    res = client.post('/api/mode', json={'mode': 'manual'})
    assert res.status_code == 200
    assert res.get_json()['mode'] == 'manual'
    
    # Clear override
    res = client.post('/api/pump/clear-override')
    assert res.status_code == 200
    assert res.get_json()['ok'] is True


def test_hardware_status_and_zero_fake_telemetry(client):
    res = client.get('/api/hardware/status')
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert 'master_motor' in data
    assert 'slave_motor' in data
    assert 'tank' in data

    # On Windows / Mock localhost, master and slave hardware must report correctly without fake numbers
    master = data['master_motor']
    assert 'raspberry_pi' in master
    assert 'current_sensor' in master
    assert 'relay' in master
    assert master['connected'] is False, "Mock environment should report connected=False"

    slave = data['slave_motor']
    assert 'esp32' in slave
    assert 'pressure_sensor' in slave
    assert 'lora' in slave


def test_telemetry_history_endpoint(client):
    res = client.get('/api/telemetry/history?limit=20')
    assert res.status_code == 200
    data = res.get_json()
    assert data['ok'] is True
    assert 'pressure_history' in data
    assert 'current_history' in data
    assert 'lora_history' in data


def test_emergency_stop_flow(client):
    # Trigger emergency stop
    res = client.post('/api/emergency-stop', json={'reason': 'Test emergency trigger'})
    assert res.status_code == 200
    assert res.get_json()['ok'] is True

    # Pump on must be blocked while emergency stop is active
    res_pump = client.post('/api/pump/on')
    assert res_pump.status_code == 403

    # Reset emergency stop
    res_reset = client.post('/api/emergency-stop/reset')
    assert res_reset.status_code == 200
    assert res_reset.get_json()['ok'] is True


def test_tank_state_rule_pump_off_not_empty():
    from server import _calculate_tank_state
    # When pump is off and current is 0A, tank level with 35 kPa pressure is NOT empty!
    tank = _calculate_tank_state(35.0, is_online=True)
    assert tank['level_percent'] is not None
    assert tank['level_percent'] > 0
    assert tank['is_empty'] is False
    assert tank['state'] in ('NORMAL', 'HIGH', 'LOW', 'FULL')


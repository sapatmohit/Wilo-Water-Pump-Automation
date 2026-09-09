"""
Database persistence module for Wilo Water Pump Automation System.
Uses SQLite for robust local and production storage.
"""

from __future__ import annotations

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
DB_PATH = os.path.join(_DB_DIR, 'wilo_system.db')


def _get_connection() -> sqlite3.Connection:
    os.makedirs(_DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize SQLite database tables and seed defaults if empty."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Users table for authentication
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'operator',
                created_at TEXT NOT NULL
            )
        ''')
        
        # 2. Auth sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # 3. Scheduled tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                duration TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                type TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL
            )
        ''')
        
        # 4. Water cuts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS water_cuts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                created_at TEXT NOT NULL
            )
        ''')
        
        # 5. Pump operation logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pump_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        
        # Seed default users if empty
        cursor.execute('SELECT COUNT(*) as count FROM users')
        if cursor.fetchone()['count'] == 0:
            _create_user(cursor, 'operator', 'operator123', 'operator')
            _create_user(cursor, 'admin', 'admin123', 'admin')
            conn.commit()
            
        # Seed default water cuts if empty
        cursor.execute('SELECT COUNT(*) as count FROM water_cuts')
        if cursor.fetchone()['count'] == 0:
            cursor.execute('''
                INSERT INTO water_cuts (area, start_time, end_time, reason, status, created_at)
                VALUES 
                    ('Sector A', '10:00', '14:00', 'Pipe Line Maintenance', 'active', ?),
                    ('Sector B', '15:00', '17:00', 'Valve Replacement', 'scheduled', ?)
            ''', (datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()


# ── Password & Auth Helpers ──────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000
    ).hex()


def _create_user(cursor: sqlite3.Cursor, username: str, password: str, role: str = 'operator') -> int:
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    cursor.execute('''
        INSERT INTO users (username, password_hash, salt, role, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, pw_hash, salt, role, datetime.now().isoformat()))
    return cursor.lastrowid


def register_user(username: str, password: str, role: str = 'operator') -> Dict[str, Any]:
    username = username.strip()
    if not username or len(username) < 3:
        return {'ok': False, 'error': 'Username must be at least 3 characters'}
    if not password or len(password) < 6:
        return {'ok': False, 'error': 'Password must be at least 6 characters'}
        
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return {'ok': False, 'error': f'User "{username}" already exists'}
            
        user_id = _create_user(cursor, username, password, role)
        conn.commit()
        return {'ok': True, 'user_id': user_id, 'username': username, 'role': role}


def login_user(username: str, password: str) -> Dict[str, Any]:
    username = username.strip()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        if not row:
            return {'ok': False, 'error': 'Invalid username or password'}
            
        pw_hash = _hash_password(password, row['salt'])
        if pw_hash != row['password_hash']:
            return {'ok': False, 'error': 'Invalid username or password'}
            
        token = secrets.token_urlsafe(32)
        now = datetime.now()
        expires = (now + timedelta(days=7)).isoformat()
        
        cursor.execute('''
            INSERT INTO sessions (token, user_id, username, role, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (token, row['id'], row['username'], row['role'], now.isoformat(), expires))
        conn.commit()
        
        return {
            'ok': True,
            'token': token,
            'user': {
                'id': row['id'],
                'username': row['username'],
                'role': row['role'],
                'created_at': row['created_at'],
            },
            'expires_at': expires
        }


def validate_session(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sessions WHERE token = ?', (token,))
        row = cursor.fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row['expires_at']) < datetime.now():
            cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
            conn.commit()
            return None
        return {
            'user_id': row['user_id'],
            'username': row['username'],
            'role': row['role']
        }


def logout_session(token: str) -> bool:
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
        conn.commit()
        return cursor.rowcount > 0


# ── Scheduled Tasks CRUD ─────────────────────────────────────────────────────

def get_scheduled_tasks() -> List[Dict[str, Any]]:
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scheduled_tasks ORDER BY date ASC, time ASC')
        return [dict(row) for row in cursor.fetchall()]


def add_scheduled_task(task_id: str, date: str, time_str: str, duration: str, task_type: str = 'manual') -> Dict[str, Any]:
    with _get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO scheduled_tasks (id, date, time, duration, status, type, created_at)
            VALUES (?, ?, ?, ?, 'scheduled', ?, ?)
        ''', (task_id, date, time_str, duration, task_type, now))
        conn.commit()
        return {'ok': True, 'id': task_id, 'date': date, 'time': time_str, 'duration': duration, 'status': 'scheduled'}


def update_task_status(task_id: str, status: str) -> bool:
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE scheduled_tasks SET status = ? WHERE id = ?', (status, task_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_scheduled_task(task_id: str) -> bool:
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM scheduled_tasks WHERE id = ?', (task_id,))
        conn.commit()
        return cursor.rowcount > 0


# ── Water Cuts CRUD ──────────────────────────────────────────────────────────

def get_water_cuts() -> List[Dict[str, Any]]:
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM water_cuts ORDER BY id DESC')
        return [dict(row) for row in cursor.fetchall()]


def add_water_cut(area: str, start_time: str, end_time: str, reason: str, status: str = 'scheduled') -> Dict[str, Any]:
    with _get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO water_cuts (area, start_time, end_time, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (area, start_time, end_time, reason, status, now))
        conn.commit()
        return {
            'ok': True,
            'id': cursor.lastrowid,
            'area': area,
            'start_time': start_time,
            'end_time': end_time,
            'reason': reason,
            'status': status
        }


def delete_water_cut(cut_id: int) -> bool:
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM water_cuts WHERE id = ?', (cut_id,))
        conn.commit()
        return cursor.rowcount > 0


# ── Operation Audit Logs ─────────────────────────────────────────────────────

def log_pump_action(action: str, source: str, status: str, details: str = '') -> None:
    try:
        with _get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pump_logs (action, source, status, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (action, source, status, details, datetime.now().isoformat()))
            conn.commit()
    except Exception:
        pass


def get_pump_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM pump_logs ORDER BY id DESC LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]

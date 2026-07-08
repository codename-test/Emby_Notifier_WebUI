#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Database module for Emby Notifier.
SQLite-based storage for port configs, channel configs,
DND settings, and message queue.
"""

import sqlite3
import json
import threading
import os
import log

DB_PATH = os.getenv("DB_PATH", "emby_notifier.db")
_local = threading.local()


def _get_conn():
    """Get a thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
    return _local.conn


# ──────────────────────────────────────────────
#  Initialization
# ──────────────────────────────────────────────

def init_db():
    """Initialize database tables."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS ports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            port INTEGER UNIQUE NOT NULL,
            server_name TEXT NOT NULL DEFAULT '',
            server_type TEXT NOT NULL DEFAULT 'Emby',
            server_url TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            port_id INTEGER NOT NULL,
            channel_type TEXT NOT NULL,
            enabled INTEGER DEFAULT 0,
            config TEXT DEFAULT '{}',
            FOREIGN KEY (port_id) REFERENCES ports(id) ON DELETE CASCADE,
            UNIQUE(port_id, channel_type)
        );

        CREATE TABLE IF NOT EXISTS dnd_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            enabled INTEGER DEFAULT 0,
            start_time TEXT DEFAULT '23:00',
            end_time TEXT DEFAULT '07:00'
        );

        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS message_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            port_id INTEGER NOT NULL,
            media_json TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP,
            error TEXT,
            FOREIGN KEY (port_id) REFERENCES ports(id) ON DELETE CASCADE
        );
    """)
    # Ensure DND settings row exists
    conn.execute(
        "INSERT OR IGNORE INTO dnd_settings (id, enabled, start_time, end_time) "
        "VALUES (1, 0, '23:00', '07:00')"
    )
    conn.commit()
    log.logger.info(f"Database initialized at {DB_PATH}")


# ──────────────────────────────────────────────
#  Port CRUD
# ──────────────────────────────────────────────

def get_all_ports():
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM ports ORDER BY port"
    ).fetchall()
    return [dict(r) for r in rows]


def get_port(port_id):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM ports WHERE id=?", (port_id,)).fetchone()
    return dict(row) if row else None


# Alias for clarity
get_port_by_id = get_port


def get_port_by_number(port_number):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM ports WHERE port=?", (port_number,)).fetchone()
    return dict(row) if row else None


def create_port(port_number, server_name, server_type="Emby", server_url=""):
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "INSERT INTO ports (port, server_name, server_type, server_url) "
            "VALUES (?, ?, ?, ?)",
            (port_number, server_name, server_type, server_url),
        )
        conn.commit()
        port_id = cursor.lastrowid
        # Auto-create default channel entries
        for ch in ["wechat_work", "telegram", "bark"]:
            conn.execute(
                "INSERT OR IGNORE INTO channels (port_id, channel_type, enabled, config) "
                "VALUES (?, ?, 0, '{}')",
                (port_id, ch),
            )
        conn.commit()
        log.logger.info(f"Port created: id={port_id}, port={port_number}, name={server_name}")
        return port_id
    except sqlite3.IntegrityError:
        log.logger.error(f"Port {port_number} already exists")
        return None


def update_port(port_id, **kwargs):
    conn = _get_conn()
    allowed = {"port", "server_name", "server_type", "server_url", "enabled"}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not fields:
        return False
    set_clause = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE ports SET {set_clause} WHERE id=?",
        (*fields.values(), port_id),
    )
    conn.commit()
    return True


def delete_port(port_id):
    conn = _get_conn()
    conn.execute("DELETE FROM channels WHERE port_id=?", (port_id,))
    conn.execute("DELETE FROM message_queue WHERE port_id=?", (port_id,))
    conn.execute("DELETE FROM ports WHERE id=?", (port_id,))
    conn.commit()


# ──────────────────────────────────────────────
#  Channel CRUD
# ──────────────────────────────────────────────

def get_channels(port_id):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM channels WHERE port_id=?", (port_id,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d["config"]) if d["config"] else {}
        result.append(d)
    return result


def get_channel(port_id, channel_type):
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM channels WHERE port_id=? AND channel_type=?",
        (port_id, channel_type),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["config"] = json.loads(d["config"]) if d["config"] else {}
    return d


def save_channel(port_id, channel_type, config, enabled=False):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO channels (port_id, channel_type, enabled, config) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(port_id, channel_type) "
        "DO UPDATE SET config=excluded.config, enabled=excluded.enabled",
        (port_id, channel_type, int(enabled), json.dumps(config, ensure_ascii=False)),
    )
    conn.commit()


def toggle_channel(port_id, channel_type, enabled):
    conn = _get_conn()
    conn.execute(
        "UPDATE channels SET enabled=? WHERE port_id=? AND channel_type=?",
        (int(enabled), port_id, channel_type),
    )
    conn.commit()


def get_enabled_channels(port_id):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM channels WHERE port_id=? AND enabled=1", (port_id,)
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["config"] = json.loads(d["config"]) if d["config"] else {}
        result.append(d)
    return result


# ──────────────────────────────────────────────
#  DND Settings
# ──────────────────────────────────────────────

def get_dnd_settings():
    conn = _get_conn()
    row = conn.execute("SELECT * FROM dnd_settings WHERE id=1").fetchone()
    return dict(row) if row else {"enabled": 0, "start_time": "23:00", "end_time": "07:00"}


def update_dnd(enabled=None, start_time=None, end_time=None):
    conn = _get_conn()
    if enabled is not None:
        conn.execute("UPDATE dnd_settings SET enabled=? WHERE id=1", (int(enabled),))
    if start_time is not None:
        conn.execute("UPDATE dnd_settings SET start_time=? WHERE id=1", (start_time,))
    if end_time is not None:
        conn.execute("UPDATE dnd_settings SET end_time=? WHERE id=1", (end_time,))
    conn.commit()


# ──────────────────────────────────────────────
#  Message Queue
# ──────────────────────────────────────────────

def enqueue_message(port_id, media_json):
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO message_queue (port_id, media_json) VALUES (?, ?)",
        (port_id, media_json),
    )
    conn.commit()
    return cursor.lastrowid


def get_pending_messages(port_id=None):
    conn = _get_conn()
    if port_id:
        rows = conn.execute(
            "SELECT * FROM message_queue WHERE port_id=? AND status='pending' ORDER BY created_at",
            (port_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM message_queue WHERE status='pending' ORDER BY created_at"
        ).fetchall()
    return [dict(r) for r in rows]


def update_message_status(msg_id, status, error=None):
    conn = _get_conn()
    if status == "sent":
        conn.execute(
            "UPDATE message_queue SET status=?, sent_at=CURRENT_TIMESTAMP, error=NULL WHERE id=?",
            (status, msg_id),
        )
    else:
        conn.execute(
            "UPDATE message_queue SET status=?, error=? WHERE id=?",
            (status, error, msg_id),
        )
    conn.commit()


def get_queue_stats():
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM message_queue").fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM message_queue WHERE status='pending'"
    ).fetchone()[0]
    sent = conn.execute(
        "SELECT COUNT(*) FROM message_queue WHERE status='sent'"
    ).fetchone()[0]
    failed = conn.execute(
        "SELECT COUNT(*) FROM message_queue WHERE status='failed'"
    ).fetchone()[0]
    return {"total": total, "pending": pending, "sent": sent, "failed": failed}


def get_all_messages(limit=100, offset=0):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT mq.*, p.port, p.server_name "
        "FROM message_queue mq "
        "JOIN ports p ON mq.port_id = p.id "
        "ORDER BY mq.created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_message(msg_id):
    conn = _get_conn()
    conn.execute("DELETE FROM message_queue WHERE id=?", (msg_id,))
    conn.commit()


# ──────────────────────────────────────────────
#  Dashboard Stats
# ──────────────────────────────────────────────

def get_dashboard_stats():
    conn = _get_conn()
    total_ports = conn.execute("SELECT COUNT(*) FROM ports").fetchone()[0]
    active_ports = conn.execute(
        "SELECT COUNT(*) FROM ports WHERE enabled=1"
    ).fetchone()[0]
    queue_stats = get_queue_stats()
    dnd = get_dnd_settings()
    return {
        "total_ports": total_ports,
        "active_ports": active_ports,
        "queue_total": queue_stats["total"],
        "queue_pending": queue_stats["pending"],
        "queue_sent": queue_stats["sent"],
        "queue_failed": queue_stats["failed"],
        "dnd_enabled": bool(dnd["enabled"]),
        "dnd_start": dnd["start_time"],
        "dnd_end": dnd["end_time"],
    }


# ──────────────────────────────────────────────
#  System Config
# ──────────────────────────────────────────────

def get_system_config(key):
    """获取系统配置"""
    conn = _get_conn()
    cursor = conn.execute("SELECT value FROM system_config WHERE key = ?", (key,))
    row = cursor.fetchone()
    if row:
        return row[0]
    return None


def set_system_config(key, value):
    """设置系统配置"""
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
        (key, value)
    )
    conn.commit()


def get_all_system_config():
    """获取所有系统配置"""
    conn = _get_conn()
    cursor = conn.execute("SELECT key, value FROM system_config")
    return {row[0]: row[1] for row in cursor.fetchall()}

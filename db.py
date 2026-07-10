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
            wechat_config_id INTEGER,
            template_id INTEGER DEFAULT 1,
            send_targets TEXT DEFAULT '[]',
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (wechat_config_id) REFERENCES wechat_configs(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS wechat_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            corp_id TEXT NOT NULL,
            corp_secret TEXT NOT NULL,
            agent_id INTEGER NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            config TEXT NOT NULL DEFAULT '{}',
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            level TEXT NOT NULL DEFAULT 'INFO',
            module TEXT DEFAULT '',
            message TEXT NOT NULL,
            port_id INTEGER DEFAULT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);

        CREATE TABLE IF NOT EXISTS push_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            picurl_movie TEXT DEFAULT 'media_backdrop',
            picurl_episode TEXT DEFAULT 'media_still',
            enable_image INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # 迁移：添加 enable_image 列（兼容旧数据库）
    try:
        conn.execute("ALTER TABLE push_templates ADD COLUMN enable_image INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # 列已存在
    # 迁移：添加 is_fallback 列
    try:
        conn.execute("ALTER TABLE push_templates ADD COLUMN is_fallback INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    # 迁移：添加 template_id 列（兼容旧数据库）
    try:
        conn.execute("ALTER TABLE ports ADD COLUMN template_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # 列已存在
    # 迁移：添加 channel_ids 列
    try:
        conn.execute("ALTER TABLE ports ADD COLUMN channel_ids TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass  # 列已存在
    # 迁移：wechat_configs → channels
    wc_count = conn.execute("SELECT COUNT(*) FROM wechat_configs").fetchone()[0]
    ch_count = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    if wc_count > 0 and ch_count == 0:
        log.logger.info("Migrating wechat_configs to channels...")
        # 建立 ID 映射：旧 wechat_config_id -> 新 channel_id
        id_map = {}
        for wc in conn.execute("SELECT * FROM wechat_configs").fetchall():
            config = json.dumps({
                "corp_id": wc["corp_id"],
                "corp_secret": wc["corp_secret"],
                "agent_id": wc["agent_id"],
                "user_id": "",
            })
            cursor = conn.execute(
                "INSERT INTO channels (name, type, config, enabled) VALUES (?, 'wechat_work_api', ?, ?)",
                (wc["name"], config, wc["enabled"])
            )
            id_map[wc["id"]] = cursor.lastrowid
        # 迁移 ports.wechat_config_id → ports.channel_ids
        for port in conn.execute("SELECT id, wechat_config_id FROM ports").fetchall():
            if port["wechat_config_id"] and port["wechat_config_id"] in id_map:
                new_channel_id = id_map[port["wechat_config_id"]]
                conn.execute(
                    "UPDATE ports SET channel_ids=? WHERE id=?",
                    (json.dumps([new_channel_id]), port["id"])
                )
        conn.commit()
        log.logger.info(f"Migration complete: {len(id_map)} channel(s) migrated")
    
    # 迁移：ports.send_targets → channels.config.user_id
    # 检查是否有端口配置了 send_targets
    ports_with_targets = conn.execute(
        "SELECT id, send_targets FROM ports WHERE send_targets IS NOT NULL AND send_targets != '[]'"
    ).fetchall()
    if ports_with_targets:
        log.logger.info(f"Migrating send_targets from {len(ports_with_targets)} port(s) to wechat_work_api channels...")
        for port in ports_with_targets:
            port_id = port["id"]
            try:
                targets = json.loads(port["send_targets"]) if isinstance(port["send_targets"], str) else port["send_targets"]
                if not targets:
                    continue
                # 将 targets 列表转换为逗号分隔的字符串
                user_id_str = ",".join(targets) if isinstance(targets, list) else str(targets)
                # 找到该端口关联的企微应用通道
                channel_ids_str = conn.execute("SELECT channel_ids FROM ports WHERE id=?", (port_id,)).fetchone()["channel_ids"]
                if not channel_ids_str:
                    continue
                channel_ids = json.loads(channel_ids_str) if isinstance(channel_ids_str, str) else channel_ids_str
                for ch_id in channel_ids:
                    ch = conn.execute("SELECT id, type, config FROM channels WHERE id=?", (ch_id,)).fetchone()
                    if ch and ch["type"] == "wechat_work_api":
                        config = json.loads(ch["config"]) if isinstance(ch["config"], str) else ch["config"]
                        # 只有当 user_id 为空时才迁移
                        if not config.get("user_id"):
                            config["user_id"] = user_id_str
                            conn.execute(
                                "UPDATE channels SET config=? WHERE id=?",
                                (json.dumps(config), ch_id)
                            )
                            log.logger.debug(f"Migrated send_targets to channel {ch_id}: {user_id_str}")
            except Exception as e:
                log.logger.error(f"Failed to migrate send_targets for port {port_id}: {e}")
        conn.commit()
        log.logger.info("send_targets migration complete")
    
    # Ensure DND settings row exists
    conn.execute(
        "INSERT OR IGNORE INTO dnd_settings (id, enabled, start_time, end_time) "
        "VALUES (1, 0, '23:00', '07:00')"
    )
    # Ensure default LOG_LEVEL exists
    conn.execute(
        "INSERT OR IGNORE INTO system_config (key, value) VALUES ('LOG_LEVEL', 'INFO')"
    )
    # Ensure default push templates exist
    count = conn.execute("SELECT COUNT(*) FROM push_templates").fetchone()[0]
    if count == 0:
        conn.execute(
            "INSERT INTO push_templates (id, name, title, description, picurl_movie, picurl_episode, enable_image, is_fallback) "
            "VALUES (1, '标准', '{type}更新', "
            "'{name} ({year}){episode}\n\n 上映日期：{date}\n⭐ 评分：{rating}\n\n简介：{intro}', "
            "'media_backdrop', 'media_still', 1, 0)"
        )
        conn.execute(
            "INSERT INTO push_templates (id, name, title, description, picurl_movie, picurl_episode, enable_image, is_fallback) "
            "VALUES (2, '基础模板', '更新通知', "
            "'{name} ({year}){episode}\n\n {date}\n⭐ {rating}', "
            "'', '', 0, 1)"
        )
    else:
        # 迁移旧模板
        conn.execute("UPDATE push_templates SET name='标准', title='{type}更新', description='{name} ({year}){episode}\n\n 上映日期：{date}\n⭐ 评分：{rating}\n\n简介：{intro}', picurl_movie='media_backdrop', picurl_episode='media_still', enable_image=1, is_fallback=0 WHERE id=1")
        conn.execute("UPDATE push_templates SET name='基础模板', title='更新通知', description='{name} ({year}){episode}\n\n {date}\n⭐ {rating}', picurl_movie='', picurl_episode='', enable_image=0, is_fallback=1 WHERE id=2")
        # 删除旧的剧集更新模板（id=3 如果存在）
        conn.execute("DELETE FROM push_templates WHERE id=3")
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


def create_port(port_number, server_name, server_type="Emby", server_url="", template_id=1, channel_ids=None):
    conn = _get_conn()
    try:
        channel_ids_json = json.dumps(channel_ids) if channel_ids else "[]"
        cursor = conn.execute(
            "INSERT INTO ports (port, server_name, server_type, server_url, template_id, channel_ids) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (port_number, server_name, server_type, server_url, template_id, channel_ids_json),
        )
        conn.commit()
        port_id = cursor.lastrowid
        log.logger.info(f"Port created: id={port_id}, port={port_number}, name={server_name}")
        return port_id
    except sqlite3.IntegrityError:
        log.logger.error(f"Port {port_number} already exists")
        return None


def update_port(port_id, **kwargs):
    conn = _get_conn()
    allowed = {"port", "server_name", "server_url", "enabled", "template_id", "channel_ids"}
    fields = {}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            if k == "channel_ids" and isinstance(v, (list, dict)):
                fields[k] = json.dumps(v)
            else:
                fields[k] = v
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
    conn.execute("DELETE FROM message_queue WHERE port_id=?", (port_id,))
    conn.execute("DELETE FROM ports WHERE id=?", (port_id,))
    conn.commit()


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


# ──────────────────────────────────────────────
#  WeChat Config Management
# ──────────────────────────────────────────────

def get_all_wechat_configs():
    """获取所有企业微信配置组"""
    conn = _get_conn()
    cursor = conn.execute("SELECT * FROM wechat_configs ORDER BY id")
    return [dict(row) for row in cursor.fetchall()]


def get_wechat_config(config_id):
    """获取单个企业微信配置"""
    conn = _get_conn()
    cursor = conn.execute("SELECT * FROM wechat_configs WHERE id = ?", (config_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_wechat_config(name, corp_id, corp_secret, agent_id, enabled=1):
    """创建企业微信配置组"""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO wechat_configs (name, corp_id, corp_secret, agent_id, enabled) VALUES (?, ?, ?, ?, ?)",
        (name, corp_id, corp_secret, agent_id, enabled)
    )
    conn.commit()
    return cursor.lastrowid


def update_wechat_config(config_id, name, corp_id, corp_secret, agent_id, enabled=1):
    """更新企业微信配置组"""
    conn = _get_conn()
    conn.execute(
        "UPDATE wechat_configs SET name=?, corp_id=?, corp_secret=?, agent_id=?, enabled=? WHERE id=?",
        (name, corp_id, corp_secret, agent_id, enabled, config_id)
    )
    conn.commit()


def delete_wechat_config(config_id):
    """删除企业微信配置组"""
    conn = _get_conn()
    conn.execute("DELETE FROM wechat_configs WHERE id = ?", (config_id,))
    conn.commit()


# ──────────────────────────────────────────────
#  Channel Management (多通道)
# ──────────────────────────────────────────────

def get_all_channels():
    """获取所有通道配置"""
    conn = _get_conn()
    cursor = conn.execute("SELECT * FROM channels ORDER BY id")
    return [dict(row) for row in cursor.fetchall()]


def get_channel(channel_id):
    """获取单个通道配置"""
    conn = _get_conn()
    cursor = conn.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_channel(name, channel_type, config, enabled=1):
    """创建通道配置"""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO channels (name, type, config, enabled) VALUES (?, ?, ?, ?)",
        (name, channel_type, config, enabled)
    )
    conn.commit()
    return cursor.lastrowid


def update_channel(channel_id, name=None, channel_type=None, config=None, enabled=None):
    """更新通道配置"""
    conn = _get_conn()
    fields = []
    values = []
    if name is not None:
        fields.append("name=?")
        values.append(name)
    if channel_type is not None:
        fields.append("type=?")
        values.append(channel_type)
    if config is not None:
        fields.append("config=?")
        values.append(config)
    if enabled is not None:
        fields.append("enabled=?")
        values.append(enabled)
    if fields:
        values.append(channel_id)
        conn.execute(f"UPDATE channels SET {', '.join(fields)} WHERE id=?", values)
        conn.commit()


def delete_channel(channel_id):
    """删除通道配置"""
    conn = _get_conn()
    conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
    conn.commit()
    # 清理 ports 中的引用
    for port in conn.execute("SELECT id, channel_ids FROM ports").fetchall():
        try:
            ids = json.loads(port["channel_ids"] or "[]")
            if channel_id in ids:
                ids.remove(channel_id)
                conn.execute("UPDATE ports SET channel_ids=? WHERE id=?", (json.dumps(ids), port["id"]))
        except:
            pass
    conn.commit()


def get_enabled_channels_for_port(port_id):
    """获取端口关联的已启用通道"""
    conn = _get_conn()
    port = conn.execute("SELECT channel_ids FROM ports WHERE id=?", (port_id,)).fetchone()
    if not port:
        return []
    
    channel_ids = json.loads(port["channel_ids"] or "[]")
    if not channel_ids:
        return []
    
    placeholders = ",".join(["?"] * len(channel_ids))
    cursor = conn.execute(
        f"SELECT * FROM channels WHERE id IN ({placeholders}) AND enabled=1",
        channel_ids
    )
    return [dict(row) for row in cursor.fetchall()]


# ──────────────────────────────────────────────
#  Logs
# ──────────────────────────────────────────────

def add_log(level, message, module="", port_id=None):
    """写入一条日志，自动清理超过 10000 条的旧记录"""
    conn = _get_conn()
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        "INSERT INTO logs (timestamp, level, message, module, port_id) VALUES (?, ?, ?, ?, ?)",
        (now, level, message, module, port_id)
    )
    # 保留最近 10000 条
    conn.execute("DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs ORDER BY id DESC LIMIT 10000)")
    conn.commit()


def get_logs(level=None, limit=200, offset=0, port_id=None):
    """查询日志，按时间倒序，level 为最低级别（显示等于和高于此级别的日志）"""
    conn = _get_conn()
    sql = "SELECT * FROM logs WHERE 1=1"
    params = []
    if level:
        # 日志等级：DEBUG < INFO < WARNING < ERROR < CRITICAL
        level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
        min_level = level_order.get(level.upper(), 1)
        # 构建 IN 条件：包含所选级别及更高级别
        levels_to_show = [l for l, v in level_order.items() if v >= min_level]
        placeholders = ",".join(["?"] * len(levels_to_show))
        sql += f" AND level IN ({placeholders})"
        params.extend(levels_to_show)
    if port_id is not None:
        sql += " AND port_id = ?"
        params.append(port_id)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def clear_logs():
    """清空所有日志"""
    conn = _get_conn()
    conn.execute("DELETE FROM logs")
    conn.commit()


def get_log_level():
    """获取当前日志等级"""
    return get_system_config("LOG_LEVEL") or "INFO"


def set_log_level(level):
    """设置日志等级"""
    set_system_config("LOG_LEVEL", level)


# ──────────────────────────────────────────────
#  Push Templates
# ──────────────────────────────────────────────

def get_templates():
    """获取所有推送模板"""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM push_templates ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_template(template_id):
    """获取单个模板"""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM push_templates WHERE id=?", (template_id,)).fetchone()
    return dict(row) if row else None


def create_template(name, title, description, picurl_movie="media_backdrop", picurl_episode="media_still", enable_image=1, is_fallback=0):
    """创建推送模板"""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO push_templates (name, title, description, picurl_movie, picurl_episode, enable_image, is_fallback) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, title, description, picurl_movie, picurl_episode, enable_image, is_fallback)
    )
    conn.commit()
    return cursor.lastrowid


def update_template(template_id, **kwargs):
    """更新推送模板"""
    conn = _get_conn()
    allowed = {"name", "title", "description", "picurl_movie", "picurl_episode", "enable_image", "is_fallback"}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not fields:
        return False
    # 回退模板强制关图（已有模板或本次设为回退都生效）
    existing = conn.execute("SELECT is_fallback FROM push_templates WHERE id=?", (template_id,)).fetchone()
    if fields.get("is_fallback") == 1 or (existing and existing[0] == 1):
        fields["enable_image"] = 0
    # 设置回退时取消其他回退标记
    if fields.get("is_fallback") == 1:
        conn.execute("UPDATE push_templates SET is_fallback=0 WHERE id!=?", (template_id,))
    set_clause = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE push_templates SET {set_clause} WHERE id=?",
        (*fields.values(), template_id),
    )
    conn.commit()
    return True


def get_fallback_template():
    """获取标记为 fallback 的模板（TMDB 失败时使用）"""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM push_templates WHERE is_fallback=1 ORDER BY id LIMIT 1").fetchone()
    return dict(row) if row else None


def delete_template(template_id):
    """删除推送模板"""
    conn = _get_conn()
    conn.execute("DELETE FROM push_templates WHERE id=?", (template_id,))
    conn.commit()


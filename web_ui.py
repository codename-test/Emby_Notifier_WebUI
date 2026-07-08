#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Web UI 模块
提供 Web 管理界面，用于配置端口、渠道、DND 等。
使用 Flask + Bootstrap 5 实现。
"""

import json
import threading
import log
import db
import media
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
port_manager = None  # Will be set by main.py


# Custom Jinja2 filter for parsing JSON
@app.template_filter('fromjson')
def fromjson_filter(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return []
    return value if value else []


# ──────────────────────────────────────────────
#  Page Routes
# ──────────────────────────────────────────────


@app.route("/")
def index():
    """仪表盘页面"""
    stats = db.get_dashboard_stats()
    ports = db.get_all_ports()
    from flask import render_template_string
    content_rendered = render_template_string(INDEX_CONTENT, stats=stats, ports=ports)
    html = BASE_TEMPLATE.replace("{title}", "仪表盘") \
        .replace("{dashboard_active}", "active") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{wechat_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", INDEX_JS)
    return html


@app.route("/ports")
def ports_page():
    """端口管理页面"""
    ports = db.get_all_ports()
    wechat_configs = db.get_all_wechat_configs()
    from flask import render_template_string
    content_rendered = render_template_string(PORTS_CONTENT, ports=ports, wechat_configs=wechat_configs)
    html = BASE_TEMPLATE.replace("{title}", "端口管理") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "active") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{wechat_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", PORTS_JS)
    return html


@app.route("/dnd")
def dnd_page():
    """勿扰设置页面"""
    dnd = db.get_dnd_settings()
    from flask import render_template_string
    content_rendered = render_template_string(DND_CONTENT, dnd=dnd)
    html = BASE_TEMPLATE.replace("{title}", "勿扰设置") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "active") \
        .replace("{queue_active}", "") \
        .replace("{wechat_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", DND_JS)
    return html


@app.route("/queue")
def queue_page():
    """消息队列页面"""
    from flask import render_template_string
    content_rendered = render_template_string(QUEUE_CONTENT)
    html = BASE_TEMPLATE.replace("{title}", "消息队列") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "active") \
        .replace("{wechat_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", QUEUE_JS)
    return html


@app.route("/wechat")
def wechat_page():
    """企业微信配置页面"""
    wechat_configs = db.get_all_wechat_configs()
    from flask import render_template_string
    content_rendered = render_template_string(WECHAT_CONTENT, wechat_configs=wechat_configs)
    html = BASE_TEMPLATE.replace("{title}", "企业微信配置") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{wechat_active}", "active") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", WECHAT_JS)
    return html


@app.route("/settings")
def settings():
    """系统设置页面"""
    config = db.get_all_system_config()
    from flask import render_template_string
    content_rendered = render_template_string(SETTINGS_CONTENT, config=config)
    html = BASE_TEMPLATE.replace("{title}", "系统设置") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{wechat_active}", "") \
        .replace("{settings_active}", "active") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", SETTINGS_JS)
    return html


# ──────────────────────────────────────────────
#  Port API
# ──────────────────────────────────────────────


@app.route("/api/ports", methods=["GET"])
def api_get_ports():
    ports = db.get_all_ports()
    for p in ports:
        p["channels"] = db.get_channels(p["id"])
        p["running"] = port_manager.is_running(p["id"]) if port_manager else False
        # 解析 send_targets
        if isinstance(p.get("send_targets"), str):
            try:
                p["send_targets"] = json.loads(p["send_targets"])
            except:
                p["send_targets"] = []
    return jsonify(ports)


@app.route("/api/ports", methods=["POST"])
def api_create_port():
    data = request.json
    port_id = db.create_port(
        port_number=data["port"],
        server_name=data.get("server_name", ""),
        server_type=data.get("server_type", "Emby"),
        server_url=data.get("server_url", ""),
        wechat_config_id=data.get("wechat_config_id"),
        send_targets=data.get("send_targets", [])
    )
    if port_id is None:
        return jsonify({"error": "端口号已存在"}), 400
    # Auto-start if enabled
    if data.get("enabled", True) and port_manager:
        port_manager.start_port(port_id)
    return jsonify({"id": port_id, "status": "created"})


@app.route("/api/ports/<int:port_id>", methods=["PUT"])
def api_update_port(port_id):
    data = request.json
    old_port = db.get_port(port_id)
    if not old_port:
        return jsonify({"error": "Port not found"}), 404

    was_running = port_manager.is_running(port_id) if port_manager else False
    if was_running:
        port_manager.stop_port(port_id)

    db.update_port(port_id, **data)

    # Restart if needed
    new_enabled = data.get("enabled", old_port["enabled"])
    if new_enabled and port_manager:
        port_manager.start_port(port_id)

    return jsonify({"status": "updated"})


@app.route("/api/ports/<int:port_id>", methods=["DELETE"])
def api_delete_port(port_id):
    if port_manager:
        port_manager.stop_port(port_id)
    db.delete_port(port_id)
    return jsonify({"status": "deleted"})


@app.route("/api/ports/<int:port_id>/toggle", methods=["POST"])
def api_toggle_port(port_id):
    port = db.get_port(port_id)
    if not port:
        return jsonify({"error": "Port not found"}), 404
    new_enabled = 0 if port["enabled"] else 1
    db.update_port(port_id, enabled=new_enabled)
    if port_manager:
        if new_enabled:
            port_manager.start_port(port_id)
        else:
            port_manager.stop_port(port_id)
    return jsonify({"enabled": new_enabled})


# ──────────────────────────────────────────────
#  WeChat Config API
# ──────────────────────────────────────────────


@app.route("/api/wechat-configs", methods=["GET"])
def api_get_wechat_configs():
    configs = db.get_all_wechat_configs()
    return jsonify(configs)


@app.route("/api/wechat-configs", methods=["POST"])
def api_create_wechat_config():
    data = request.json
    config_id = db.create_wechat_config(
        name=data.get("name", ""),
        corp_id=data.get("corp_id", ""),
        corp_secret=data.get("corp_secret", ""),
        agent_id=data.get("agent_id", 0),
        enabled=data.get("enabled", 1)
    )
    return jsonify({"id": config_id, "status": "created"})


@app.route("/api/wechat-configs/<int:config_id>", methods=["PUT"])
def api_update_wechat_config(config_id):
    data = request.json
    db.update_wechat_config(
        config_id=config_id,
        name=data.get("name", ""),
        corp_id=data.get("corp_id", ""),
        corp_secret=data.get("corp_secret", ""),
        agent_id=data.get("agent_id", 0),
        enabled=data.get("enabled", 1)
    )
    return jsonify({"status": "updated"})


@app.route("/api/wechat-configs/<int:config_id>", methods=["DELETE"])
def api_delete_wechat_config(config_id):
    db.delete_wechat_config(config_id)
    return jsonify({"status": "deleted"})


# ──────────────────────────────────────────────
#  Channel API
# ──────────────────────────────────────────────


@app.route("/api/ports/<int:port_id>/channels", methods=["GET"])
def api_get_channels(port_id):
    channels = db.get_channels(port_id)
    return jsonify(channels)


@app.route("/api/ports/<int:port_id>/channels/<channel_type>", methods=["PUT"])
def api_save_channel(port_id, channel_type):
    data = request.json
    db.save_channel(port_id, channel_type, data.get("config", {}), data.get("enabled", False))
    return jsonify({"status": "saved"})


@app.route("/api/ports/<int:port_id>/channels/<channel_type>/toggle", methods=["POST"])
def api_toggle_channel(port_id, channel_type):
    ch = db.get_channel(port_id, channel_type)
    if not ch:
        return jsonify({"error": "Channel not found"}), 404
    new_enabled = 0 if ch["enabled"] else 1
    db.toggle_channel(port_id, channel_type, new_enabled)
    return jsonify({"enabled": new_enabled})


# ──────────────────────────────────────────────
#  DND API
# ──────────────────────────────────────────────


@app.route("/api/dnd", methods=["GET"])
def api_get_dnd():
    return jsonify(db.get_dnd_settings())


@app.route("/api/dnd", methods=["POST"])
def api_save_dnd():
    data = request.json
    db.update_dnd(
        enabled=data.get("enabled"),
        start_time=data.get("start_time"),
        end_time=data.get("end_time")
    )
    return jsonify({"status": "saved"})


# ──────────────────────────────────────────────
#  Queue API
# ──────────────────────────────────────────────


@app.route("/api/queue", methods=["GET"])
def api_get_queue():
    messages = db.get_all_messages()
    for m in messages:
        port = db.get_port(m["port_id"])
        if port:
            m["server_name"] = port["server_name"]
            m["port"] = port["port"]
    return jsonify({"messages": messages})


@app.route("/api/queue/flush", methods=["POST"])
def api_flush_queue():
    """Flush pending messages (trigger send)"""
    pending = db.get_pending_messages()
    count = 0
    for msg in pending:
        port = db.get_port(msg["port_id"])
        if port:
            try:
                media_detail = json.loads(msg["media_json"])
                channels = db.get_enabled_channels(msg["port_id"])
                for ch in channels:
                    media.send_notification(ch, media_detail, port["server_name"])
                db.update_message_status(msg["id"], "sent")
                count += 1
            except Exception as e:
                db.update_message_status(msg["id"], "failed", str(e))
    return jsonify({"count": count})


@app.route("/api/queue/<int:msg_id>", methods=["DELETE"])
def api_delete_queue_msg(msg_id):
    db.delete_message(msg_id)
    return jsonify({"status": "deleted"})


# ──────────────────────────────────────────────
#  Test Push API
# ──────────────────────────────────────────────


@app.route("/api/ports/<int:port_id>/test", methods=["POST"])
def api_test_push(port_id):
    """Send test notification"""
    port = db.get_port(port_id)
    if not port:
        return jsonify({"error": "Port not found"}), 404
    
    channels = db.get_enabled_channels(port_id)
    if not channels:
        return jsonify({"error": "没有启用的推送渠道"}), 400
    
    success_count = 0
    error_count = 0
    
    for ch in channels:
        try:
            media.send_test_notification(ch, port["server_name"])
            success_count += 1
        except Exception as e:
            error_count += 1
            log.logger.error(f"Test push failed for channel {ch['channel_type']}: {e}")
    
    return jsonify({
        "success": success_count,
        "failed": error_count,
        "total": len(channels)
    })


# ──────────────────────────────────────────────
#  Stats API
# ──────────────────────────────────────────────


@app.route("/api/stats", methods=["GET"])
def api_stats():
    stats = db.get_dashboard_stats()
    if port_manager:
        stats["ports_status"] = port_manager.get_status()
    return jsonify(stats)


# ──────────────────────────────────────────────
#  System Config API
# ──────────────────────────────────────────────


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(db.get_all_system_config())


@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.json
    for key, value in data.items():
        db.set_system_config(key, value)
    
    # 验证 TMDB Token（如果提供了）
    if "TMDB_API_TOKEN" in data and data["TMDB_API_TOKEN"]:
        import tmdb_api
        success = tmdb_api.login()
        if success:
            return jsonify({"status": "saved", "tmdb_valid": True})
        else:
            return jsonify({"status": "saved", "tmdb_valid": False, "message": "TMDB Token 验证失败"})
    
    return jsonify({"status": "saved"})


@app.route("/api/config/test_tmdb", methods=["POST"])
def api_test_tmdb():
    data = request.json
    token = data.get("token", "")
    
    if not token:
        return jsonify({"success": False, "error": "Token 不能为空"})
    
    # 临时设置 token 进行测试
    db.set_system_config("TMDB_API_TOKEN", token)
    
    import tmdb_api
    success = tmdb_api.login()
    
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "TMDB API 连接失败，请检查 Token 是否正确"})


def create_app(pm=None):
    """Create and return Flask app, optionally with port manager reference."""
    global port_manager
    port_manager = pm
    return app


def run_web_ui(web_port=5000, pm=None):
    """Run the Web UI server."""
    global port_manager
    port_manager = pm
    log.logger.info(f"Web UI starting on http://0.0.0.0:{web_port}")
    app.run(host="0.0.0.0", port=web_port, debug=False, use_reloader=False)


# ──────────────────────────────────────────────
#  HTML Templates
# ──────────────────────────────────────────────

BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Emby Notifier</title>
    <link href="https://cdn.bootcss.com/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.bootcss.com/bootstrap-icons/1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        :root {
            --sidebar-width: 240px;
            --sidebar-bg: #1a1d23;
            --sidebar-hover: #2d3139;
            --sidebar-active: #3b82f6;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; }
        .sidebar {
            position: fixed; top: 0; left: 0; width: var(--sidebar-width);
            height: 100vh; background: var(--sidebar-bg); color: #fff;
            padding-top: 0; z-index: 1000; overflow-y: auto;
        }
        .sidebar .brand {
            padding: 1.2rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 1.1rem; font-weight: 600;
        }
        .sidebar .brand i { color: #3b82f6; margin-right: 8px; }
        .sidebar .nav-link {
            color: rgba(255,255,255,0.7); padding: 0.7rem 1rem;
            border-radius: 8px; margin: 2px 8px; font-size: 0.9rem;
            transition: all 0.2s;
        }
        .sidebar .nav-link:hover { color: #fff; background: var(--sidebar-hover); }
        .sidebar .nav-link.active { color: #fff; background: var(--sidebar-active); }
        .sidebar .nav-link i { margin-right: 10px; width: 20px; text-align: center; }
        .main-content { margin-left: var(--sidebar-width); padding: 24px; min-height: 100vh; }
        .page-header { margin-bottom: 24px; }
        .page-header h2 { font-weight: 600; color: #1a1d23; }
        .stat-card {
            background: #fff; border-radius: 12px; padding: 1.2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: none;
        }
        .stat-card .stat-icon {
            width: 48px; height: 48px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.3rem;
        }
        .stat-card .stat-value { font-size: 1.8rem; font-weight: 700; color: #1a1d23; }
        .stat-card .stat-label { color: #6b7280; font-size: 0.85rem; }
        .card { border: none; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
        .card-header { background: #fff; border-bottom: 1px solid #f0f0f0; font-weight: 600; }
        .badge-running { background: #10b981; }
        .badge-stopped { background: #ef4444; }
        .badge-dnd { background: #f59e0b; }
        .btn-icon { width: 32px; height: 32px; padding: 0; display: inline-flex; align-items: center; justify-content: center; border-radius: 8px; }
        .table th { font-weight: 600; color: #6b7280; font-size: 0.85rem; text-transform: uppercase; }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <nav class="sidebar">
        <div class="brand">
            <i class="bi bi-bell-fill"></i> Emby Notifier
        </div>
        <div class="nav flex-column mt-3">
            <a class="nav-link {dashboard_active}" href="/"><i class="bi bi-speedometer2"></i> 仪表盘</a>
            <a class="nav-link {ports_active}" href="/ports"><i class="bi bi-hdd-network"></i> 端口管理</a>
            <a class="nav-link {dnd_active}" href="/dnd"><i class="bi bi-moon-fill"></i> 勿扰设置</a>
            <a class="nav-link {queue_active}" href="/queue"><i class="bi bi-inbox"></i> 消息队列</a>
            <a class="nav-link {wechat_active}" href="/wechat"><i class="bi bi-wechat"></i> 企业微信</a>
            <a class="nav-link {settings_active}" href="/settings"><i class="bi bi-gear-fill"></i> 系统设置</a>
        </div>
        <div style="position:absolute;bottom:16px;left:0;right:0;text-align:center;">
            <small class="text-muted">v5.0.0</small>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="main-content">
        {content}
    </div>

    <script src="https://cdn.bootcss.com/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script>
        // API helper
        async function api(url, method='GET', body=null) {
            const opts = { method, headers: {'Content-Type': 'application/json'} };
            if (body) opts.body = JSON.stringify(body);
            const res = await fetch(url, opts);
            return res.json();
        }
        async function apiPost(url, body=null) { return api(url, 'POST', body); }
        async function apiPut(url, body) { return api(url, 'PUT', body); }
        async function apiDelete(url) { return api(url, 'DELETE'); }

        // Toast notification
        function showToast(msg, type='success') {
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;';
                document.body.appendChild(container);
            }
            const toast = document.createElement('div');
            toast.className = 'alert alert-' + type + ' alert-dismissible fade show';
            toast.style.cssText = 'min-width:250px;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
            toast.innerHTML = msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
            container.appendChild(toast);
            setTimeout(function() { toast.remove(); }, 3000);
        }
    </script>
    {extra_js}
</body>
</html>"""



INDEX_CONTENT = """
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-speedometer2"></i> 仪表盘</h2>
            <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">
                <i class="bi bi-arrow-clockwise"></i> 刷新
            </button>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center">
                        <div class="stat-icon bg-primary bg-opacity-10 text-primary me-3">
                            <i class="bi bi-hdd-network"></i>
                        </div>
                        <div>
                            <div class="stat-value">{{ stats.active_ports }}</div>
                            <div class="stat-label">活跃端口</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center">
                        <div class="stat-icon bg-success bg-opacity-10 text-success me-3">
                            <i class="bi bi-check-circle"></i>
                        </div>
                        <div>
                            <div class="stat-value">{{ stats.queue_sent }}</div>
                            <div class="stat-label">已推送</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center">
                        <div class="stat-icon bg-warning bg-opacity-10 text-warning me-3">
                            <i class="bi bi-clock"></i>
                        </div>
                        <div>
                            <div class="stat-value">{{ stats.queue_pending }}</div>
                            <div class="stat-label">待推送</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card">
                    <div class="d-flex align-items-center">
                        <div class="stat-icon bg-{% if stats.dnd_enabled %}warning{% else %}secondary{% endif %} bg-opacity-10 text-{% if stats.dnd_enabled %}warning{% else %}secondary{% endif %} me-3">
                            <i class="bi bi-moon-fill"></i>
                        </div>
                        <div>
                            <div class="stat-value">{% if stats.dnd_enabled %}开{% else %}关{% endif %}</div>
                            <div class="stat-label">勿扰模式</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header py-3">
                <i class="bi bi-hdd-network me-2"></i>端口状态
            </div>
            <div class="card-body p-0">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>端口</th>
                            <th>服务器名称</th>
                            <th>类型</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for port in ports %}
                        <tr>
                            <td><code>{{ port.port }}</code></td>
                            <td>{{ port.server_name }}</td>
                            <td>{{ port.server_type }}</td>
                            <td>
                                {% if port.enabled %}
                                <span class="badge badge-running">运行中</span>
                                {% else %}
                                <span class="badge badge-stopped">已停止</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
"""

INDEX_JS = """
    <script>
        setInterval(() => location.reload(), 30000);
    </script>
"""


PORTS_CONTENT = """
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-hdd-network"></i> 端口管理</h2>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addPortModal">
                <i class="bi bi-plus-lg"></i> 添加端口
            </button>
        </div>

        <div class="card">
            <div class="card-body p-0">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>组名</th>
                            <th>端口</th>
                            <th>服务器类型</th>
                            <th>企业微信配置</th>
                            <th>发送对象</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="portsTable">
                        {% for port in ports %}
                        <tr data-port-id="{{ port.id }}">
                            <td>{{ port.server_name }}</td>
                            <td><code>{{ port.port }}</code></td>
                            <td>{{ port.server_type }}</td>
                            <td>
                                {% if port.wechat_config_id %}
                                    {% for wc in wechat_configs %}
                                        {% if wc.id == port.wechat_config_id %}
                                            {{ wc.name }}
                                        {% endif %}
                                    {% endfor %}
                                {% else %}
                                    <span class="text-muted">未配置</span>
                                {% endif %}
                            </td>
                            <td>
                                {% set targets = [] %}
                                {% if port.send_targets %}
                                    {% if port.send_targets is string %}
                                        {% set targets = port.send_targets | fromjson %}
                                    {% else %}
                                        {% set targets = port.send_targets %}
                                    {% endif %}
                                {% endif %}
                                {% if targets %}
                                    {{ targets | join(', ') }}
                                {% else %}
                                    <span class="text-muted">未配置</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if port.enabled %}
                                <span class="badge badge-running">运行中</span>
                                {% else %}
                                <span class="badge badge-stopped">已停止</span>
                                {% endif %}
                            </td>
                            <td>
                                <button class="btn btn-icon btn-outline-primary btn-sm" onclick="editPort({{ port.id }})" title="编辑">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-icon btn-outline-success btn-sm" onclick="testPush({{ port.id }})" title="测试推送">
                                    <i class="bi bi-send"></i>
                                </button>
                                <button class="btn btn-icon btn-outline-{% if port.enabled %}warning{% else %}success{% endif %} btn-sm" onclick="togglePort({{ port.id }})" title="{% if port.enabled %}停止{% else %}启动{% endif %}">
                                    <i class="bi bi-{% if port.enabled %}pause{% else %}play{% endif %}-fill"></i>
                                </button>
                                <button class="btn btn-icon btn-outline-danger btn-sm" onclick="deletePort({{ port.id }})" title="删除">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Add Port Modal -->
        <div class="modal fade" id="addPortModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">添加端口</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addPortForm">
                            <div class="mb-3">
                                <label class="form-label">组名 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="addPortName" required placeholder="例如：家庭服务器">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">监听端口 <span class="text-danger">*</span></label>
                                <input type="number" class="form-control" id="addPortNumber" required placeholder="例如：8001">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">服务器类型</label>
                                <select class="form-select" id="addPortType">
                                    <option value="Emby">Emby</option>
                                    <option value="Jellyfin">Jellyfin</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">企业微信配置组</label>
                                <select class="form-select" id="addPortWechatConfig">
                                    <option value="">请选择...</option>
                                    {% for wc in wechat_configs %}
                                    <option value="{{ wc.id }}">{{ wc.name }}</option>
                                    {% endfor %}
                                </select>
                                <div class="form-text">需要先在"企业微信"页面创建配置组</div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">发送对象</label>
                                <textarea class="form-control" id="addPortTargets" rows="3" placeholder="用户ID或组ID，每行一个&#10;例如：&#10;@all&#10;zhangsan&#10;group123"></textarea>
                                <div class="form-text">支持用户ID和组ID，每行一个。"@all" 表示发送给所有人</div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="savePort()">保存</button>
                    </div>
                </div>
            </div>
        </div>
"""

PORTS_JS = """
    <script>
        async function savePort() {
            const name = document.getElementById('addPortName').value.trim();
            const port = parseInt(document.getElementById('addPortNumber').value);
            const type = document.getElementById('addPortType').value;
            const wechatConfigId = document.getElementById('addPortWechatConfig').value;
            const targetsText = document.getElementById('addPortTargets').value.trim();
            
            if (!name || !port) {
                showToast('请填写组名和端口号', 'danger');
                return;
            }
            
            const targets = targetsText ? targetsText.split('\n').map(t => t.trim()).filter(t => t) : [];
            
            const data = {
                port: port,
                server_name: name,
                server_type: type,
                wechat_config_id: wechatConfigId ? parseInt(wechatConfigId) : null,
                send_targets: targets,
                enabled: true
            };
            
            const res = await apiPost('/api/ports', data);
            if (res.error) {
                showToast('创建失败: ' + res.error, 'danger');
            } else {
                showToast('端口已创建');
                setTimeout(() => location.reload(), 500);
            }
        }
        
        async function editPort(portId) {
            // TODO: 实现编辑功能
            showToast('编辑功能开发中', 'info');
        }
        
        async function togglePort(portId) {
            const res = await apiPost(`/api/ports/${portId}/toggle`);
            showToast(res.enabled ? '已启动' : '已停止');
            setTimeout(() => location.reload(), 500);
        }
        
        async function deletePort(portId) {
            if (!confirm('确定要删除此端口吗？')) return;
            await apiDelete(`/api/ports/${portId}`);
            showToast('端口已删除');
            setTimeout(() => location.reload(), 500);
        }
        
        async function testPush(portId) {
            showToast('正在发送测试消息...', 'info');
            const res = await apiPost(`/api/ports/${portId}/test`);
            if (res.error) {
                showToast('测试失败: ' + res.error, 'danger');
            } else {
                showToast(`测试完成: 成功 ${res.success} 个，失败 ${res.failed} 个`);
            }
        }
    </script>
"""


DND_CONTENT = """
        <div class="page-header">
            <h2><i class="bi bi-moon-fill"></i> 勿扰设置</h2>
        </div>

        <div class="card">
            <div class="card-body">
                <form id="dndForm">
                    <div class="mb-3 form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="dndEnabled" {% if dnd.enabled %}checked{% endif %}>
                        <label class="form-check-label" for="dndEnabled">启用勿扰模式</label>
                    </div>
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label">开始时间</label>
                            <input type="time" class="form-control" id="dndStart" value="{{ dnd.start_time }}">
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label">结束时间</label>
                            <input type="time" class="form-control" id="dndEnd" value="{{ dnd.end_time }}">
                        </div>
                    </div>
                    <button type="button" class="btn btn-primary" onclick="saveDnd()">
                        <i class="bi bi-check-lg"></i> 保存设置
                    </button>
                </form>
            </div>
        </div>

        <div class="card mt-3">
            <div class="card-header py-3">
                <i class="bi bi-info-circle-fill me-2"></i>说明
            </div>
            <div class="card-body">
                <p>勿扰模式开启后，在指定时间段内收到的推送消息会被暂存到消息队列中，待勿扰时间结束后自动推送。</p>
                <p class="mb-0"><strong>示例：</strong>设置 23:00 - 07:00，则晚上 11 点到早上 7 点之间的消息会被延迟推送。</p>
            </div>
        </div>
"""

DND_JS = """
    <script>
        async function saveDnd() {
            const data = {
                enabled: document.getElementById('dndEnabled').checked,
                start_time: document.getElementById('dndStart').value,
                end_time: document.getElementById('dndEnd').value
            };
            await apiPost('/api/dnd', data);
            showToast('勿扰设置已保存');
        }
    </script>
"""


QUEUE_CONTENT = """
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-inbox"></i> 消息队列</h2>
            <button class="btn btn-primary" onclick="flushQueue()">
                <i class="bi bi-send"></i> 推送全部待发消息
            </button>
        </div>

        <div class="card">
            <div class="card-body p-0">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>服务器</th>
                            <th>媒体信息</th>
                            <th>状态</th>
                            <th>创建时间</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="queueTable"></tbody>
                </table>
            </div>
        </div>
"""

QUEUE_JS = """
    <script>
        async function loadQueue() {
            const data = await api('/api/queue');
            const tbody = document.getElementById('queueTable');
            
            if (data.messages.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">暂无消息</td></tr>';
                return;
            }
            
            tbody.innerHTML = data.messages.map(m => {
                let mediaInfo = '';
                try {
                    const info = JSON.parse(m.media_json);
                    mediaInfo = `${info.Name || ''} (${info.Type || ''})`;
                } catch(e) { mediaInfo = m.media_json.substring(0, 50); }

                const statusClass = m.status === 'sent' ? 'queue-status-sent' :
                                    m.status === 'failed' ? 'queue-status-failed' : 'queue-status-pending';
                const statusText = m.status === 'sent' ? '已发送' :
                                   m.status === 'failed' ? '失败' : '待推送';

                return `<tr>
                    <td>${m.id}</td>
                    <td>${m.server_name || ''} :${m.port || ''}</td>
                    <td>${mediaInfo}</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
                    <td>${m.created_at || ''}</td>
                    <td>
                        <button class="btn btn-icon btn-outline-danger btn-sm" onclick="deleteMsg(${m.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>`;
            }).join('');
        }

        async function flushQueue() {
            showToast('正在推送队列消息...', 'info');
            const res = await apiPost('/api/queue/flush');
            showToast(`已推送 ${res.count} 条消息`);
            setTimeout(() => loadQueue(), 1000);
        }

        async function deleteMsg(msgId) {
            await apiDelete(`/api/queue/${msgId}`);
            showToast('消息已删除');
            loadQueue();
        }

        document.addEventListener('DOMContentLoaded', () => {
            loadQueue();
            setInterval(loadQueue, 30000);
        });
    </script>
"""


WECHAT_CONTENT = """
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-wechat"></i> 企业微信配置</h2>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addWechatModal">
                <i class="bi bi-plus-lg"></i> 添加配置组
            </button>
        </div>

        <div class="card">
            <div class="card-body p-0">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>配置组名称</th>
                            <th>企业 ID (Corp ID)</th>
                            <th>应用凭证 (Secret)</th>
                            <th>应用 ID (Agent ID)</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for config in wechat_configs %}
                        <tr>
                            <td>{{ config.name }}</td>
                            <td><code>{{ config.corp_id }}</code></td>
                            <td><code>{{ config.corp_secret[:8] }}...</code></td>
                            <td><code>{{ config.agent_id }}</code></td>
                            <td>
                                {% if config.enabled %}
                                <span class="badge bg-success">启用</span>
                                {% else %}
                                <span class="badge bg-secondary">禁用</span>
                                {% endif %}
                            </td>
                            <td>
                                <button class="btn btn-icon btn-outline-primary btn-sm" onclick="editWechatConfig({{ config.id }})" title="编辑">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-icon btn-outline-danger btn-sm" onclick="deleteWechatConfig({{ config.id }})" title="删除">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                        {% if not wechat_configs %}
                        <tr>
                            <td colspan="6" class="text-center text-muted py-4">暂无配置组，请点击"添加配置组"</td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card mt-3">
            <div class="card-header py-3">
                <i class="bi bi-info-circle-fill me-2"></i>使用说明
            </div>
            <div class="card-body">
                <ol class="mb-0">
                    <li>登录 <a href="https://work.weixin.qq.com" target="_blank">企业微信管理后台</a></li>
                    <li>进入"应用管理" → "自建" → 创建应用</li>
                    <li>获取 <strong>Corp ID</strong>（在"我的企业"→"企业信息"中）</li>
                    <li>获取应用的 <strong>Secret</strong> 和 <strong>Agent ID</strong></li>
                    <li>在此页面添加配置组，然后在"端口管理"中选择使用</li>
                </ol>
            </div>
        </div>

        <!-- Add WeChat Config Modal -->
        <div class="modal fade" id="addWechatModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">添加企业微信配置</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addWechatForm">
                            <div class="mb-3">
                                <label class="form-label">配置组名称 <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="addWechatName" required placeholder="例如：默认企业微信">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">企业 ID (Corp ID) <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="addWechatCorpId" required placeholder="例如：ww1234567890abcdef">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">应用凭证 (Secret) <span class="text-danger">*</span></label>
                                <input type="text" class="form-control" id="addWechatSecret" required placeholder="例如：abcdefghijklmnopqrstuvwxyz123456">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">应用 ID (Agent ID) <span class="text-danger">*</span></label>
                                <input type="number" class="form-control" id="addWechatAgentId" required placeholder="例如：1000002">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="saveWechatConfig()">保存</button>
                    </div>
                </div>
            </div>
        </div>
"""

WECHAT_JS = """
    <script>
        async function saveWechatConfig() {
            const name = document.getElementById('addWechatName').value.trim();
            const corpId = document.getElementById('addWechatCorpId').value.trim();
            const secret = document.getElementById('addWechatSecret').value.trim();
            const agentId = parseInt(document.getElementById('addWechatAgentId').value);
            
            if (!name || !corpId || !secret || !agentId) {
                showToast('请填写所有必填项', 'danger');
                return;
            }
            
            const data = {
                name: name,
                corp_id: corpId,
                corp_secret: secret,
                agent_id: agentId,
                enabled: 1
            };
            
            const res = await apiPost('/api/wechat-configs', data);
            if (res.error) {
                showToast('创建失败: ' + res.error, 'danger');
            } else {
                showToast('配置组已创建');
                setTimeout(() => location.reload(), 500);
            }
        }
        
        async function editWechatConfig(configId) {
            // TODO: 实现编辑功能
            showToast('编辑功能开发中', 'info');
        }
        
        async function deleteWechatConfig(configId) {
            if (!confirm('确定要删除此配置组吗？')) return;
            await apiDelete(`/api/wechat-configs/${configId}`);
            showToast('配置组已删除');
            setTimeout(() => location.reload(), 500);
        }
    </script>
"""


SETTINGS_CONTENT = """
        <div class="page-header">
            <h2><i class="bi bi-gear-fill"></i> 系统设置</h2>
        </div>

        <div class="card mb-4">
            <div class="card-header py-3">
                <i class="bi bi-key-fill me-2"></i>API 配置
            </div>
            <div class="card-body">
                <form id="configForm">
                    <div class="mb-3">
                        <label class="form-label">TMDB API Token <span class="text-danger">*</span></label>
                        <input type="text" class="form-control" id="tmdbToken" placeholder="请输入 TMDB API Token" value="{{ config.get('TMDB_API_TOKEN', '') }}">
                        <div class="form-text">
                            用于获取电影/剧集的详细信息（海报、评分、简介等）。
                            <a href="https://www.themoviedb.org/settings/api" target="_blank">获取 TMDB API Token</a>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">TVDB API Key（可选）</label>
                        <input type="text" class="form-control" id="tvdbKey" placeholder="请输入 TVDB API Key" value="{{ config.get('TVDB_API_KEY', '') }}">
                        <div class="form-text">
                            用于辅助剧集匹配，提高准确性。
                            <a href="https://www.thetvdb.com/api-information" target="_blank">获取 TVDB API Key</a>
                        </div>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">TMDB 图片域名（可选）</label>
                        <input type="text" class="form-control" id="tmdbImageDomain" placeholder="https://image.tmdb.org" value="{{ config.get('TMDB_IMAGE_DOMAIN', 'https://image.tmdb.org') }}">
                        <div class="form-text">
                            用于加速图片加载，可配置为中转代理地址。
                        </div>
                    </div>
                    
                    <button type="button" class="btn btn-primary" onclick="saveConfig()">
                        <i class="bi bi-check-lg"></i> 保存配置
                    </button>
                    <button type="button" class="btn btn-outline-secondary" onclick="testTmdb()">
                        <i class="bi bi-plug"></i> 测试 TMDB 连接
                    </button>
                </form>
            </div>
        </div>

        <div class="card">
            <div class="card-header py-3">
                <i class="bi bi-info-circle-fill me-2"></i>使用说明
            </div>
            <div class="card-body">
                <h6>快速开始</h6>
                <ol>
                    <li>填写 TMDB API Token（必填）</li>
                    <li>在"企业微信"页面添加企业微信配置组</li>
                    <li>在"端口管理"中添加端口，选择企业微信配置组和发送对象</li>
                    <li>在 Emby/Jellyfin 控制台中配置 Webhook 地址</li>
                </ol>
                
                <h6 class="mt-3">Webhook 配置示例</h6>
                <div class="bg-light p-3 rounded">
                    <code>
                        URL: http://你的服务器IP:端口号/<br>
                        事件类型: library.new<br>
                        请求格式: application/json
                    </code>
                </div>
            </div>
        </div>
"""

SETTINGS_JS = """
    <script>
        async function saveConfig() {
            const config = {
                TMDB_API_TOKEN: document.getElementById('tmdbToken').value.trim(),
                TVDB_API_KEY: document.getElementById('tvdbKey').value.trim(),
                TMDB_IMAGE_DOMAIN: document.getElementById('tmdbImageDomain').value.trim() || 'https://image.tmdb.org'
            };
            
            if (!config.TMDB_API_TOKEN) {
                showToast('请输入 TMDB API Token', 'danger');
                return;
            }
            
            showToast('正在保存配置...', 'info');
            const res = await apiPost('/api/config', config);
            
            if (res.status === 'saved') {
                if (res.tmdb_valid === true) {
                    showToast('✅ 配置已保存，TMDB 连接成功！', 'success');
                } else if (res.tmdb_valid === false) {
                    showToast('⚠️ 配置已保存，但 TMDB Token 验证失败：' + (res.message || ''), 'warning');
                } else {
                    showToast('✅ 配置已保存', 'success');
                }
            } else {
                showToast('保存失败：' + (res.error || '未知错误'), 'danger');
            }
        }
        
        async function testTmdb() {
            const token = document.getElementById('tmdbToken').value.trim();
            if (!token) {
                showToast('请先填写 TMDB API Token', 'danger');
                return;
            }
            
            showToast('正在测试 TMDB 连接...', 'info');
            const res = await apiPost('/api/config/test_tmdb', { token });
            
            if (res.success) {
                showToast('✅ TMDB 连接成功！', 'success');
            } else {
                showToast('❌ TMDB 连接失败：' + (res.error || ''), 'danger');
            }
        }
    </script>
"""

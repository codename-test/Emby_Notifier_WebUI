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


# ──────────────────────────────────────────────
#  Page Routes
# ──────────────────────────────────────────────


@app.route("/")
def index():
    stats = db.get_dashboard_stats()
    ports = db.get_all_ports()
    # Render Jinja2 parts first
    from flask import render_template_string
    content_rendered = render_template_string(INDEX_CONTENT, stats=stats, ports=ports)
    # Assemble full page
    html = BASE_TEMPLATE.replace("{title}", "仪表盘") \
        .replace("{dashboard_active}", "active") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", INDEX_JS)
    return html


@app.route("/settings")
def settings():
    config = db.get_all_system_config()
    from flask import render_template_string
    content_rendered = render_template_string(SETTINGS_CONTENT, config=config)
    html = BASE_TEMPLATE.replace("{title}", "系统设置") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
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
    return jsonify(ports)


@app.route("/api/ports", methods=["POST"])
def api_create_port():
    data = request.json
    port_id = db.create_port(
        port_number=data["port"],
        server_name=data.get("server_name", ""),
        server_type=data.get("server_type", "Emby"),
        server_url=data.get("server_url", ""),
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
#  Channel API
# ──────────────────────────────────────────────


@app.route("/api/ports/<int:port_id>/channels", methods=["GET"])
def api_get_channels(port_id):
    channels = db.get_channels(port_id)
    return jsonify(channels)


@app.route("/api/ports/<int:port_id>/channels/<channel_type>", methods=["PUT"])
def api_save_channel(port_id, channel_type):
    data = request.json
    config = data.get("config", {})
    enabled = data.get("enabled", False)
    db.save_channel(port_id, channel_type, config, enabled)
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


@app.route("/api/dnd", methods=["PUT"])
def api_update_dnd():
    data = request.json
    db.update_dnd(
        enabled=data.get("enabled"),
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
    )
    return jsonify({"status": "updated"})


# ──────────────────────────────────────────────
#  Queue API
# ──────────────────────────────────────────────


@app.route("/api/queue", methods=["GET"])
def api_get_queue():
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    messages = db.get_all_messages(limit=limit, offset=offset)
    stats = db.get_queue_stats()
    return jsonify({"messages": messages, "stats": stats})


@app.route("/api/queue/<int:msg_id>", methods=["DELETE"])
def api_delete_message(msg_id):
    db.delete_message(msg_id)
    return jsonify({"status": "deleted"})


@app.route("/api/queue/flush", methods=["POST"])
def api_flush_queue():
    """手动刷新队列，发送所有待处理消息"""
    data = request.json or {}
    port_id = data.get("port_id")
    if port_id:
        count = media.flush_queue_for_port(port_id)
    else:
        # Flush all ports
        count = 0
        for p in db.get_all_ports():
            count += media.flush_queue_for_port(p["id"])
    return jsonify({"status": "flushed", "count": count})


# ──────────────────────────────────────────────
#  Test & Stats
# ──────────────────────────────────────────────


@app.route("/api/ports/<int:port_id>/test", methods=["POST"])
def api_test_port(port_id):
    """发送测试消息"""
    port = db.get_port(port_id)
    if not port:
        return jsonify({"error": "Port not found"}), 404

    enabled_channels = db.get_enabled_channels(port_id)
    if not enabled_channels:
        return jsonify({"error": "No enabled channels"}), 400

    try:
        results = media.send_test_notification(port_id)
        return jsonify({"status": "sent", "results": results})
    except Exception as e:
        log.logger.error(f"Test notification failed: {e}")
        return jsonify({"error": str(e)}), 500


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


# ──────────────────────────────────────────────
#  HTML Templates (embedded)
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
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; scroll-behavior: smooth; }
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
        .modal-header { border-bottom: 1px solid #f0f0f0; }
        .modal-footer { border-top: 1px solid #f0f0f0; }
        .form-label { font-weight: 500; color: #374151; }
        .channel-card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
        .channel-card.enabled { border-color: #3b82f6; background: #f0f7ff; }
        .channel-card .channel-title { font-weight: 600; }
        .queue-status-pending { color: #f59e0b; }
        .queue-status-sent { color: #10b981; }
        .queue-status-failed { color: #ef4444; }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <nav class="sidebar">
        <div class="brand">
            <i class="bi bi-bell-fill"></i> Emby Notifier
        </div>
        <div class="nav flex-column mt-3">
            <a class="nav-link {dashboard_active}" href="#dashboard"><i class="bi bi-speedometer2"></i> 仪表盘</a>
            <a class="nav-link {ports_active}" href="#ports"><i class="bi bi-hdd-network"></i> 端口管理</a>
            <a class="nav-link {dnd_active}" href="#dnd"><i class="bi bi-moon-fill"></i> 勿扰设置</a>
            <a class="nav-link {queue_active}" href="#queue"><i class="bi bi-inbox"></i> 消息队列</a>
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
        <div id="dashboard" class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-speedometer2"></i> 仪表盘</h2>
            <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">
                <i class="bi bi-arrow-clockwise"></i> 刷新
            </button>
        </div>

        <!-- Stats Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="stat-card d-flex align-items-center">
                    <div class="stat-icon bg-primary bg-opacity-10 text-primary me-3">
                        <i class="bi bi-hdd-network"></i>
                    </div>
                    <div>
                        <div class="stat-value">{{ stats.active_ports }}</div>
                        <div class="stat-label">活跃端口</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card d-flex align-items-center">
                    <div class="stat-icon bg-warning bg-opacity-10 text-warning me-3">
                        <i class="bi bi-inbox"></i>
                    </div>
                    <div>
                        <div class="stat-value">{{ stats.queue_pending }}</div>
                        <div class="stat-label">待推送消息</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card d-flex align-items-center">
                    <div class="stat-icon bg-success bg-opacity-10 text-success me-3">
                        <i class="bi bi-check-circle"></i>
                    </div>
                    <div>
                        <div class="stat-value">{{ stats.queue_sent }}</div>
                        <div class="stat-label">已推送</div>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stat-card d-flex align-items-center">
                    <div class="stat-icon {% if stats.dnd_enabled %}bg-warning bg-opacity-10 text-warning{% else %}bg-secondary bg-opacity-10 text-secondary{% endif %} me-3">
                        <i class="bi bi-moon{% if stats.dnd_enabled %}-fill{% endif %}"></i>
                    </div>
                    <div>
                        <div class="stat-value">{% if stats.dnd_enabled %}{{ stats.dnd_start }}-{{ stats.dnd_end }}{% else %}关闭{% endif %}</div>
                        <div class="stat-label">勿扰模式</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Ports Section -->
        <div id="ports" class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center py-3">
                <span><i class="bi bi-hdd-network me-2"></i>端口管理</span>
                <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#portModal" onclick="resetPortForm()">
                    <i class="bi bi-plus-lg"></i> 添加端口
                </button>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>端口号</th>
                                <th>服务器名称</th>
                                <th>类型</th>
                                <th>状态</th>
                                <th>渠道</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for p in ports %}
                            <tr>
                                <td><strong>{{ p.port }}</strong></td>
                                <td>{{ p.server_name or '-' }}</td>
                                <td><span class="badge bg-info">{{ p.server_type }}</span></td>
                                <td>
                                    {% if p.enabled %}
                                    <span class="badge badge-running">运行中</span>
                                    {% else %}
                                    <span class="badge badge-stopped">已停止</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <button class="btn btn-outline-secondary btn-sm" onclick="showChannels({{ p.id }}, '{{ p.server_name }}')">
                                        <i class="bi bi-gear"></i> 配置
                                    </button>
                                </td>
                                <td>
                                    <button class="btn btn-icon btn-outline-primary" title="编辑" onclick="editPort({{ p.id }})">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <button class="btn btn-icon btn-outline-{{ 'warning' if p.enabled else 'success' }}" title="{{ '停止' if p.enabled else '启动' }}" onclick="togglePort({{ p.id }})">
                                        <i class="bi bi-{{ 'pause' if p.enabled else 'play' }}"></i>
                                    </button>
                                    <button class="btn btn-icon btn-outline-info" title="测试推送" onclick="testPort({{ p.id }})">
                                        <i class="bi bi-send"></i>
                                    </button>
                                    <button class="btn btn-icon btn-outline-danger" title="删除" onclick="deletePort({{ p.id }})">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </td>
                            </tr>
                            {% endfor %}
                            {% if not ports %}
                            <tr><td colspan="6" class="text-center text-muted py-4">暂无端口配置，请点击"添加端口"开始</td></tr>
                            {% endif %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- DND Section -->
        <div id="dnd" class="card mb-4">
            <div class="card-header py-3">
                <i class="bi bi-moon-fill me-2"></i>勿扰模式设置
            </div>
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="dndEnabled" {% if stats.dnd_enabled %}checked{% endif %}>
                            <label class="form-check-label" for="dndEnabled">启用勿扰</label>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">开始时间</label>
                        <input type="time" class="form-control" id="dndStart" value="{{ stats.dnd_start }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">结束时间</label>
                        <input type="time" class="form-control" id="dndEnd" value="{{ stats.dnd_end }}">
                    </div>
                    <div class="col-md-3 d-flex align-items-end">
                        <button class="btn btn-primary" onclick="saveDND()">
                            <i class="bi bi-check-lg"></i> 保存
                        </button>
                    </div>
                </div>
                <div class="mt-2">
                    <small class="text-muted">勿扰期间收到的新媒体消息将暂存到队列，勿扰结束后统一推送。</small>
                </div>
            </div>
        </div>

        <!-- Queue Section -->
        <div id="queue" class="card mb-4">
            <div class="card-header d-flex justify-content-between align-items-center py-3">
                <span><i class="bi bi-inbox me-2"></i>消息队列</span>
                <div>
                    <button class="btn btn-success btn-sm" onclick="flushQueue()">
                        <i class="bi bi-send-check"></i> 立即推送全部
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" onclick="loadQueue()">
                        <i class="bi bi-arrow-clockwise"></i> 刷新
                    </button>
                </div>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>端口</th>
                                <th>媒体信息</th>
                                <th>状态</th>
                                <th>创建时间</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="queueBody">
                            <tr><td colspan="6" class="text-center text-muted py-3">加载中...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Port Modal -->
        <div class="modal fade" id="portModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="portModalTitle">添加端口</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="editPortId">
                        <div class="mb-3">
                            <label class="form-label">端口号 <span class="text-danger">*</span></label>
                            <input type="number" class="form-control" id="portNumber" placeholder="例如: 8001" min="1" max="65535">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">服务器名称</label>
                            <input type="text" class="form-control" id="serverName" placeholder="例如: My Emby Server">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">服务器类型</label>
                            <select class="form-select" id="serverType">
                                <option value="Emby">Emby</option>
                                <option value="Jellyfin">Jellyfin</option>
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">服务器 URL</label>
                            <input type="text" class="form-control" id="serverUrl" placeholder="例如: https://emby.example.com">
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="portEnabled" checked>
                            <label class="form-check-label" for="portEnabled">启用</label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="savePort()">保存</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Channel Modal -->
        <div class="modal fade" id="channelModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">推送渠道配置</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="channelModalBody">
                        <!-- WeChat Work -->
                        <div class="channel-card" id="ch-wechat_work">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div class="channel-title"><i class="bi bi-chat-dots-fill text-success me-2"></i>企业微信</div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="wechatEnabled">
                                    <label class="form-check-label" for="wechatEnabled">启用</label>
                                </div>
                            </div>
                            <div class="row g-2">
                                <div class="col-md-6">
                                    <label class="form-label">Corp ID</label>
                                    <input type="text" class="form-control" id="wechatCorpId" placeholder="企业ID">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Corp Secret</label>
                                    <input type="password" class="form-control" id="wechatCorpSecret" placeholder="应用密钥">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Agent ID</label>
                                    <input type="number" class="form-control" id="wechatAgentId" placeholder="应用AgentID">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">User ID</label>
                                    <input type="text" class="form-control" id="wechatUserId" placeholder="用户ID，默认 @all" value="@all">
                                </div>
                            </div>
                        </div>

                        <!-- Telegram -->
                        <div class="channel-card" id="ch-telegram">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div class="channel-title"><i class="bi bi-telegram text-primary me-2"></i>Telegram</div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="tgEnabled">
                                    <label class="form-check-label" for="tgEnabled">启用</label>
                                </div>
                            </div>
                            <div class="row g-2">
                                <div class="col-md-6">
                                    <label class="form-label">Bot Token</label>
                                    <input type="password" class="form-control" id="tgBotToken" placeholder="Bot Token">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Chat ID</label>
                                    <input type="text" class="form-control" id="tgChatId" placeholder="Chat ID">
                                </div>
                            </div>
                        </div>

                        <!-- Bark -->
                        <div class="channel-card" id="ch-bark">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div class="channel-title"><i class="bi bi-phone text-info me-2"></i>Bark (iOS)</div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="barkEnabled">
                                    <label class="form-check-label" for="barkEnabled">启用</label>
                                </div>
                            </div>
                            <div class="row g-2">
                                <div class="col-md-6">
                                    <label class="form-label">Server</label>
                                    <input type="text" class="form-control" id="barkServer" placeholder="https://api.day.app" value="https://api.day.app">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">Device Keys</label>
                                    <input type="text" class="form-control" id="barkDeviceKeys" placeholder="设备Key，多个用逗号分隔">
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="saveChannels()">保存配置</button>
                    </div>
                </div>
            </div>
        </div>
"""

INDEX_JS = """
    <script>
        let currentPortId = null;

        // ── Port Management ──
        function resetPortForm() {
            document.getElementById('portModalTitle').textContent = '添加端口';
            document.getElementById('editPortId').value = '';
            document.getElementById('portNumber').value = '';
            document.getElementById('serverName').value = '';
            document.getElementById('serverType').value = 'Emby';
            document.getElementById('serverUrl').value = '';
            document.getElementById('portEnabled').checked = true;
        }

        async function editPort(portId) {
            const ports = await api('/api/ports');
            const p = ports.find(x => x.id === portId);
            if (!p) return;
            document.getElementById('portModalTitle').textContent = '编辑端口';
            document.getElementById('editPortId').value = p.id;
            document.getElementById('portNumber').value = p.port;
            document.getElementById('serverName').value = p.server_name;
            document.getElementById('serverType').value = p.server_type;
            document.getElementById('serverUrl').value = p.server_url || '';
            document.getElementById('portEnabled').checked = !!p.enabled;
            new bootstrap.Modal(document.getElementById('portModal')).show();
        }

        async function savePort() {
            const editId = document.getElementById('editPortId').value;
            const data = {
                port: parseInt(document.getElementById('portNumber').value),
                server_name: document.getElementById('serverName').value,
                server_type: document.getElementById('serverType').value,
                server_url: document.getElementById('serverUrl').value,
                enabled: document.getElementById('portEnabled').checked ? 1 : 0,
            };
            if (!data.port) { showToast('请输入端口号', 'danger'); return; }

            if (editId) {
                await apiPut(`/api/ports/${editId}`, data);
                showToast('端口已更新');
            } else {
                const res = await api('/api/ports', 'POST', data);
                if (res.error) { showToast(res.error, 'danger'); return; }
                showToast('端口已创建');
            }
            bootstrap.Modal.getInstance(document.getElementById('portModal')).hide();
            setTimeout(() => location.reload(), 500);
        }

        async function togglePort(portId) {
            await apiPost(`/api/ports/${portId}/toggle`);
            showToast('状态已切换');
            setTimeout(() => location.reload(), 500);
        }

        async function deletePort(portId) {
            if (!confirm('确定要删除此端口及其所有配置吗？')) return;
            await apiDelete(`/api/ports/${portId}`);
            showToast('端口已删除');
            setTimeout(() => location.reload(), 500);
        }

        async function testPort(portId) {
            showToast('正在发送测试消息（电影+剧集）...', 'info');
            const res = await apiPost(`/api/ports/${portId}/test`);
            if (res.error) { showToast(res.error, 'danger'); return; }
            
            // 解析结果
            const results = res.results || {};
            const successCount = Object.values(results).filter(v => v === 'success').length;
            const errorCount = Object.keys(results).filter(k => k.includes('error')).length;
            
            if (errorCount === 0) {
                showToast(`✅ 测试消息发送成功！共 ${successCount} 条`, 'success');
            } else {
                const errors = Object.entries(results)
                    .filter(([k, v]) => k.includes('error'))
                    .map(([k, v]) => `${k}: ${v}`)
                    .join('<br>');
                showToast(`⚠️ 部分发送失败<br>${errors}`, 'warning');
            }
        }

        // ── Channel Management ──
        async function showChannels(portId, serverName) {
            currentPortId = portId;
            const channels = await api(`/api/ports/${portId}/channels`);
            const chMap = {};
            channels.forEach(c => chMap[c.channel_type] = c);

            // WeChat Work
            const wechat = chMap['wechat_work'] || {config: {}, enabled: 0};
            document.getElementById('wechatEnabled').checked = !!wechat.enabled;
            document.getElementById('wechatCorpId').value = wechat.config.corp_id || '';
            document.getElementById('wechatCorpSecret').value = wechat.config.corp_secret || '';
            document.getElementById('wechatAgentId').value = wechat.config.agent_id || '';
            document.getElementById('wechatUserId').value = wechat.config.user_id || '@all';
            document.getElementById('ch-wechat_work').className = wechat.enabled ? 'channel-card enabled' : 'channel-card';

            // Telegram
            const tg = chMap['telegram'] || {config: {}, enabled: 0};
            document.getElementById('tgEnabled').checked = !!tg.enabled;
            document.getElementById('tgBotToken').value = tg.config.bot_token || '';
            document.getElementById('tgChatId').value = tg.config.chat_id || '';
            document.getElementById('ch-telegram').className = tg.enabled ? 'channel-card enabled' : 'channel-card';

            // Bark
            const barkCh = chMap['bark'] || {config: {}, enabled: 0};
            document.getElementById('barkEnabled').checked = !!barkCh.enabled;
            document.getElementById('barkServer').value = barkCh.config.server || 'https://api.day.app';
            document.getElementById('barkDeviceKeys').value = barkCh.config.device_keys || '';
            document.getElementById('ch-bark').className = barkCh.enabled ? 'channel-card enabled' : 'channel-card';

            document.getElementById('channelModal').querySelector('.modal-title').textContent =
                '推送渠道配置 - ' + serverName;
            new bootstrap.Modal(document.getElementById('channelModal')).show();
        }

        async function saveChannels() {
            if (!currentPortId) return;

            // Save WeChat
            await apiPut(`/api/ports/${currentPortId}/channels/wechat_work`, {
                enabled: document.getElementById('wechatEnabled').checked,
                config: {
                    corp_id: document.getElementById('wechatCorpId').value,
                    corp_secret: document.getElementById('wechatCorpSecret').value,
                    agent_id: document.getElementById('wechatAgentId').value,
                    user_id: document.getElementById('wechatUserId').value || '@all',
                }
            });

            // Save Telegram
            await apiPut(`/api/ports/${currentPortId}/channels/telegram`, {
                enabled: document.getElementById('tgEnabled').checked,
                config: {
                    bot_token: document.getElementById('tgBotToken').value,
                    chat_id: document.getElementById('tgChatId').value,
                }
            });

            // Save Bark
            await apiPut(`/api/ports/${currentPortId}/channels/bark`, {
                enabled: document.getElementById('barkEnabled').checked,
                config: {
                    server: document.getElementById('barkServer').value || 'https://api.day.app',
                    device_keys: document.getElementById('barkDeviceKeys').value,
                }
            });

            showToast('渠道配置已保存');
            bootstrap.Modal.getInstance(document.getElementById('channelModal')).hide();
        }

        // ── DND Management ──
        async function saveDND() {
            await apiPut('/api/dnd', {
                enabled: document.getElementById('dndEnabled').checked ? 1 : 0,
                start_time: document.getElementById('dndStart').value,
                end_time: document.getElementById('dndEnd').value,
            });
            showToast('勿扰设置已保存');
        }

        // ── Queue Management ──
        async function loadQueue() {
            const data = await api('/api/queue');
            const tbody = document.getElementById('queueBody');
            if (!data.messages || data.messages.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">暂无队列消息</td></tr>';
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

        // ── Init ──
        document.addEventListener('DOMContentLoaded', () => {
            loadQueue();
            // Auto-refresh queue every 30s
            setInterval(loadQueue, 30000);
        });
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
                    <li>在"端口管理"中添加 Emby/Jellyfin 服务器的 Webhook 端口</li>
                    <li>为每个端口配置推送渠道（企业微信/Telegram/Bark）</li>
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
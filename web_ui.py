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
import port_manager as pm_module
from version import __version__
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
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "") \
        .replace("{templates_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", INDEX_JS)
    return html


@app.route("/ports")
def ports_page():
    """端口管理页面"""
    ports = db.get_all_ports()
    for p in ports:
        p["channels"] = db.get_channels(p["id"])
    wechat_configs = db.get_all_wechat_configs()
    all_channels = db.get_all_channels()
    from flask import render_template_string
    all_templates = db.get_templates()
    template_names = {t["id"]: t["name"] for t in all_templates}
    templates = [t for t in all_templates if not t.get("is_fallback")]
    content_rendered = render_template_string(PORTS_CONTENT, ports=ports, wechat_configs=wechat_configs, templates=templates, template_names=template_names, all_channels=all_channels)
    html = BASE_TEMPLATE.replace("{title}", "端口管理") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "active") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "") \
        .replace("{templates_active}", "") \
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
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "") \
        .replace("{templates_active}", "") \
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
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "") \
        .replace("{templates_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", QUEUE_JS)
    return html


@app.route("/wechat")
def wechat_page():
    """企业微信配置页面"""
    wechat_configs = db.get_all_wechat_configs()
    from flask import render_template_string
    import json as _json
    wechat_configs_json = _json.dumps(wechat_configs, default=str)
    content_rendered = render_template_string(WECHAT_CONTENT, wechat_configs=wechat_configs, wechat_configs_json=wechat_configs_json)
    html = BASE_TEMPLATE.replace("{title}", "企业微信配置") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "active") \
        .replace("{templates_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", WECHAT_JS.replace("{{ wechat_configs_json|safe }}", wechat_configs_json))
    return html
@app.route("/channels")
def channels_page():
    """通道管理页面"""
    channels = db.get_all_channels()
    from flask import render_template_string
    import json as _json
    channels_json = _json.dumps(channels, default=str)
    content_rendered = render_template_string(CHANNELS_CONTENT, channels=channels, channels_json=channels_json)
    html = BASE_TEMPLATE.replace("{title}", "推送通道") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "") \
        .replace("{channels_active}", "active") \
        .replace("{templates_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", CHANNELS_JS.replace("{{ channels_json|safe }}", channels_json))
    return html

@app.route("/logs")
def logs_page():
    """系统日志页面"""
    from flask import render_template_string
    content_rendered = render_template_string(LOGS_CONTENT)
    html = BASE_TEMPLATE.replace("{title}", "系统日志") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{logs_active}", "active") \
        .replace("{channels_active}", "") \
        .replace("{templates_active}", "") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", LOGS_JS)
    return html
@app.route("/templates")
def templates_page():
    """推送模板页面"""
    from flask import render_template_string
    templates = db.get_templates()
    content_rendered = render_template_string(TEMPLATES_CONTENT, templates=templates)
    html = BASE_TEMPLATE.replace("{title}", "推送模板") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "") \
        .replace("{templates_active}", "active") \
        .replace("{settings_active}", "") \
        .replace("{content}", content_rendered) \
        .replace("{extra_js}", TEMPLATES_JS)
    return html








@app.route("/settings")
def settings():
    """系统设置页面"""
    import os as _os
    config = db.get_all_system_config()
    ports = db.get_all_ports()
    from flask import render_template_string
    content_rendered = render_template_string(
        SETTINGS_CONTENT,
        config=config,
        version=__version__,
        port_count=len(ports),
        db_path=_os.getenv("DB_PATH", "emby_notifier.db"),
    )
    html = BASE_TEMPLATE.replace("{title}", "系统设置") \
        .replace("{dashboard_active}", "") \
        .replace("{ports_active}", "") \
        .replace("{dnd_active}", "") \
        .replace("{queue_active}", "") \
        .replace("{logs_active}", "") \
        .replace("{channels_active}", "") \
        .replace("{templates_active}", "") \
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
    port_number = data["port"]
    
    # 检查端口是否被占用
    ok, err = pm_module.check_port_available(port_number)
    if not ok:
        return jsonify({"error": err}), 400
    
    port_id = db.create_port(
        port_number=port_number,
        server_name=data.get("server_name", ""),
        server_url=data.get("server_url", ""),
        template_id=data.get("template_id", 1),
        channel_ids=data.get("channel_ids", []),
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

    # 如果端口号变更，检查新端口是否可用
    new_port = data.get("port", old_port["port"])
    if new_port != old_port["port"]:
        ok, err = pm_module.check_port_available(new_port)
        if not ok:
            return jsonify({"error": err}), 400

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
#  Channel API (多通道管理)
# ──────────────────────────────────────────────


@app.route("/api/channels", methods=["GET"])
def api_get_all_channels():
    channels = db.get_all_channels()
    return jsonify(channels)


@app.route("/api/channels", methods=["POST"])
def api_create_channel():
    data = request.json
    channel_id = db.create_channel(
        name=data.get("name", ""),
        channel_type=data.get("type", ""),
        config=json.dumps(data.get("config", {})),
        enabled=data.get("enabled", 1),
    )
    return jsonify({"id": channel_id})


@app.route("/api/channels/<int:channel_id>", methods=["PUT"])
def api_update_channel(channel_id):
    data = request.json
    db.update_channel(
        channel_id,
        name=data.get("name"),
        channel_type=data.get("type"),
        config=json.dumps(data["config"]) if "config" in data else None,
        enabled=data.get("enabled"),
    )
    return jsonify({"status": "updated"})


@app.route("/api/channels/<int:channel_id>", methods=["DELETE"])
def api_delete_channel(channel_id):
    db.delete_channel(channel_id)
    return jsonify({"status": "deleted"})


@app.route("/api/channels/<int:channel_id>/duplicate", methods=["POST"])
def api_duplicate_channel(channel_id):
    """复制通道"""
    ch = db.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Channel not found"}), 404
    new_id = db.create_channel(
        name=ch["name"] + " (副本)",
        channel_type=ch["type"],
        config=ch["config"],
        enabled=0,  # 复制后默认禁用，避免重复推送
    )
    return jsonify({"id": new_id})


@app.route("/api/channels/<int:channel_id>/test", methods=["POST"])
def api_test_channel(channel_id):
    """测试通道连通性"""
    ch = db.get_channel(channel_id)
    if not ch:
        return jsonify({"error": "Channel not found"}), 404
    
    try:
        config = json.loads(ch["config"]) if isinstance(ch["config"], str) else ch["config"]
        from channels import create_channel
        channel = create_channel(ch["type"], config)
        ok = channel.test()
        if ok:
            log.logger.debug(f"Channel test successful: {ch['name']} ({ch['type']})")
            return jsonify({"success": True, "message": "测试成功"})
        else:
            log.logger.error(f"Channel test failed: {ch['name']} ({ch['type']})")
            return jsonify({"success": False, "message": "测试失败，请检查配置"})
    except Exception as e:
        log.logger.error(f"Channel test error: {ch['name']} - {e}")
        return jsonify({"success": False, "error": str(e)})


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
    """Flush pending/failed messages (trigger send)"""
    count = 0
    for p in db.get_all_ports():
        if p["enabled"]:
            try:
                n = media.flush_queue_for_port(p["id"])
                count += n
            except Exception as e:
                log.logger.error(f"[Port {p['port']}] Flush error: {e}")
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
    
    channel_ids = json.loads(port.get("channel_ids", "[]")) if port else []
    if not channel_ids:
        return jsonify({"error": "没有配置推送通道"}), 400
    
    try:
        results = media.send_test_notification(port_id)
        # 检查实际结果
        errors = [v for k, v in results.items() if k.endswith("_error")]
        success_count = len([v for k, v in results.items() if v == "success"])
        failed_count = len(errors)
        if failed_count > 0:
            return jsonify({
                "success": success_count,
                "failed": failed_count,
                "total": success_count + failed_count,
                "errors": errors
            }), 200
        return jsonify({"success": success_count, "failed": 0, "total": success_count})
    except Exception as e:
        log.logger.error(f"Test push failed: {e}")
        return jsonify({"error": str(e), "success": 0, "failed": 1, "total": 1}), 500


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
@app.route("/api/logs", methods=["GET"])
def api_get_logs():
    level = request.args.get("level")
    limit = request.args.get("limit", 100, type=int)
    logs = db.get_logs(level=level, limit=limit)
    return jsonify(logs)

@app.route("/api/logs", methods=["DELETE"])
def api_clear_logs():
    db.clear_logs()
    return jsonify({"status": "cleared"})


@app.route("/api/logs/export")
def api_export_logs():
    """导出完整日志为文本文件"""
    from flask import Response
    from datetime import datetime
    
    logs = db.get_logs(limit=10000)
    lines = []
    for log in logs:
        timestamp = log.get("timestamp", "")
        level = log.get("level", "")
        module = log.get("module", "")
        message = log.get("message", "")
        lines.append(f"[{timestamp}] [{level}] [{module}] {message}")
    
    content = "\n".join(lines)
    filename = f"emby_notifier_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
@app.route("/api/templates", methods=["GET"])
def api_get_templates():
    return jsonify(db.get_templates())

@app.route("/api/templates", methods=["POST"])
def api_create_template():
    data = request.json
    tid = db.create_template(
        name=data.get("name", ""),
        title=data.get("title", ""),
        description=data.get("description", ""),
        picurl_movie=data.get("picurl_movie", "media_backdrop"),
        picurl_episode=data.get("picurl_episode", "media_still"),
        enable_image=data.get("enable_image", 1),
    )
    return jsonify({"id": tid})

@app.route("/api/templates/<int:template_id>", methods=["PUT"])
def api_update_template(template_id):
    data = request.json
    t = db.get_template(template_id)
    # 回退模板强制关闭图片
    if t and t.get("is_fallback"):
        data["enable_image"] = 0
    db.update_template(template_id, **data)
    return jsonify({"status": "updated"})

@app.route("/api/templates/<int:template_id>", methods=["DELETE"])
def api_delete_template(template_id):
    t = db.get_template(template_id)
    if t and t.get("is_fallback"):
        return jsonify({"error": "回退模板不可删除"}), 400
    db.delete_template(template_id)
    return jsonify({"status": "deleted"})








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
            <a class="nav-link {logs_active}" href="/logs"><i class="bi bi-list-ul"></i> 系统日志</a>
            <a class="nav-link {channels_active}" href="/channels"><i class="bi bi-broadcast"></i> 推送通道</a>
            <a class="nav-link {templates_active}" href="/templates"><i class="bi bi-file-earmark-text"></i> 推送模板</a>
            <a class="nav-link {settings_active}" href="/settings"><i class="bi bi-gear-fill"></i> 系统设置</a>
        </div>
        <div style="position:absolute;bottom:16px;left:0;right:0;text-align:center;">
            <small class="text-muted">{version}</small>
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

# Inject current version into the base template
BASE_TEMPLATE = BASE_TEMPLATE.replace("{version}", f"v{__version__}")

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
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for port in ports %}
                        <tr>
                            <td><code>{{ port.port }}</code></td>
                            <td>{{ port.server_name }}</td>
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
                            <th>推送模板</th>
                            <th>推送通道</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="portsTable">
                        {% for port in ports %}
                        <tr data-port-id="{{ port.id }}">
                            <td>{{ port.server_name }}</td>
                            <td><code>{{ port.port }}</code></td>
                            <td>{{ template_names.get(port.template_id, '标准') }}</td>
                            <td>
                                {% if port.channels %}
                                    {% for ch in port.channels %}
                                        <span class="badge bg-{% if ch.type == 'wechat_work_api' %}primary{% elif ch.type == 'wechat_work_bot' %}success{% elif ch.type == 'dingtalk' %}info{% elif ch.type == 'feishu' %}warning text-dark{% elif ch.type == 'telegram_bot' %}secondary{% elif ch.type == 'bark' %}dark{% else %}secondary{% endif %} me-1">{{ ch.name }}</span>
                                    {% endfor %}
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
                                <label class="form-label">推送通道</label>
                                <div id="portChannelList" class="border rounded p-2" style="max-height: 200px; overflow-y: auto;">
                                    {% for ch in all_channels %}
                                    <div class="form-check">
                                        <input class="form-check-input port-channel-check" type="checkbox" value="{{ ch.id }}" id="portCh{{ ch.id }}">
                                        <label class="form-check-label" for="portCh{{ ch.id }}">
                                            {{ ch.name }}
                                            {% if ch.type == 'wechat_work_api' %}
                                                <span class="badge bg-primary">企微应用</span>
                                            {% elif ch.type == 'wechat_work_bot' %}
                                                <span class="badge bg-success">企微机器人</span>
                                            {% elif ch.type == 'dingtalk' %}
                                                <span class="badge bg-info">钉钉</span>
                                            {% elif ch.type == 'feishu' %}
                                                <span class="badge bg-warning text-dark">飞书</span>
                                            {% elif ch.type == 'telegram_bot' %}
                                                <span class="badge bg-secondary">Telegram</span>
                                            {% elif ch.type == 'bark' %}
                                                <span class="badge bg-dark">Bark</span>
                                            {% endif %}
                                        </label>
                                    </div>
                                    {% endfor %}
                                </div>
                                <div class="form-text">可多选，同时推送到多个通道</div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">推送模板</label>
                                <select class="form-select" id="addPortTemplate">
                                    {% for t in templates %}
                                    <option value="{{ t.id }}">{{ t.name }}</option>
                                    {% endfor %}
                                </select>
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
            
            if (!name || !port) {
                showToast('请填写组名和端口号', 'danger');
                return;
            }
            
            // 获取选中的通道 IDs
            const channelIds = Array.from(document.querySelectorAll('.port-channel-check:checked')).map(cb => parseInt(cb.value));
            
            const data = {
                port: port,
                server_name: name,
                channel_ids: channelIds,
                template_id: parseInt(document.getElementById('addPortTemplate').value) || 1,
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
            const ports = await api('/api/ports');
            const port = ports.find(p => p.id === portId);
            if (!port) { showToast('端口不存在', 'danger'); return; }
            
            // Switch modal title to edit mode
            document.querySelector('#addPortModal .modal-title').textContent = '编辑端口';
            document.getElementById('addPortName').value = port.server_name || '';
            document.getElementById('addPortNumber').value = port.port || '';
            // 设置通道选中状态
            const portChannelIds = port.channel_ids ? (typeof port.channel_ids === 'string' ? JSON.parse(port.channel_ids) : port.channel_ids) : [];
            document.querySelectorAll('.port-channel-check').forEach(cb => {
                cb.checked = portChannelIds.includes(parseInt(cb.value));
            });
            document.getElementById('addPortTemplate').value = port.template_id || '1';
            
            // Change save button behavior to update instead of create
            const saveBtn = document.querySelector('#addPortModal .btn-primary');
            saveBtn.onclick = async function() {
                const channelIds = Array.from(document.querySelectorAll('.port-channel-check:checked')).map(cb => parseInt(cb.value));
                const data = {
                    port: parseInt(document.getElementById('addPortNumber').value),
                    server_name: document.getElementById('addPortName').value.trim(),
                    channel_ids: channelIds,
                    template_id: parseInt(document.getElementById('addPortTemplate').value) || 1,
                };
                if (!data.server_name || !data.port) { showToast('请填写组名和端口号', 'danger'); return; }
                const res = await apiPut('/api/ports/' + portId, data);
                if (res.error) { showToast('更新失败: ' + res.error, 'danger'); }
                else { showToast('端口已更新'); bootstrap.Modal.getInstance(document.getElementById('addPortModal')).hide(); setTimeout(() => location.reload(), 500); }
            };
            
            new bootstrap.Modal(document.getElementById('addPortModal')).show();
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
            } else if (res.failed > 0) {
                const errList = (res.errors || []).join(', ');
                showToast(`测试完成: ${res.success} 成功, ${res.failed} 失败 — ${errList}`, 'warning');
            } else {
                showToast(`测试完成: ${res.success} 个全部成功`);
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
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addWechatModal" onclick="resetWechatModal()">
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
                        <h5 class="modal-title" id="addWechatModalTitle">添加企业微信配置</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="editWechatId" value="">
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
        // 企业微信配置数据（供编辑使用）
        const wechatConfigsData = {{ wechat_configs_json|safe }};
        
        async function saveWechatConfig() {
            const editId = document.getElementById('editWechatId').value;
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
            
            let res;
            if (editId) {
                res = await apiPut(`/api/wechat-configs/${editId}`, data);
            } else {
                res = await apiPost('/api/wechat-configs', data);
            }
            
            if (res.error) {
                showToast('保存失败: ' + res.error, 'danger');
            } else {
                showToast(editId ? '配置已更新' : '配置组已创建');
                setTimeout(() => location.reload(), 500);
            }
        }
        
        function editWechatConfig(configId) {
            const cfg = wechatConfigsData.find(c => c.id === configId);
            if (!cfg) { showToast('配置未找到', 'danger'); return; }
            
            document.getElementById('editWechatId').value = cfg.id;
            document.getElementById('addWechatName').value = cfg.name || '';
            document.getElementById('addWechatCorpId').value = cfg.corp_id || '';
            document.getElementById('addWechatSecret').value = cfg.corp_secret || '';
            document.getElementById('addWechatAgentId').value = cfg.agent_id || 0;
            document.getElementById('addWechatModalTitle').textContent = '编辑企业微信配置';
            
            new bootstrap.Modal(document.getElementById('addWechatModal')).show();
        }
        
        function resetWechatModal() {
            document.getElementById('editWechatId').value = '';
            document.getElementById('addWechatName').value = '';
            document.getElementById('addWechatCorpId').value = '';
            document.getElementById('addWechatSecret').value = '';
            document.getElementById('addWechatAgentId').value = '';
            document.getElementById('addWechatModalTitle').textContent = '添加企业微信配置';
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
                    <li>在"推送通道"页面添加推送通道（企微、钉钉、飞书等）</li>
                    <li>在"端口管理"中添加端口，选择推送通道</li>
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

        <div class="card mt-4">
            <div class="card-header py-3">
                <i class="bi bi-info-circle-fill me-2"></i>系统信息
            </div>
            <div class="card-body">
                <table class="table table-borderless mb-0">
                    <tr><td class="text-muted" style="width:120px">版本</td><td><code>v{{ version }}</code></td></tr>
                    <tr><td class="text-muted">仓库</td><td><a href="https://github.com/codename-test/Emby_Notifier_WebUI" target="_blank">codename-test/Emby_Notifier_WebUI</a></td></tr>
                    <tr><td class="text-muted">作者</td><td>codename-test</td></tr>
                    <tr><td class="text-muted">端口数</td><td>{{ port_count }}</td></tr>
                    <tr><td class="text-muted">数据库</td><td><code class="text-muted small">{{ db_path }}</code></td></tr>
                </table>
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



LOGS_CONTENT = """
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-list-ul"></i> 系统日志</h2>
            <div>
                <select class="form-select form-select-sm d-inline-block w-auto me-2" id="logLevelFilter" onchange="loadLogs()">
                    <option value="">全部级别</option>
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO" selected>INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                    <option value="CRITICAL">CRITICAL</option>
                </select>
                <button class="btn btn-outline-danger btn-sm" onclick="clearLogs()">
                    <i class="bi bi-trash"></i> 清空日志
                </button>
            </div>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-hover font-monospace small">
                <thead>
                    <tr>
                        <th style="width:160px">时间</th>
                        <th style="width:80px">级别</th>
                        <th style="width:120px">模块</th>
                        <th>消息 <small class="text-muted">(点击展开/复制)</small></th>
                    </tr>
                </thead>
                <tbody id="logTableBody">
                    <tr><td colspan="4" class="text-center text-muted">加载中...</td></tr>
                </tbody>
            </table>
        </div>
        <!-- 日志详情弹窗 -->
        <div class="modal fade" id="logDetailModal" tabindex="-1">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header py-2">
                        <h6 class="modal-title">日志详情</h6>
                        <div>
                            <button class="btn btn-sm btn-outline-primary me-2" onclick="copyLogDetail()">
                                <i class="bi bi-clipboard"></i> 复制
                            </button>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                    </div>
                    <div class="modal-body">
                        <textarea id="logDetailContent" class="bg-light p-3 rounded form-control" readonly style="white-space:pre-wrap;word-break:break-all;font-size:0.85rem;max-height:60vh;overflow-y:auto;resize:none;border:none;height:60vh;font-family:SFMono-Regular,Menlo,Monaco,Consolas,monospace" onclick="this.select()"></textarea>
                    </div>
                </div>
            </div>
        </div>
"""

LOGS_JS = """
    <script>
        const levelColors = {
            'DEBUG': 'secondary',
            'INFO': 'primary',
            'WARNING': 'warning',
            'ERROR': 'danger',
            'CRITICAL': 'dark'
        };

        let currentLogMessage = '';

        async function loadLogs() {
            const level = document.getElementById('logLevelFilter').value;
            const url = level ? '/api/logs?level=' + level + '&limit=200' : '/api/logs?limit=200';
            const logs = await api(url);
            const tbody = document.getElementById('logTableBody');
            if (!logs || logs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">暂无日志</td></tr>';
                return;
            }
            tbody.innerHTML = logs.map((l, idx) => {
                const ts = l.timestamp ? l.timestamp.replace('T', ' ').substring(0, 19) : '';
                const color = levelColors[l.level] || 'secondary';
                const msg = l.message || '';
                const shortMsg = msg.length > 100 ? msg.substring(0, 100) + '...' : msg;
                return '<tr style="cursor:pointer" onclick="showLogDetail(' + idx + ')">' +
                    '<td class="text-nowrap">' + ts + '</td>' +
                    '<td><span class="badge bg-' + color + '">' + (l.level || '') + '</span></td>' +
                    '<td>' + (l.module || '') + '</td>' +
                    '<td style="word-break:break-all">' + shortMsg.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</td>' +
                    '</tr>';
            }).join('');
            window._logMessages = logs.map(l => l.message || '');
        }

        function showLogDetail(idx) {
            currentLogMessage = window._logMessages[idx] || '';
            document.getElementById('logDetailContent').textContent = currentLogMessage;
            new bootstrap.Modal(document.getElementById('logDetailModal')).show();
        }

        function copyLogDetail() {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(currentLogMessage).then(() => {
                    showToast('已复制到剪贴板');
                }).catch(() => {
                    fallbackCopy();
                });
            } else {
                fallbackCopy();
            }
        }
        function fallbackCopy() {
            const textarea = document.createElement('textarea');
            textarea.value = currentLogMessage;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                showToast('已复制到剪贴板');
            } catch (e) {
                showToast('复制失败', 'danger');
            }
            document.body.removeChild(textarea);
        }

        async function clearLogs() {
            if (!confirm('确定要清空所有日志吗？')) return;
            await apiDelete('/api/logs');
            showToast('日志已清空');
            loadLogs();
        }

        loadLogs();
        setInterval(loadLogs, 5000);
    </script>
"""



TEMPLATES_CONTENT = """
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-file-earmark-text"></i> 推送模板</h2>
            <button class="btn btn-primary" onclick="openAddTemplate()">
                <i class="bi bi-plus-lg"></i> 添加模板
            </button>
        </div>

        <div class="alert alert-info small mb-3">
            <i class="bi bi-info-circle-fill"></i> 
            <strong>回退模板</strong>：当 TMDB 获取媒体详情失败时（如未收录的影片），自动切换到标记为 <span class="badge bg-warning text-dark">回退</span> 的模板推送。回退模板不可删除、不可在端口下拉中选择、封面图强制关闭。
        </div>

        <div class="row" id="templateCards">
            {% for t in templates %}
            <div class="col-md-6 mb-3">
                <div class="card{% if t.is_fallback %} border-warning{% endif %}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h5 class="card-title mb-0">
                                {{ t.name }}
                                {% if t.is_fallback %}<span class="badge bg-warning text-dark ms-1">回退</span>{% endif %}
                                {% if not t.get('enable_image', 1) %}<span class="badge bg-secondary ms-1">无图</span>{% endif %}
                            </h5>
                            <div>
                                <button class="btn btn-icon btn-outline-primary btn-sm" onclick="openEditTemplate({{ t.id }})" title="\u7f16\u8f91"><i class="bi bi-pencil"></i></button>
                                {% if not t.is_fallback %}
                                <button class="btn btn-icon btn-outline-danger btn-sm" onclick="deleteTemplate({{ t.id }})" title="\u5220\u9664"><i class="bi bi-trash"></i></button>
                                {% endif %}
                            </div>
                        </div>
                        <p class="text-muted small mb-1"><strong>\u6807\u9898\uff1a</strong>{{ t.title }}</p>
                        <pre class="bg-light p-2 rounded small mb-0" style="max-height:120px;overflow-y:auto">{{ t.description }}</pre>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Edit Template Modal -->
        <div class="modal fade" id="editTemplateModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="editTemplateModalTitle">\u7f16\u8f91\u6a21\u677f</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="editTemplateId">
                        <div class="mb-3">
                            <label class="form-label">\u6a21\u677f\u540d\u79f0 *</label>
                            <input type="text" class="form-control" id="editTemplateName" placeholder="\u4f8b\u5982\uff1a\u5f71\u89c6\u66f4\u65b0">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">\u6807\u9898\u6a21\u677f</label>
                            <input type="text" class="form-control" id="editTemplateTitle" placeholder="\u652f\u6301\u53d8\u91cf\uff1a{type} {name} {year} \u7b49">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">\u63cf\u8ff0\u6a21\u677f</label>
                            <textarea class="form-control" id="editTemplateDesc" rows="6" placeholder="\u652f\u6301\u53d8\u91cf\uff1a{type} {name} {year} {episode} {date} {rating} {intro} {tmdb_url} {season} {ep_num} {ep_name}"></textarea>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">\u7535\u5f71\u5c01\u9762\u56fe\u5b57\u6bb5</label>
                                <select class="form-select" id="editPicMovie">
                                    <option value="media_backdrop">media_backdrop (\u80cc\u666f\u56fe)</option>
                                    <option value="media_poster">media_poster (\u6d77\u62a5)</option>
                                    <option value="media_still">media_still (\u5267\u7167)</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">\u5267\u96c6\u5c01\u9762\u56fe\u5b57\u6bb5</label>
                                <select class="form-select" id="editPicEpisode">
                                    <option value="media_still">media_still (\u5267\u7167)</option>
                                    <option value="media_backdrop">media_backdrop (\u80cc\u666f\u56fe)</option>
                                    <option value="media_poster">media_poster (\u6d77\u62a5)</option>
                                </select>
                            </div>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="editEnableImage" checked>
                            <label class="form-check-label" for="editEnableImage">启用封面图片</label>
                        </div>
                        <div class="bg-light p-2 rounded small">
                            <strong>\u53ef\u7528\u53d8\u91cf\uff1a</strong>
                            <code>{type}</code> \u7535\u5f71/\u5267\u96c6
                            <code>{name}</code> \u540d\u79f0
                            <code>{year}</code> \u5e74\u4efd
                            <code>{episode}</code> \u5b63\u00b7\u96c6\uff08\u4ec5\u5267\u96c6\u6709\u503c\uff09
                            <code>{date}</code> \u4e0a\u6620\u65e5\u671f
                            <code>{rating}</code> \u8bc4\u5206
                            <code>{intro}</code> \u7b80\u4ecb
                            <code>{tmdb_url}</code> TMDB\u94fe\u63a5
                            <code>{season}</code> \u5b63\u53f7
                            <code>{ep_num}</code> \u96c6\u53f7
                            <code>{ep_name}</code> \u96c6\u540d
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">\u53d6\u6d88</button>
                        <button type="button" class="btn btn-primary" onclick="saveTemplate()">\u4fdd\u5b58</button>
                    </div>
                </div>
            </div>
        </div>
"""

TEMPLATES_JS = """
    <script>
        function openAddTemplate() {
            document.getElementById('editTemplateModalTitle').textContent = '\u6dfb\u52a0\u6a21\u677f';
            document.getElementById('editTemplateId').value = '';
            document.getElementById('editTemplateName').value = '';
            document.getElementById('editTemplateTitle').value = '';
            document.getElementById('editTemplateDesc').value = '';
            document.getElementById('editPicMovie').value = 'media_backdrop';
            document.getElementById('editPicEpisode').value = 'media_still';
            document.getElementById('editEnableImage').checked = true;
            document.getElementById('editEnableImage').disabled = false;
            new bootstrap.Modal(document.getElementById('editTemplateModal')).show();
        }

        async function openEditTemplate(id) {
            const res = await api('/api/templates');
            const t = res.find(x => x.id === id);
            if (!t) { showToast('\u6a21\u677f\u4e0d\u5b58\u5728', 'danger'); return; }
            document.getElementById('editTemplateModalTitle').textContent = '\u7f16\u8f91\u6a21\u677f';
            document.getElementById('editTemplateId').value = t.id;
            document.getElementById('editTemplateName').value = t.name || '';
            document.getElementById('editTemplateTitle').value = t.title || '';
            document.getElementById('editTemplateDesc').value = t.description || '';
            document.getElementById('editPicMovie').value = t.picurl_movie || 'media_backdrop';
            document.getElementById('editPicEpisode').value = t.picurl_episode || 'media_still';
            document.getElementById('editEnableImage').checked = t.enable_image !== 0;
            // 回退模板禁用图片
            document.getElementById('editEnableImage').disabled = !!t.is_fallback;
            new bootstrap.Modal(document.getElementById('editTemplateModal')).show();
        }

        async function saveTemplate() {
            const id = document.getElementById('editTemplateId').value;
            const data = {
                name: document.getElementById('editTemplateName').value.trim(),
                title: document.getElementById('editTemplateTitle').value.trim(),
                description: document.getElementById('editTemplateDesc').value,
                picurl_movie: document.getElementById('editPicMovie').value,
                picurl_episode: document.getElementById('editPicEpisode').value,
                enable_image: document.getElementById('editEnableImage').checked ? 1 : 0
            };
            if (!data.name) { showToast('\u8bf7\u8f93\u5165\u6a21\u677f\u540d\u79f0', 'danger'); return; }
            let res;
            if (id) { res = await apiPut('/api/templates/' + id, data); }
            else { res = await apiPost('/api/templates', data); }
            if (res.error) { showToast('\u64cd\u4f5c\u5931\u8d25: ' + res.error, 'danger'); return; }
            showToast(id ? '\u6a21\u677f\u5df2\u66f4\u65b0' : '\u6a21\u677f\u5df2\u521b\u5efa');
            bootstrap.Modal.getInstance(document.getElementById('editTemplateModal')).hide();
            setTimeout(() => location.reload(), 500);
        }

        async function deleteTemplate(id) {
            if (!confirm('\u786e\u5b9a\u8981\u5220\u9664\u6b64\u6a21\u677f\u5417\uff1f')) return;
            await apiDelete('/api/templates/' + id);
            showToast('\u6a21\u677f\u5df2\u5220\u9664');
            setTimeout(() => location.reload(), 500);
        }
    </script>
"""
CHANNELS_CONTENT = """
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-broadcast"></i> 推送通道</h2>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addChannelModal" onclick="resetChannelModal()">
                <i class="bi bi-plus-lg"></i> 添加通道
            </button>
        </div>

        <div class="alert alert-info">
            <i class="bi bi-info-circle"></i> 配置推送通道，端口可关联多个通道同时推送。支持企业微信应用/机器人、钉钉、飞书。
        </div>

        <div class="card">
            <div class="card-body p-0">
                <table class="table table-hover mb-0">
                    <thead>
                        <tr>
                            <th>名称</th>
                            <th>类型</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="channelsTable">
                        {% for ch in channels %}
                        <tr data-channel-id="{{ ch.id }}">
                            <td>{{ ch.name }}</td>
                            <td>
                                {% if ch.type == 'wechat_work_api' %}
                                    <span class="badge bg-primary">企业微信应用</span>
                                {% elif ch.type == 'wechat_work_bot' %}
                                    <span class="badge bg-success">企业微信机器人</span>
                                {% elif ch.type == 'dingtalk' %}
                                    <span class="badge bg-info">钉钉</span>
                                {% elif ch.type == 'feishu' %}
                                    <span class="badge bg-warning text-dark">飞书</span>
                                {% elif ch.type == 'telegram_bot' %}
                                    <span class="badge bg-secondary">Telegram</span>
                                {% elif ch.type == 'bark' %}
                                    <span class="badge bg-dark">Bark</span>
                                {% else %}
                                    <span class="badge bg-secondary">{{ ch.type }}</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if ch.enabled %}
                                    <span class="badge bg-success">启用</span>
                                {% else %}
                                    <span class="badge bg-secondary">禁用</span>
                                {% endif %}
                            </td>
                            <td>
                                <button class="btn btn-icon btn-outline-primary btn-sm" onclick="testChannel({{ ch.id }})" title="测试"><i class="bi bi-send"></i></button>
                                <button class="btn btn-icon btn-outline-primary btn-sm" onclick="openEditChannel({{ ch.id }})" title="编辑"><i class="bi bi-pencil"></i></button>
                                <button class="btn btn-icon btn-outline-success btn-sm" onclick="duplicateChannel({{ ch.id }})" title="复制"><i class="bi bi-files"></i></button>
                                <button class="btn btn-icon btn-outline-danger btn-sm" onclick="deleteChannel({{ ch.id }})" title="删除"><i class="bi bi-trash"></i></button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 添加/编辑通道弹窗 -->
        <div class="modal fade" id="addChannelModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="addChannelModalTitle">添加通道</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="addChannelForm" onsubmit="return false">
                            <input type="hidden" id="editChannelId">
                            <div class="mb-3">
                                <label class="form-label">通道名称</label>
                                <input type="text" class="form-control" id="editChannelName" placeholder="例如：我的通知通道" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">通道类型</label>
                                <select class="form-select" id="editChannelType" onchange="onChannelTypeChange()">
                                    <option value="wechat_work_api">企业微信应用</option>
                                    <option value="wechat_work_bot">企业微信机器人</option>
                                    <option value="dingtalk">钉钉</option>
                                    <option value="feishu">飞书</option>
                                    <option value="telegram_bot">Telegram</option>
                                    <option value="bark">Bark (iOS)</option>
                                </select>
                            </div>
                            
                            <!-- 企业微信应用配置 -->
                            <div id="config_wechat_work_api" class="channel-config">
                                <div class="mb-3">
                                    <label class="form-label">Corp ID</label>
                                    <input type="text" class="form-control" id="cfg_corp_id" placeholder="企业 ID">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Corp Secret</label>
                                    <input type="password" class="form-control" id="cfg_corp_secret" placeholder="应用 Secret">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Agent ID</label>
                                    <input type="text" class="form-control" id="cfg_agent_id" placeholder="应用 Agent ID">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">接收人</label>
                                    <textarea class="form-control" id="cfg_user_id" rows="3" placeholder="每行一个用户 ID&#10;例如：&#10;@all&#10;zhangsan&#10;lisi"></textarea>
                                    <div class="form-text">"@all" 表示所有人，多个用户每行一个</div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">部门 ID</label>
                                    <input type="text" class="form-control" id="cfg_party_id" placeholder="部门 ID，多个用 | 分隔">
                                    <div class="form-text">可选，指定接收消息的部门</div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">标签 ID</label>
                                    <input type="text" class="form-control" id="cfg_tag_id" placeholder="标签 ID，多个用 | 分隔">
                                    <div class="form-text">可选，指定接收消息的标签</div>
                                </div>
                            </div>
                            
                            <!-- 企业微信机器人配置 -->
                            <div id="config_wechat_work_bot" class="channel-config" style="display:none">
                                <div class="mb-3">
                                    <label class="form-label">Webhook URL</label>
                                    <input type="text" class="form-control" id="cfg_wwb_webhook_url" placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...">
                                </div>
                            </div>
                            
                            <!-- 钉钉配置 -->
                            <div id="config_dingtalk" class="channel-config" style="display:none">
                                <div class="mb-3">
                                    <label class="form-label">Webhook URL</label>
                                    <input type="text" class="form-control" id="cfg_dingtalk_webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=...">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">加签密钥（可选）</label>
                                    <input type="password" class="form-control" id="cfg_dingtalk_secret" placeholder="SEC...">
                                </div>
                            </div>
                            
                            <!-- 飞书配置 -->
                            <div id="config_feishu" class="channel-config" style="display:none">
                                <div class="mb-3">
                                    <label class="form-label">Webhook URL</label>
                                    <input type="text" class="form-control" id="cfg_feishu_webhook_url" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/...">
                                </div>
                            </div>
                            
                            <!-- Telegram Bot 配置 -->
                            <div id="config_telegram_bot" class="channel-config" style="display:none">
                                <div class="mb-3">
                                    <label class="form-label">Bot Token</label>
                                    <input type="password" class="form-control" id="cfg_bot_token" placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Chat ID</label>
                                    <input type="text" class="form-control" id="cfg_chat_id" placeholder="用户 ID 或群组 ID（如 @channelname）">
                                </div>
                            </div>
                            
                            <!-- Bark 配置 -->
                            <div id="config_bark" class="channel-config" style="display:none">
                                <div class="mb-3">
                                    <label class="form-label">服务器地址（可选）</label>
                                    <input type="text" class="form-control" id="cfg_server_url" placeholder="https://api.day.app" value="https://api.day.app">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Device Key</label>
                                    <input type="text" class="form-control" id="cfg_device_key" placeholder="你的设备密钥">
                                </div>
                            </div>
                            
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="editChannelEnabled" checked>
                                <label class="form-check-label" for="editChannelEnabled">启用</label>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                        <button type="button" class="btn btn-primary" onclick="saveChannel()">保存</button>
                    </div>
                </div>
            </div>
        </div>
"""

CHANNELS_JS = """
    <script>
        const channelsData = {{ channels_json|safe }};
        
        function onChannelTypeChange() {
            const type = document.getElementById('editChannelType').value;
            document.querySelectorAll('.channel-config').forEach(el => el.style.display = 'none');
            const configDiv = document.getElementById('config_' + type);
            if (configDiv) configDiv.style.display = 'block';
        }
        
        function resetChannelModal() {
            document.getElementById('addChannelModalTitle').textContent = '添加通道';
            document.getElementById('editChannelId').value = '';
            document.getElementById('editChannelName').value = '';
            document.getElementById('editChannelType').value = 'wechat_work_api';
            document.getElementById('editChannelEnabled').checked = true;
            // 清空所有配置字段
            document.querySelectorAll('.channel-config input').forEach(el => el.value = '');
            document.getElementById('cfg_user_id').value = '@all';
            onChannelTypeChange();
        }
        
        function openEditChannel(id) {
            const ch = channelsData.find(c => c.id === id);
            if (!ch) return;
            
            document.getElementById('addChannelModalTitle').textContent = '编辑通道';
            document.getElementById('editChannelId').value = ch.id;
            document.getElementById('editChannelName').value = ch.name;
            document.getElementById('editChannelType').value = ch.type;
            document.getElementById('editChannelEnabled').checked = ch.enabled == 1;
            
            // 先切换显示对应的配置表单
            onChannelTypeChange();
            
            const config = typeof ch.config === 'string' ? JSON.parse(ch.config) : ch.config;
            
            // 填充配置字段
            if (config.corp_id) document.getElementById('cfg_corp_id').value = config.corp_id;
            if (config.corp_secret) document.getElementById('cfg_corp_secret').value = config.corp_secret;
            if (config.agent_id) document.getElementById('cfg_agent_id').value = config.agent_id;
            if (config.user_id) {
                // 把 | 分隔的字符串换成多行
                document.getElementById('cfg_user_id').value = config.user_id.replace(/\|/g, '\\n');
            }
            if (config.party_id) document.getElementById('cfg_party_id').value = config.party_id;
            if (config.tag_id) document.getElementById('cfg_tag_id').value = config.tag_id;
            if (config.webhook_url) {
                if (ch.type === 'wechat_work_bot') document.getElementById('cfg_wwb_webhook_url').value = config.webhook_url;
                else if (ch.type === 'dingtalk') document.getElementById('cfg_dingtalk_webhook_url').value = config.webhook_url;
                else if (ch.type === 'feishu') document.getElementById('cfg_feishu_webhook_url').value = config.webhook_url;
            }
            if (config.secret) document.getElementById('cfg_dingtalk_secret').value = config.secret;
            if (config.bot_token) document.getElementById('cfg_bot_token').value = config.bot_token;
            if (config.chat_id) document.getElementById('cfg_chat_id').value = config.chat_id;
            if (config.server_url) document.getElementById('cfg_server_url').value = config.server_url;
            if (config.device_key) document.getElementById('cfg_device_key').value = config.device_key;
            
            onChannelTypeChange();
            new bootstrap.Modal(document.getElementById('addChannelModal')).show();
        }
        
        function saveChannel() {
            const id = document.getElementById('editChannelId').value;
            const type = document.getElementById('editChannelType').value;
            
            const config = {};
            if (type === 'wechat_work_api') {
                config.corp_id = document.getElementById('cfg_corp_id').value;
                config.corp_secret = document.getElementById('cfg_corp_secret').value;
                config.agent_id = document.getElementById('cfg_agent_id').value;
                // 把多行文本用 | 连接
                const userIdText = document.getElementById('cfg_user_id').value.trim();
                config.user_id = userIdText ? userIdText.split('\\n').map(s => s.trim()).filter(s => s).join('|') : '';
                config.party_id = document.getElementById('cfg_party_id').value.trim();
                config.tag_id = document.getElementById('cfg_tag_id').value.trim();
                // 验证：接收人/部门ID/标签ID 至少填一个
                if (!config.user_id && !config.party_id && !config.tag_id) {
                    showToast('接收人、部门 ID、标签 ID 至少填写一项', 'danger');
                    return;
                }
            } else if (type === 'wechat_work_bot') {
                config.webhook_url = document.getElementById('cfg_wwb_webhook_url').value;
            } else if (type === 'dingtalk') {
                config.webhook_url = document.getElementById('cfg_dingtalk_webhook_url').value;
                config.secret = document.getElementById('cfg_dingtalk_secret').value;
            } else if (type === 'feishu') {
                config.webhook_url = document.getElementById('cfg_feishu_webhook_url').value;
            } else if (type === 'telegram_bot') {
                config.bot_token = document.getElementById('cfg_bot_token').value;
                config.chat_id = document.getElementById('cfg_chat_id').value;
            } else if (type === 'bark') {
                config.server_url = document.getElementById('cfg_server_url').value;
                config.device_key = document.getElementById('cfg_device_key').value;
            }
            
            const data = {
                name: document.getElementById('editChannelName').value,
                type: type,
                config: config,
                enabled: document.getElementById('editChannelEnabled').checked ? 1 : 0
            };
            
            const url = id ? `/api/channels/${id}` : '/api/channels';
            const method = id ? 'PUT' : 'POST';
            
            fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(r => r.json())
            .then(() => {
                showToast('保存成功');
                location.reload();
            })
            .catch(err => showToast('保存失败：' + err, 'danger'));
        }
        
        function deleteChannel(id) {
            if (!confirm('确定删除此通道？')) return;
            fetch(`/api/channels/${id}`, {method: 'DELETE'})
            .then(r => r.json())
            .then(() => {
                showToast('已删除');
                location.reload();
            })
            .catch(err => showToast('删除失败：' + err, 'danger'));
        }

        function duplicateChannel(id) {
            if (!confirm('确定复制此通道？')) return;
            fetch(`/api/channels/${id}/duplicate`, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.error) {
                    showToast('复制失败：' + data.error, 'danger');
                } else {
                    showToast('已复制（默认禁用）');
                    location.reload();
                }
            })
            .catch(err => showToast('复制失败：' + err, 'danger'));
        }
        
        function testChannel(id) {
            showToast('正在测试...', 'info');
            fetch(`/api/channels/${id}/test`, {method: 'POST'})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showToast('测试成功！', 'success');
                } else {
                    showToast('测试失败：' + (data.error || data.message), 'danger');
                }
            })
            .catch(err => showToast('测试失败：' + err, 'danger'));
        }
        
        document.addEventListener('DOMContentLoaded', onChannelTypeChange);
    </script>
"""


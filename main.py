#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Emby Notifier v5.0.0
主入口：初始化数据库、启动多端口服务、启动 WebUI、启动 DND 队列检查。
"""

import threading
import time
import signal
import sys
import os
import logging

import log
import db
import media
import port_manager
from web_ui import run_web_ui
from version import __version__ as VERSION

AUTHOR = "codename-test"
UPDATETIME = "2026-07-08"
DESCRIPTION = (
    "Emby Notifier WebUI - 基于 Emby Notifier 的二次开发版本，新增 WebUI 管理界面。"
    "Multi-port, WebUI, DND support."
)
REPOSITORY = "https://github.com/codename-test/Emby_Notifier_WebUI"

WELCOME = f"""
███████╗███╗   ███╗██████╗ ██╗   ██╗    ███╗   ██╗ ██████╗ ████████╗██╗███████╗██╗███████╗██████╗
██╔════╝████╗ ████║██╔══██╗╚██╗ ██╔╝    ████╗  ██║██╔═══██╗╚══██╔══╝██║██╔════╝██║██╔════╝██╔══██╗
█████╗  ██╔████╔██║██████╔╝ ╚████╔╝     ██╔██╗ ██║██║   ██║   ██║   ██║█████╗  ██║█████╗  ██████╔╝
██╔══╝  ██║╚██╔╝██║██╔══██╗  ╚██╔╝      ██║╚██╗██║██║   ██║   ██║   ██║██╔══╝  ██║██╔══╝  ██╔══██╗
███████╗██║ ╚═╝ ██║██████╔╝   ██║       ██║ ╚████║╚██████╔╝   ██║   ██║██║     ██║███████╗██║  ██║
╚══════╝╚═╝     ╚═╝╚═════╝    ╚═╝       ╚═╝  ╚═══╝ ╚═════╝    ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝
"""


def welcome():
    print("\033[1;32m")
    print(WELCOME)
    print(f"  Version: {VERSION}")
    print(f"  Update:  {UPDATETIME}")
    print(f"  Author:  {AUTHOR}")
    print(f"  Repo:    {REPOSITORY}")
    print("\033[0m")


def dnd_queue_checker(pm):
    """
    后台线程：定期检查勿扰状态。
    当勿扰结束时，自动刷新所有端口的待推送队列。
    """
    was_in_dnd = False
    while True:
        try:
            dnd = db.get_dnd_settings()
            if dnd["enabled"]:
                in_dnd = media._is_in_dnd(dnd["start_time"], dnd["end_time"])
                if was_in_dnd and not in_dnd:
                    # DND 结束，刷新所有队列
                    log.logger.info("DND period ended. Flushing all pending queues...")
                    for p in db.get_all_ports():
                        if p["enabled"]:
                            try:
                                count = media.flush_queue_for_port(p["id"])
                                if count > 0:
                                    log.logger.info(
                                        f"[Port {p['port']}] Flushed {count} queued messages."
                                    )
                            except Exception as e:
                                log.logger.error(
                                    f"[Port {p['port']}] Failed to flush queue: {e}"
                                )
                was_in_dnd = in_dnd
            else:
                if was_in_dnd:
                    # DND was just disabled
                    log.logger.info("DND disabled. Flushing all pending queues...")
                    for p in db.get_all_ports():
                        if p["enabled"]:
                            try:
                                count = media.flush_queue_for_port(p["id"])
                                if count > 0:
                                    log.logger.info(
                                        f"[Port {p['port']}] Flushed {count} queued messages."
                                    )
                            except Exception as e:
                                log.logger.error(
                                    f"[Port {p['port']}] Failed to flush queue: {e}"
                                )
                was_in_dnd = False
        except Exception as e:
            log.logger.error(f"DND checker error: {e}")

        time.sleep(30)  # Check every 30 seconds


def main():
    welcome()

    # 1. 初始化数据库
    log.logger.info("Initializing database...")
    db.init_db()

    # 1.5 从数据库读取日志等级并应用
    log_level = db.get_log_level()
    if log_level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        log.logger.setLevel(getattr(logging, log_level))
        for h in log.logger.handlers:
            h.setLevel(getattr(logging, log_level))
    log.setup_db_logging()
    log.logger.info(f"Log level set to: {log_level}")

    # 2. 启动端口管理器
    pm = port_manager.PortManager()
    pm.start_all()
    ports = db.get_all_ports()
    active_count = sum(1 for p in ports if p["enabled"])
    log.logger.info(f"Port manager started. {active_count} active port(s).")

    # 3. 启动 DND 队列检查线程
    dnd_thread = threading.Thread(
        target=dnd_queue_checker, args=(pm,), daemon=True, name="dnd-checker"
    )
    dnd_thread.start()
    log.logger.info("DND queue checker started.")

    # 3.5 启动时检查队列，如果有 pending 消息且不在 DND 时间段，立即刷新
    try:
        dnd = db.get_dnd_settings()
        in_dnd = dnd["enabled"] and media._is_in_dnd(dnd["start_time"], dnd["end_time"])
        if not in_dnd:
            pending = db.get_pending_messages()
            if pending:
                log.logger.info(f"Startup: {len(pending)} pending messages found. Flushing...")
                for p in ports:
                    if p["enabled"]:
                        try:
                            count = media.flush_queue_for_port(p["id"])
                            if count > 0:
                                log.logger.info(
                                    f"[Port {p['port']}] Flushed {count} queued messages."
                                )
                        except Exception as e:
                            log.logger.error(
                                f"[Port {p['port']}] Failed to flush queue: {e}"
                            )
    except Exception as e:
        log.logger.error(f"Startup queue flush error: {e}")

    # 4. 启动 WebUI
    web_port = int(os.getenv("WEB_PORT", "5000"))
    web_thread = threading.Thread(
        target=run_web_ui, args=(web_port, pm), daemon=True, name="web-ui"
    )
    web_thread.start()
    log.logger.info(f"Web UI started at http://0.0.0.0:{web_port}")

    # 5. 主线程保持运行
    print(f"\n\033[1;36m  ➜ WebUI:  http://localhost:{web_port}\033[0m")
    for p in ports:
        if p["enabled"]:
            print(
                f"\033[1;36m  ➜ Webhook: http://localhost:{p['port']}  ({p['server_name']})\033[0m"
            )
    print()

    def signal_handler(sig, frame):
        log.logger.info("Shutting down...")
        pm.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.logger.info("Shutting down...")
        pm.stop_all()


if __name__ == "__main__":
    main()

#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
端口管理器
每个端口在独立线程中运行 aiohttp 服务器，
拥有独立的事件循环和消息队列。
"""

import asyncio
import threading
import time
import json
import socket
import log
import media
import my_utils
import db
from aiohttp import web


class PortServer:
    """单个端口的 HTTP 服务器"""

    def __init__(self, port_id, port_number):
        self.port_id = port_id
        self.port_number = port_number
        self.loop = None
        self.thread = None
        self._queue = None
        self._server = None
        self._runner = None
        self._worker_task = None
        self._running = False
        self._stop_event = None  # asyncio.Event set when stopping

    def start(self):
        """在独立线程中启动 aiohttp 服务器"""
        self._running = True
        self.thread = threading.Thread(
            target=self._run, daemon=True, name=f"port-{self.port_number}"
        )
        self.thread.start()
        # 等待事件循环和队列初始化
        for _ in range(50):
            if self.loop is not None and self._queue is not None:
                break
            time.sleep(0.1)
        log.logger.info(
            f"Port server started: port={self.port_number}, id={self.port_id}"
        )

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._serve())
        except Exception as e:
            log.logger.error(f"[Port {self.port_number}] Server error: {e}")
        finally:
            try:
                # 清理所有待处理的任务
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            except Exception:
                pass
            self.loop.close()

    async def _serve(self):
        self._queue = asyncio.Queue()
        self._stop_event = asyncio.Event()

        app = web.Application()
        app["port_id"] = self.port_id
        app["msg_queue"] = self._queue
        app.router.add_post("/", self._handle_post)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._server = web.TCPSite(self._runner, "0.0.0.0", self.port_number)
        await self._server.start()
        log.logger.info(
            f"HTTP server listening on 0.0.0.0:{self.port_number} (port_id={self.port_id})"
        )

        # Worker 协程：消费消息队列
        self._worker_task = asyncio.create_task(self._worker())
        try:
            # 等待停止信号，而非轮询
            await self._stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            # 取消 worker
            if self._worker_task and not self._worker_task.done():
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except (asyncio.CancelledError, Exception):
                    pass
            # 清理 runner
            if self._runner:
                await self._runner.cleanup()

    async def _handle_post(self, request):
        data = await request.text()
        if request.content_type != "application/json":
            log.logger.error(
                f"[Port {self.port_number}] Unsupported content type: "
                f"{request.content_type}"
            )
        else:
            log.logger.debug(f"[Port {self.port_number}] Received: {data}")
            await self._queue.put(data)
        return web.Response(text="OK")

    async def _worker(self):
        while True:
            try:
                msg = await self._queue.get()
                try:
                    if my_utils.contains_unicode_escape(msg):
                        # 处理 Unicode 转义序列，使用 surrogateescape 避免编码错误
                        msg = msg.encode("utf-8", errors="surrogateescape").decode("unicode_escape", errors="surrogateescape")
                    media.process_media(msg, self.port_id)
                except Exception as e:
                    log.logger.error(
                        f"[Port {self.port_number}] Worker error: {e}"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.logger.error(
                    f"[Port {self.port_number}] Unexpected worker error: {e}"
                )

    def submit_media(self, emby_data_json):
        """从外部线程提交媒体数据到此端口的队列（用于队列刷新等）"""
        if self.loop and self._queue and self._running:
            asyncio.run_coroutine_threadsafe(
                self._queue.put(emby_data_json), self.loop
            )

    def stop(self):
        """停止服务器"""
        self._running = False
        if self._stop_event and self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._stop_event.set)
        if self.thread:
            self.thread.join(timeout=5)
        log.logger.info(f"Port server stopped: port={self.port_number}")


def check_port_available(port_number: int) -> tuple[bool, str]:
    """检查端口是否可用"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        result = s.connect_ex(("127.0.0.1", port_number))
        if result == 0:
            return False, f"端口 {port_number} 已被占用"
        return True, ""
    except Exception as e:
        return False, str(e)
    finally:
        s.close()


class PortManager:
    """管理所有端口服务器的生命周期"""

    def __init__(self):
        self.servers = {}  # port_id -> PortServer

    def start_all(self):
        """启动数据库中所有已启用的端口"""
        ports = db.get_all_ports()
        for p in ports:
            if p["enabled"]:
                self.start_port(p["id"])

    def start_port(self, port_id):
        """启动指定端口"""
        port_config = db.get_port(port_id)
        if not port_config:
            log.logger.error(f"Port config not found: id={port_id}")
            return False

        if port_id in self.servers:
            log.logger.warning(f"Port {port_config['port']} already running")
            return False

        # 检查端口是否被占用
        ok, err = check_port_available(port_config["port"])
        if not ok:
            log.logger.error(f"Port {port_config['port']}: {err}")
            return False

        server = PortServer(port_id, port_config["port"])
        server.start()
        self.servers[port_id] = server
        return True

    def stop_port(self, port_id):
        """停止指定端口"""
        if port_id in self.servers:
            self.servers[port_id].stop()
            del self.servers[port_id]
            return True
        return False

    def restart_port(self, port_id):
        """重启指定端口"""
        self.stop_port(port_id)
        time.sleep(0.5)
        return self.start_port(port_id)

    def stop_all(self):
        """停止所有端口"""
        for port_id in list(self.servers.keys()):
            self.stop_port(port_id)

    def get_status(self):
        """获取所有端口状态"""
        result = []
        ports = db.get_all_ports()
        for p in ports:
            result.append(
                {
                    **p,
                    "running": p["id"] in self.servers,
                }
            )
        return result

    def is_running(self, port_id):
        return port_id in self.servers

    def get_sender(self, port_id):
        """获取端口的 Sender 实例"""
        from sender import PortSender
        port_config = db.get_port(port_id)
        if not port_config:
            return None
        channel_ids = json.loads(port_config.get("channel_ids", "[]")) if port_config else []
        if not channel_ids:
            return None
        return PortSender(
            port_id, port_config.get("server_name", ""), channel_ids
        )

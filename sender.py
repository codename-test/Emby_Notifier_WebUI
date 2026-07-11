#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Sender 模块 - 多通道推送管理。
每个端口可关联多个通道（企业微信应用/机器人、钉钉、飞书等）。
"""

import json
import log
import db
from channels import create_channel


class PortSender:
    """管理单个端口的所有推送通道"""

    def __init__(self, port_id, server_name, channel_ids):
        """
        Args:
            port_id: 端口配置 ID
            server_name: 服务器名称
            channel_ids: list of channel IDs
        """
        self.port_id = port_id
        self.server_name = server_name
        self.channels = []

        for cid in channel_ids:
            ch = db.get_channel(cid)
            if ch and ch["enabled"]:
                try:
                    config = json.loads(ch["config"]) if isinstance(ch["config"], str) else ch["config"]
                    channel = create_channel(ch["type"], config)
                    self.channels.append(channel)
                    log.logger.debug(f"[Port {port_id}] Channel loaded: {ch['name']} ({ch['type']})")
                except Exception as e:
                    log.logger.error(f"[Port {port_id}] Failed to init channel {cid}: {e}")

    def has_any_channel(self):
        return len(self.channels) > 0

    def send_test_msg(self, test_content="Emby Notifier 测试消息"):
        """发送测试消息到所有通道"""
        results = {}
        for channel in self.channels:
            try:
                # 构造简单测试媒体数据
                test_media = {
                    "media_type": "Movie",
                    "media_name": "测试电影",
                    "media_rel": "2024-01-01",
                    "media_episode": "",
                    "media_date": "2024-01-01",
                    "media_rating": 8.5,
                    "media_intro": "这是一条测试消息",
                    "media_tmdburl": "",
                    "media_backdrop": "",
                    "media_poster": "",
                    "media_still": "",
                }
                test_template = {
                    "title": "测试通知",
                    "description": test_content,
                    "picurl_movie": "",
                    "picurl_episode": "",
                    "enable_image": 0,
                }
                ok = channel.send(test_media, test_template)
                results[channel.CHANNEL_NAME] = "success" if ok else "failed"
            except Exception as e:
                results[channel.CHANNEL_NAME] = str(e)
                log.logger.error(f"[Port {self.port_id}] {channel.CHANNEL_NAME} test failed: {e}")
        return results

    def send_media_details(self, media: dict):
        """推送媒体详情到所有通道
        
        Returns:
            bool: True if ALL channels sent successfully, False otherwise
        """
        # 选择模板（标准/回退）
        template = self._select_template(media)

        results = []
        all_ok = True
        for channel in self.channels:
            try:
                ok = channel.send(media, template)
                results.append({"channel": channel.CHANNEL_NAME, "ok": ok})
                if ok:
                    log.logger.debug(f"[Port {self.port_id}] {channel.CHANNEL_NAME}: sent successfully")
                else:
                    all_ok = False
                    log.logger.error(f"[Port {self.port_id}] {channel.CHANNEL_NAME}: send failed")
            except Exception as e:
                results.append({"channel": channel.CHANNEL_NAME, "ok": False, "error": str(e)})
                all_ok = False
                log.logger.error(f"[Port {self.port_id}] {channel.CHANNEL_NAME} error: {e}")

        return all_ok

    def _select_template(self, media: dict) -> dict:
        """根据媒体数据选择模板"""
        # TMDB 失败时使用回退模板（主动跳过 TMDB 的不算失败）
        if media.get("tmdb_failed") and not media.get("skip_tmdb"):
            fallback = db.get_fallback_template()
            if fallback:
                log.logger.warning(f"[Port {self.port_id}] Using fallback template: {fallback.get('name', 'fallback')}")
                return fallback

        # 获取端口配置的模板
        port = db.get_port(self.port_id)
        template_id = port.get("template_id", 1) if port else 1
        template = db.get_template(template_id)
        if not template:
            template = db.get_template(1)  # 默认标准模板
        return template

    def has_channels(self) -> bool:
        """检查是否有可用通道"""
        return len(self.channels) > 0

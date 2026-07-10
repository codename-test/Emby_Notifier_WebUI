#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Bark Channel (iOS 推送).
"""

import requests
import log
from . import BaseChannel


class Bark(BaseChannel):
    """Bark iOS 推送通道。"""
    
    CHANNEL_TYPE = "bark"
    CHANNEL_NAME = "Bark"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.server_url = config.get("server_url", "https://api.day.app")
        self.device_key = config.get("device_key", "")
    
    def send(self, media: dict, template: dict) -> bool:
        """发送推送通知。"""
        if not self.device_key:
            log.logger.error("Bark: No device key configured")
            return False
        
        content = self.render_content(media, template)
        
        # Bark 推送格式
        title = content["title"]
        body = self._build_body(content)
        
        url = f"{self.server_url}/{self.device_key}"
        payload = {
            "title": title,
            "body": body,
            "icon": content.get("picurl", ""),
            "url": content.get("tmdb_url", ""),
            "group": "EmbyNotifier",
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("code") == 200:
                log.logger.debug(f"Bark: Message sent successfully")
                return True
            else:
                log.logger.error(f"Bark send error: {data.get('message')}")
                return False
        except Exception as e:
            log.logger.error(f"Bark send failed: {e}")
            return False
    
    def _build_body(self, content: dict) -> str:
        """构建推送正文。"""
        lines = []
        lines.append(f"{content['name']} ({content['year']})")
        if content.get('episode'):
            lines.append(f"{content['episode']}")
        lines.append("")
        if content.get('date'):
            lines.append(f"上映日期：{content['date']}")
        if content.get('rating'):
            lines.append(f"评分：{content['rating']}")
        lines.append("")
        if content.get('intro'):
            intro = content['intro'][:200] + "..." if len(content['intro']) > 200 else content['intro']
            lines.append(intro)
        return "\n".join(lines)
    
    def test(self) -> bool:
        """测试通道连通性。"""
        if not self.device_key:
            log.logger.error("Bark test failed: No device key configured")
            return False
        
        url = f"{self.server_url}/{self.device_key}"
        payload = {
            "title": "Emby Notifier 测试",
            "body": "通道测试成功！",
            "group": "EmbyNotifier",
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("code") == 200:
                log.logger.debug("Bark test successful")
                return True
            else:
                log.logger.error(f"Bark test failed: {data.get('message')}")
                return False
        except Exception as e:
            log.logger.error(f"Bark test failed: {e}")
            return False

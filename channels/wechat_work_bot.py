#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
WeChat Work (企业微信) Bot Webhook Channel.
"""

import requests
import log
from . import BaseChannel


class WechatWorkBot(BaseChannel):
    """企业微信机器人推送通道。"""
    
    CHANNEL_TYPE = "wechat_work_bot"
    CHANNEL_NAME = "企业微信机器人"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
    
    def send(self, media: dict, template: dict) -> bool:
        """发送图文消息。"""
        if not self.webhook_url:
            log.logger.error("WeChat Work Bot: No webhook URL configured")
            return False
        
        content = self.render_content(media, template)
        
        # 企业微信机器人图文消息
        articles = [{
            "title": content["title"],
            "description": content["description"],
            "url": content.get("tmdb_url", ""),
            "picurl": content.get("picurl", ""),
        }]
        
        payload = {
            "msgtype": "news",
            "news": {
                "articles": articles,
            }
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=15)
            data = resp.json()
            if data.get("errcode") == 0:
                log.logger.debug(f"WeChat Work Bot: Message sent successfully")
                return True
            else:
                log.logger.error(f"WeChat Work Bot send error: {data.get('errmsg')}")
                return False
        except Exception as e:
            log.logger.error(f"WeChat Work Bot send failed: {e}")
            return False
    
    def test(self) -> bool:
        """测试通道连通性。"""
        if not self.webhook_url:
            log.logger.error("WeChat Work Bot test failed: No webhook URL configured")
            return False
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": "Emby Notifier 通道测试成功！"
            }
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=15)
            data = resp.json()
            if data.get("errcode") == 0:
                log.logger.debug("WeChat Work Bot test successful")
                return True
            else:
                log.logger.error(f"WeChat Work Bot test failed: {data.get('errmsg')}")
                return False
        except Exception as e:
            log.logger.error(f"WeChat Work Bot test failed: {e}")
            return False

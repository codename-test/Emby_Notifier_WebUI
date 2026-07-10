#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Telegram Bot Channel.
"""

import requests
import log
from . import BaseChannel


class TelegramBot(BaseChannel):
    """Telegram Bot 推送通道。"""
    
    CHANNEL_TYPE = "telegram_bot"
    CHANNEL_NAME = "Telegram"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")
    
    def _get_api_url(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/"
    
    def send(self, media: dict, template: dict) -> bool:
        """发送图文消息（Telegram 用 HTML 格式）。"""
        if not self.bot_token or not self.chat_id:
            log.logger.error("Telegram Bot: No bot token or chat_id configured")
            return False
        
        content = self.render_content(media, template)
        
        # 构建 HTML 格式消息
        text = self._build_html(content)
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        
        # 如果有图片，用 sendPhoto
        if content.get("picurl"):
            payload["photo"] = content["picurl"]
            payload["caption"] = text
            url = self._get_api_url() + "sendPhoto"
        else:
            url = self._get_api_url() + "sendMessage"
        
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("ok"):
                log.logger.debug(f"Telegram Bot: Message sent successfully")
                return True
            else:
                log.logger.error(f"Telegram Bot send error: {data.get('description')}")
                return False
        except Exception as e:
            log.logger.error(f"Telegram Bot send failed: {e}")
            return False
    
    def _build_html(self, content: dict) -> str:
        """构建 Telegram HTML 格式文本。"""
        lines = []
        lines.append(f"<b>{content['title']}</b>")
        lines.append("")
        lines.append(f"<b>{content['name']}</b> ({content['year']})")
        if content.get('episode'):
            lines.append(f"{content['episode']}")
        lines.append("")
        if content.get('date'):
            lines.append(f"📅 上映日期：{content['date']}")
        if content.get('rating'):
            lines.append(f"⭐ 评分：{content['rating']}")
        lines.append("")
        if content.get('intro'):
            intro = content['intro'][:400] + "..." if len(content['intro']) > 400 else content['intro']
            lines.append(f"<i>{intro}</i>")
        if content.get('tmdb_url'):
            lines.append("")
            lines.append(f'<a href="{content["tmdb_url"]}">查看详情</a>')
        return "\n".join(lines)
    
    def test(self) -> bool:
        """测试通道连通性。"""
        if not self.bot_token or not self.chat_id:
            log.logger.error("Telegram Bot test failed: No bot token or chat_id configured")
            return False
        
        url = self._get_api_url() + "sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": "Emby Notifier 通道测试成功！",
            "parse_mode": "HTML",
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("ok"):
                log.logger.debug("Telegram Bot test successful")
                return True
            else:
                log.logger.error(f"Telegram Bot test failed: {data.get('description')}")
                return False
        except Exception as e:
            log.logger.error(f"Telegram Bot test failed: {e}")
            return False

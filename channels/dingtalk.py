#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
DingTalk (钉钉) Bot Webhook Channel.
"""

import requests
import log
from . import BaseChannel


class DingTalk(BaseChannel):
    """钉钉机器人推送通道。"""
    
    CHANNEL_TYPE = "dingtalk"
    CHANNEL_NAME = "钉钉"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
        self.secret = config.get("secret", "")  # 加签密钥（可选）
    
    def send(self, media: dict, template: dict) -> bool:
        """发送 markdown 消息。"""
        if not self.webhook_url:
            log.logger.error("DingTalk: No webhook URL configured")
            return False
        
        content = self.render_content(media, template)
        
        # 钉钉 markdown 格式
        title = content["title"]
        text = self._build_markdown(content)
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text,
            }
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=15)
            data = resp.json()
            if data.get("errcode") == 0:
                log.logger.debug(f"DingTalk: Message sent successfully")
                return True
            else:
                log.logger.error(f"DingTalk send error: {data.get('errmsg')}")
                return False
        except Exception as e:
            log.logger.error(f"DingTalk send failed: {e}")
            return False
    
    def _build_markdown(self, content: dict) -> str:
        """构建钉钉 markdown 文本。"""
        lines = []
        lines.append(f"## {content['title']}")
        lines.append("")
        lines.append(f"**{content['name']}** ({content['year']})")
        if content.get('episode'):
            lines.append(f"{content['episode']}")
        lines.append("")
        if content.get('date'):
            lines.append(f"📅 上映日期：{content['date']}")
        if content.get('rating'):
            lines.append(f"⭐ 评分：{content['rating']}")
        lines.append("")
        if content.get('intro'):
            # 钉钉 markdown 不支持太长，截断
            intro = content['intro'][:200] + "..." if len(content['intro']) > 200 else content['intro']
            lines.append(f"> {intro}")
        if content.get('tmdb_url'):
            lines.append("")
            lines.append(f"[查看详情]({content['tmdb_url']})")
        return "\n".join(lines)
    
    def test(self) -> bool:
        """测试通道连通性。"""
        if not self.webhook_url:
            log.logger.error("DingTalk test failed: No webhook URL configured")
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
                log.logger.debug("DingTalk test successful")
                return True
            else:
                log.logger.error(f"DingTalk test failed: {data.get('errmsg')}")
                return False
        except Exception as e:
            log.logger.error(f"DingTalk test failed: {e}")
            return False

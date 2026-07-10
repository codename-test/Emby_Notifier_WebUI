#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Feishu (飞书) Bot Webhook Channel.
"""

import requests
import log
from . import BaseChannel


class Feishu(BaseChannel):
    """飞书机器人推送通道。"""
    
    CHANNEL_TYPE = "feishu"
    CHANNEL_NAME = "飞书"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
    
    def send(self, media: dict, template: dict) -> bool:
        """发送交互式卡片消息。"""
        if not self.webhook_url:
            log.logger.error("Feishu: No webhook URL configured")
            return False
        
        content = self.render_content(media, template)
        
        # 飞书卡片格式
        card = {
            "config": {
                "wide_screen_mode": True,
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": content["title"],
                },
                "template": "blue",
            },
            "elements": [],
        }
        
        # 添加内容元素
        elements = []
        
        # 标题行
        title_text = f"**{content['name']}**"
        if content.get('year'):
            title_text += f" ({content['year']})"
        if content.get('episode'):
            title_text += f"\n{content['episode']}"
        elements.append({
            "tag": "markdown",
            "content": title_text,
        })
        
        # 元信息
        meta_parts = []
        if content.get('date'):
            meta_parts.append(f"📅 上映日期：{content['date']}")
        if content.get('rating'):
            meta_parts.append(f"⭐ 评分：{content['rating']}")
        if meta_parts:
            elements.append({
                "tag": "markdown",
                "content": "\n".join(meta_parts),
            })
        
        # 简介
        if content.get('intro'):
            intro = content['intro'][:300] + "..." if len(content['intro']) > 300 else content['intro']
            elements.append({
                "tag": "markdown",
                "content": f"> {intro}",
            })
        
        # 封面图
        if content.get('picurl'):
            elements.append({
                "tag": "img",
                "img_key": "",  # 飞书需要上传获取 img_key，这里用 URL 方式
                "title": {
                    "tag": "plain_text",
                    "content": "封面",
                },
            })
            # 飞书机器人不支持直接 URL 图片，改用 action 链接
            if content.get('tmdb_url'):
                elements.append({
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "查看详情",
                        },
                        "url": content['tmdb_url'],
                        "type": "primary",
                    }],
                })
        
        card["elements"] = elements
        
        payload = {
            "msg_type": "interactive",
            "card": card,
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=15)
            data = resp.json()
            if data.get("code") == 0 or data.get("StatusCode") == 0:
                log.logger.debug(f"Feishu: Message sent successfully")
                return True
            else:
                log.logger.error(f"Feishu send error: {data.get('msg', data.get('StatusMessage', ''))}")
                return False
        except Exception as e:
            log.logger.error(f"Feishu send failed: {e}")
            return False
    
    def test(self) -> bool:
        """测试通道连通性。"""
        if not self.webhook_url:
            log.logger.error("Feishu test failed: No webhook URL configured")
            return False
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": "Emby Notifier 通道测试成功！"
            }
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=15)
            data = resp.json()
            if data.get("code") == 0 or data.get("StatusCode") == 0:
                log.logger.debug("Feishu test successful")
                return True
            else:
                log.logger.error(f"Feishu test failed: {data.get('msg', data.get('StatusMessage', ''))}")
                return False
        except Exception as e:
            log.logger.error(f"Feishu test failed: {e}")
            return False

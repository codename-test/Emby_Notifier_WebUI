#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
WeChat Work (企业微信) Application API Channel.
"""

import requests
import log
from . import BaseChannel


class WechatWorkAPI(BaseChannel):
    """企业微信应用推送通道。"""
    
    CHANNEL_TYPE = "wechat_work_api"
    CHANNEL_NAME = "企业微信应用"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.corp_id = config.get("corp_id", "")
        self.corp_secret = config.get("corp_secret", "")
        self.agent_id = config.get("agent_id", "")
        self.user_id = config.get("user_id", "")
        self._access_token = None
    
    def _get_access_token(self) -> str:
        """获取 access_token。"""
        if self._access_token:
            return self._access_token
        
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret,
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            if data.get("errcode") == 0:
                self._access_token = data.get("access_token", "")
                return self._access_token
            else:
                log.logger.error(f"WeChat Work API token error: {data.get('errmsg')}")
        except Exception as e:
            log.logger.error(f"WeChat Work API token request failed: {e}")
        return ""
    
    def send(self, media: dict, template: dict) -> bool:
        """发送图文消息。"""
        token = self._get_access_token()
        if not token:
            log.logger.error("WeChat Work API: No access token")
            return False
        
        content = self.render_content(media, template)
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        
        # 构建图文消息
        articles = [{
            "title": content["title"],
            "description": content["description"],
            "url": content.get("tmdb_url", ""),
            "picurl": content.get("picurl", ""),
        }]
        
        payload = {
            "touser": self.user_id,
            "msgtype": "news",
            "agentid": self.agent_id,
            "news": {
                "articles": articles,
            },
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("errcode") == 0:
                log.logger.debug(f"WeChat Work API: Message sent successfully")
                return True
            else:
                log.logger.error(f"WeChat Work API send error: {data.get('errmsg')}")
                return False
        except Exception as e:
            log.logger.error(f"WeChat Work API send failed: {e}")
            return False
    
    def test(self) -> bool:
        """测试通道连通性。"""
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"
        payload = {
            "touser": self.user_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": "Emby Notifier 通道测试成功！"
            },
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            return data.get("errcode") == 0
        except:
            return False

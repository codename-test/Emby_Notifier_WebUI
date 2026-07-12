#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Channel base class and factory function.
"""

import requests
import log


class BaseChannel:
    """Base class for all notification channels."""
    
    CHANNEL_TYPE = "base"
    CHANNEL_NAME = "Base Channel"
    
    def __init__(self, config: dict):
        self.config = config
    
    def render_content(self, media: dict, template: dict) -> dict:
        """Render template variables into content dict."""
        type_ch = "电影" if media.get("media_type") == "Movie" else "剧集"
        year = media.get("media_rel", "")[:4] if media.get("media_rel") else ""
        episode = media.get("media_episode", "")
        name = media.get("media_name", "")
        date = media.get("media_rel", "")
        rating = media.get("media_rating", 0)
        intro = media.get("media_intro", "")
        tmdb_url = media.get("media_tmdburl", "")
        
        # Get picurl from template
        picurl = ""
        if template.get("enable_image", 1):
            if media.get("media_type") == "Movie":
                picurl = template.get("picurl_movie", "")
            else:
                picurl = template.get("picurl_episode", "")
            # Replace TMDB image placeholder
            if picurl == "media_backdrop":
                picurl = media.get("media_backdrop", "")
            elif picurl == "media_poster":
                picurl = media.get("media_poster", "")
            elif picurl == "media_still":
                picurl = media.get("media_still", "")
        
        title = template.get("title", "{type}更新").format(
            type=type_ch, name=name, year=year, episode=episode
        )
        
        description = template.get("description", "").format(
            type=type_ch, name=name, year=year, episode=episode,
            date=date, rating=rating, intro=intro, tmdb_url=tmdb_url
        )
        
        return {
            "title": title,
            "description": description,
            "picurl": picurl,
            "tmdb_url": tmdb_url,
            "name": name,
            "year": year,
            "episode": episode,
            "date": date,
            "rating": rating,
            "intro": intro,
            "type": type_ch,
        }
    
    def send(self, media: dict, template: dict) -> bool:
        """Send notification. Override in subclass."""
        raise NotImplementedError
    
    def test(self) -> bool:
        """Test channel connectivity. Override in subclass."""
        raise NotImplementedError


def create_channel(channel_type: str, config: dict) -> BaseChannel:
    """Factory function to create channel instance."""
    from .wechat_work_api import WechatWorkAPI
    from .wechat_work_bot import WechatWorkBot
    from .dingtalk import DingTalk
    from .feishu import Feishu
    from .telegram_bot import TelegramBot
    from .bark import Bark
    
    registry = {
        "wechat_work_api": WechatWorkAPI,
        "wechat_work_bot": WechatWorkBot,
        "dingtalk": DingTalk,
        "feishu": Feishu,
        "telegram_bot": TelegramBot,
        "bark": Bark,
    }
    
    cls = registry.get(channel_type)
    if not cls:
        raise ValueError(f"Unknown channel type: {channel_type}")
    return cls(config)

#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Sender 模块 - 管理每个端口的推送渠道。
每个端口拥有独立的推送配置和 Token 缓存。
"""

import os
import json
import log
import wxapp
import tgbot
import bark


class PortSender:
    """管理单个端口的所有推送渠道"""

    def __init__(self, port_id, server_name, enabled_channels):
        """
        Args:
            port_id: 端口配置ID
            server_name: 服务器名称
            enabled_channels: list of dicts from db.get_enabled_channels()
                Each dict: {channel_type, config: {key: value}}
        """
        self.port_id = port_id
        self.server_name = server_name
        self.channels = {}
        self._wechat_token_cache = {}

        for ch in enabled_channels:
            ch_type = ch["channel_type"]
            ch_config = ch.get("config", {})
            self.channels[ch_type] = ch_config
            log.logger.info(f"[Port {port_id}] Channel enabled: {ch_type}")

    def has_channel(self, channel_type):
        return channel_type in self.channels

    def has_any_channel(self):
        return len(self.channels) > 0

    def send_test_msg(self, test_content="Emby Notifier 测试消息"):
        """发送测试消息到所有已启用的渠道"""
        results = {}
        if "wechat_work" in self.channels:
            try:
                self._send_wechat_text(test_content)
                results["wechat_work"] = "success"
            except Exception as e:
                results["wechat_work"] = str(e)
                log.logger.error(f"[Port {self.port_id}] WeChat test failed: {e}")

        if "telegram" in self.channels:
            try:
                cfg = self.channels["telegram"]
                escaped = test_content
                for ch in ["_", "*", "`", "["]:
                    escaped = escaped.replace(ch, f"\\{ch}")
                tgbot.send_message(
                    cfg["bot_token"], cfg["chat_id"], escaped
                )
                results["telegram"] = "success"
            except Exception as e:
                results["telegram"] = str(e)
                log.logger.error(f"[Port {self.port_id}] Telegram test failed: {e}")

        if "bark" in self.channels:
            try:
                cfg = self.channels["bark"]
                bark.send_message(
                    cfg.get("server", "https://api.day.app"),
                    cfg.get("device_keys", "").split(","),
                    {"title": "Emby Notifier", "body": test_content},
                )
                results["bark"] = "success"
            except Exception as e:
                results["bark"] = str(e)
                log.logger.error(f"[Port {self.port_id}] Bark test failed: {e}")

        return results

    def send_media_details(self, media: dict):
        """发送媒体详情到所有已启用的渠道"""
        for ch_type in self.channels:
            try:
                if ch_type == "wechat_work":
                    self._send_wechat_news(media)
                elif ch_type == "telegram":
                    self._send_telegram(media)
                elif ch_type == "bark":
                    self._send_bark(media)
            except Exception as e:
                log.logger.error(
                    f"[Port {self.port_id}] Failed to send via {ch_type}: {e}"
                )

    # ── WeChat Work ──────────────────────────

    def _get_wechat_token(self):
        cfg = self.channels["wechat_work"]
        return wxapp.get_access_token(
            cfg["corp_id"], cfg["corp_secret"], self._wechat_token_cache
        )

    def _send_wechat_text(self, content):
        cfg = self.channels["wechat_work"]
        access_token = self._get_wechat_token()
        wxapp.send_text(
            access_token,
            cfg.get("user_id", "@all"),
            int(cfg.get("agent_id", 0)),
            content,
        )

    def _send_wechat_news(self, media):
        cfg = self.channels["wechat_work"]
        access_token = self._get_wechat_token()

        msg_type = os.getenv("WECHAT_MSG_TYPE", "text")
        server_url = media.get("server_url", "")
        
        # 构建标题
        type_ch = "电影" if media["media_type"] == "Movie" else "剧集"
        title = f"[{type_ch}] {media['media_name']}"
        if media["media_type"] == "Episode":
            title += f" S{media['tv_season']}E{media['tv_episode']} {media.get('tv_episode_name', '')}"
        
        # 构建描述
        desc = (
            f"评分: {media['media_rating']}  上映: {media['media_rel']}\n\n"
            f"{media['media_intro'][:120]}..."
        )
        link = media.get("media_tmdburl", server_url)
        poster = media.get("media_poster", "")

        if msg_type == "news":
            wxapp.send_news(
                access_token,
                cfg.get("user_id", "@all"),
                int(cfg.get("agent_id", 0)),
                title,
                desc,
                link,
                poster,
            )
        else:
            content = (
                f"#影视更新 #{media['server_name']}\n"
                f"[{type_ch}]\n"
                f"片名: {media['media_name']} ({media['media_rel'][:4]})\n"
            )
            if media["media_type"] == "Episode":
                content += f"已更新至 第{media['tv_season']}季 第{media['tv_episode']}集\n"
            content += (
                f"评分: {media['media_rating']}\n"
                f"上映日期: {media['media_rel']}\n\n"
                f"内容简介: {media['media_intro']}\n\n"
                f"相关链接: {media['media_tmdburl']}"
            )
            wxapp.send_text(
                access_token,
                cfg.get("user_id", "@all"),
                int(cfg.get("agent_id", 0)),
                content,
            )

    # ── Telegram ─────────────────────────────

    def _send_telegram(self, media):
        cfg = self.channels["telegram"]
        caption = (
            "#影视更新 #{server_name}\n"
            + "\[{type_ch}]\n"
            + "片名： *{title}* ({year})\n"
            + "{episode}"
            + "评分： {rating}\n\n"
            + "上映日期： {rel}\n\n"
            + "内容简介： {intro}\n\n"
            + "相关链接： [TMDB]({tmdb_url})\n"
        )
        server_name = media["server_name"]
        for ch in ["_", "*", "`", "["]:
            server_name = server_name.replace(ch, f"\\{ch}")
        caption = caption.format(
            server_name=server_name,
            type_ch="电影" if media["media_type"] == "Movie" else "剧集",
            title=(
                media["media_name"]
                if media["media_type"] == "Movie"
                else f"{media['media_name']} {media['tv_episode_name']}"
            ),
            year=media["media_rel"][0:4] if media["media_rel"] else "Unknown",
            episode=(
                f"已更新至 第{media['tv_season']}季 第{media['tv_episode']}集\n"
                if media["media_type"] == "Episode"
                else ""
            ),
            rating=media["media_rating"],
            rel=media["media_rel"],
            intro=media["media_intro"],
            tmdb_url=media["media_tmdburl"],
        )
        poster = media["media_poster"]
        tgbot.send_photo(cfg["bot_token"], cfg["chat_id"], caption, poster)

    # ── Bark ─────────────────────────────────

    def _send_bark(self, media):
        cfg = self.channels["bark"]
        server = cfg.get("server", "https://api.day.app")
        device_keys = cfg.get("device_keys", "").split(",")

        type_ch = "电影" if media["media_type"] == "Movie" else "剧集"
        title = f"[{type_ch}] {media['media_name']}"
        body = (
            f"评分: {media['media_rating']}  上映: {media['media_rel']}\n"
            f"{media['media_intro'][:200]}"
        )
        content = {
            "title": title,
            "body": body,
            "url": media.get("media_tmdburl", ""),
            "group": media.get("server_name", "Emby"),
        }
        poster = media.get("media_poster", "")
        if poster:
            content["image"] = poster
        bark.send_message(server, device_keys, content)

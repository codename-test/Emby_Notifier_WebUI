#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
媒体处理模块
负责解析 Emby/Jellyfin Webhook 消息，获取 TMDB 详情，
并根据 DND 状态决定立即推送或暂存队列。
"""

import os
import abc
import json
import time
import datetime
import log
import my_utils
import tmdb_api
import tvdb_api
import db
from sender import PortSender


class IMedia(abc.ABC):
    """媒体信息抽象基类"""

    def __init__(self):
        self.info_ = {
            "Name": "",
            "Type": "Movie/Episode",
            "PremiereYear": 1970,
            "ProviderIds": {"Tmdb": "", "Imdb": "", "Tvdb": ""},
            "Series": 0,
            "Season": 0,
        }
        self.media_detail_ = {
            "server_type": "Emby",
            "server_url": "",
            "server_name": "",
            "media_name": "",
            "media_type": "Movie/Episode",
            "media_rating": 0.0,
            "media_rel": "",
            "media_intro": "",
            "media_tmdburl": "",
            "media_poster": "",
            "media_backdrop": "",
            "media_still": "",
            "tv_season": 0,
            "tv_episode": 0,
            "tv_episode_name": "",
        }
        self.port_id_ = None

    @abc.abstractmethod
    def parse_info(self, emby_media_info):
        pass

    @abc.abstractmethod
    def get_details(self):
        pass

    def _get_tmdb_id(self):
        """通过 TMDB 搜索 + TVDB 辅助匹配获取准确的 TMDB ID"""
        # If TMDB ID already known from ProviderIds, skip search
        existing_tmdb = self.info_["ProviderIds"].get("Tmdb", "")
        if existing_tmdb and existing_tmdb != "-1":
            log.logger.info(f"TMDB ID already known: {existing_tmdb}")
            return

        log.logger.info(f"Searching TMDB: {self.info_['Name']} ({self.info_['PremiereYear']})")
        medias, err = tmdb_api.search_media(
            self.info_["Type"], self.info_["Name"], self.info_["PremiereYear"]
        )
        if err:
            log.logger.error(err)
            raise Exception(err)

        Tvdb_id = self.info_["ProviderIds"].get("Tvdb", "-1")
        for m in medias:
            ext_ids, err = tmdb_api.get_external_ids(self.info_["Type"], m["id"])
            if err:
                log.logger.warning(err)
                continue
            if Tvdb_id == str(ext_ids.get("tvdb_id")):
                self.info_["ProviderIds"]["Tmdb"] = str(m["id"])
                log.logger.info(f"TMDB ID matched via TVDB: {m['id']}")
                return

        # Fallback: use first result
        if medias:
            log.logger.warning(
                f"No exact match for {self.info_['Name']}, using first result."
            )
            self.info_["ProviderIds"]["Tmdb"] = str(medias[0]["id"])
        else:
            # Name search failed, try direct lookup by TVDB ID
            Tvdb_id = self.info_["ProviderIds"].get("Tvdb", "")
            if Tvdb_id and Tvdb_id != "-1":
                log.logger.info(f"Name search failed, trying TVDB ID: {Tvdb_id}")
                tmdb_id, err = tmdb_api.find_by_tvdb_id(Tvdb_id)
                if tmdb_id:
                    self.info_["ProviderIds"]["Tmdb"] = str(tmdb_id)
                    return
                if err:
                    log.logger.warning(err)
            raise Exception(f"No media found on TMDB for {self.info_['Name']}")


class Movie(IMedia):
    """电影"""

    def __init__(self):
        super().__init__()
        self.info_["Type"] = "Movie"

    def __str__(self):
        return f"Movie: {self.info_['Name']} ({self.info_['PremiereYear']})"

    def parse_info(self, emby_media_info):
        self.info_["Name"] = emby_media_info.get("Name", "")
        date_str = emby_media_info.get("PremiereDate", "")
        if date_str:
            self.info_["PremiereYear"] = int(date_str[0:4])
        self.info_["ProviderIds"] = emby_media_info.get("ProviderIds", {})
        self.media_detail_["server_type"] = emby_media_info.get("ServerType", "Emby")
        self.media_detail_["server_url"] = emby_media_info.get("ServerURL", "")
        self.media_detail_["server_name"] = emby_media_info.get("ServerName", "")
        self.media_detail_["media_type"] = "Movie"

    def get_details(self):
        self._get_tmdb_id()
        tmdb_id = self.info_["ProviderIds"]["Tmdb"]
        details, err = tmdb_api.get_movie_details(tmdb_id)
        if err:
            raise Exception(err)
        self.media_detail_["media_name"] = details.get("title", self.info_["Name"])
        self.media_detail_["media_rating"] = details.get("vote_average", 0)
        self.media_detail_["media_rel"] = details.get("release_date", "Unknown")
        self.media_detail_["media_intro"] = details.get("overview", "暂无简介")
        self.media_detail_["media_tmdburl"] = (
            f"https://www.themoviedb.org/movie/{tmdb_id}?language=zh-CN"
        )
        poster_path = details.get("poster_path")
        if poster_path:
            self.media_detail_["media_poster"] = tmdb_api.get_poster_url(poster_path)
        backdrop_path = details.get("backdrop_path")
        if backdrop_path:
            self.media_detail_["media_backdrop"] = tmdb_api.get_poster_url(backdrop_path)


class Episode(IMedia):
    """剧集"""

    def __init__(self):
        super().__init__()
        self.info_["Type"] = "Episode"

    def __str__(self):
        return (
            f"Episode: {self.info_['Name']} "
            f"S{self.info_['Season']}E{self.info_['Episode']}"
        )

    def parse_info(self, emby_media_info):
        self.info_["Name"] = emby_media_info.get("SeriesName", "")
        self.info_["Season"] = emby_media_info.get("SeasonNumber", 0)
        self.info_["Episode"] = emby_media_info.get("IndexNumber", 0)
        date_str = emby_media_info.get("PremiereDate", "")
        if date_str:
            self.info_["PremiereYear"] = int(date_str[0:4])
        self.info_["ProviderIds"] = emby_media_info.get("ProviderIds", {})
        self.media_detail_["server_type"] = emby_media_info.get("ServerType", "Emby")
        self.media_detail_["server_url"] = emby_media_info.get("ServerURL", "")
        self.media_detail_["server_name"] = emby_media_info.get("ServerName", "")
        self.media_detail_["media_type"] = "Episode"
        self.media_detail_["tv_season"] = self.info_["Season"]
        self.media_detail_["tv_episode"] = self.info_["Episode"]
        self.media_detail_["tv_episode_name"] = emby_media_info.get("Name", "")

        # If SeriesName has no ProviderIds, try to get from Item
        if not self.info_["ProviderIds"].get("Tvdb"):
            series_provider = emby_media_info.get("SeriesProviderIds", {})
            if series_provider:
                self.info_["ProviderIds"].update(series_provider)

    def get_details(self):
        self._get_tmdb_id()
        tmdb_id = self.info_["ProviderIds"]["Tmdb"]

        # Get TV show details
        tv_details, err = tmdb_api.get_tv_details(tmdb_id)
        if err:
            raise Exception(err)

        # Get episode details
        ep_details, err = tmdb_api.get_tv_episode_details(
            tmdb_id, self.info_["Season"], self.info_["Episode"]
        )
        if err:
            log.logger.warning(f"Failed to get episode details: {err}, using show info")
            ep_details = {}

        self.media_detail_["media_name"] = tv_details.get("name", self.info_["Name"])
        self.media_detail_["media_rating"] = tv_details.get("vote_average", 0)
        self.media_detail_["media_intro"] = tv_details.get("overview", "暂无简介")
        self.media_detail_["media_tmdburl"] = (
            f"https://www.themoviedb.org/tv/{tmdb_id}?language=zh-CN"
        )

        # Air date: episode > season > current year
        air_date = ep_details.get("air_date", "")
        if not air_date:
            seasons = tv_details.get("seasons", [])
            for s in seasons:
                if s.get("season_number") == self.info_["Season"]:
                    air_date = s.get("air_date", "")
                    break
        if not air_date:
            air_date = str(datetime.datetime.now().year)
        self.media_detail_["media_rel"] = air_date

        # Poster
        poster_path = tv_details.get("poster_path")
        if poster_path:
            self.media_detail_["media_poster"] = tmdb_api.get_poster_url(poster_path)

        # Still image (episode screenshot), fallback to poster
        still_path = ep_details.get("still_path")
        if still_path:
            self.media_detail_["media_still"] = tmdb_api.get_still_url(still_path)
        elif poster_path:
            self.media_detail_["media_still"] = tmdb_api.get_poster_url(poster_path)

        # Backdrop
        backdrop_path = tv_details.get("backdrop_path")
        if backdrop_path:
            self.media_detail_["media_backdrop"] = tmdb_api.get_poster_url(
                backdrop_path
            )


# ──────────────────────────────────────────────
#  Message Preprocessing
# ──────────────────────────────────────────────


def jellyfin_msg_preprocess(msg):
    """将 Jellyfin 消息格式统一为 Emby 格式"""
    data = json.loads(msg)
    # Jellyfin webhook flat format: {NotificationType, Name, ItemType, ...}
    if "NotificationType" in data and "Event" not in data:
        nt = data.get("NotificationType", "")
        if nt in ("ItemAdded",):
            data["Event"] = "library.new"
        # Map ItemType -> Type (used by create_media)
        if "ItemType" in data and "Type" not in data:
            data["Type"] = data.pop("ItemType")
        # Convert flat Provider_* fields to ProviderIds dict
        provider_ids = {}
        for k in list(data.keys()):
            if k.startswith("Provider_"):
                provider_name = k[9:]  # e.g. "tvdb", "imdb", "tmdb"
                provider_ids[provider_name.capitalize()] = data.pop(k)
        if provider_ids:
            data["ProviderIds"] = provider_ids
        # Wrap in Emby key
        emby_fields = {}
        for k, v in list(data.items()):
            if k not in ("Event",):
                emby_fields[k] = data.pop(k)
        data["Emby"] = emby_fields
    # Legacy Jellyfin wrapper: {Jellyfin: {...}} -> {Emby: {...}}
    elif "Emby" not in data and "Jellyfin" in data:
        data["Emby"] = data.pop("Jellyfin")
    if "ServerType" not in data.get("Emby", {}):
        data.setdefault("Emby", {})["ServerType"] = "Jellyfin"
    return json.dumps(data, ensure_ascii=False)


def create_media(media_type):
    """工厂方法：根据类型创建媒体对象"""
    if media_type == "Movie":
        return Movie()
    elif media_type == "Episode":
        return Episode()
    else:
        return None


# ──────────────────────────────────────────────
#  Main Processing Entry
# ──────────────────────────────────────────────


def process_media(msg, port_id):
    """
    处理媒体消息主入口。
    1. 解析 Webhook JSON
    2. 检查 DND 状态
    3. DND 中 → 存入队列; 非 DND → 获取详情并推送
    """
    # 预处理 Jellyfin 消息
    msg = jellyfin_msg_preprocess(msg)
    data = json.loads(msg)

    if "Emby" not in data:
        log.logger.warning("No 'Emby' field in message, skipping.")
        return

    emby_data = data["Emby"]
    event = data.get("Event", "")

    if event != "library.new":
        log.logger.info(f"Event '{event}' is not 'library.new', skipping.")
        return

    # 检查端口配置
    port_config = db.get_port(port_id)
    if port_config is None:
        log.logger.error(f"Port config not found for port_id={port_id}")
        return

    # 覆盖 server_name
    if port_config.get("server_name"):
        emby_data["ServerName"] = port_config["server_name"]
    if port_config.get("server_url"):
        emby_data["ServerURL"] = port_config["server_url"]
    emby_data["ServerType"] = port_config.get("server_type", "Emby")

    # 检查 DND
    dnd = db.get_dnd_settings()
    if dnd["enabled"] and _is_in_dnd(dnd["start_time"], dnd["end_time"]):
        log.logger.info(
            f"[Port {port_id}] DND active, queuing message."
        )
        db.enqueue_message(port_id, json.dumps(emby_data, ensure_ascii=False))
        return

    # 非 DND，处理并推送
    _fetch_and_send(emby_data, port_id)


def _fetch_and_send(emby_data, port_id):
    """获取媒体详情并推送"""
    media_type = emby_data.get("Type", "")
    media_obj = create_media(media_type)
    if media_obj is None:
        log.logger.warning(f"Unsupported media type: {media_type}")
        return

    media_obj.port_id_ = port_id
    media_obj.parse_info(emby_data)
    log.logger.info(f"[Port {port_id}] Processing: {media_obj}")

    try:
        media_obj.get_details()
    except Exception as e:
        log.logger.error(f"[Port {port_id}] Failed to get media details: {e}")
        return

    # 创建 Sender 并推送
    enabled_channels = db.get_enabled_channels(port_id)
    if not enabled_channels:
        log.logger.warning(f"[Port {port_id}] No enabled channels, skipping push.")
        return

    port_config = db.get_port(port_id)
    sender = PortSender(
        port_id,
        port_config.get("server_name", ""),
        enabled_channels,
    )
    sender.send_media_details(media_obj.media_detail_)
    log.logger.info(f"[Port {port_id}] Media details sent successfully.")


def flush_queue_for_port(port_id):
    """处理指定端口的队列消息"""
    messages = db.get_pending_messages(port_id)
    if not messages:
        return 0

    enabled_channels = db.get_enabled_channels(port_id)
    if not enabled_channels:
        log.logger.warning(f"[Port {port_id}] No enabled channels for queue flush.")
        return 0

    port_config = db.get_port(port_id)
    sender = PortSender(
        port_id,
        port_config.get("server_name", ""),
        enabled_channels,
    )

    sent_count = 0
    for msg in messages:
        try:
            emby_data = json.loads(msg["media_json"])
            media_type = emby_data.get("Type", "")
            media_obj = create_media(media_type)
            if media_obj is None:
                db.update_message_status(msg["id"], "failed", "Unsupported media type")
                continue

            media_obj.parse_info(emby_data)
            media_obj.get_details()
            sender.send_media_details(media_obj.media_detail_)
            db.update_message_status(msg["id"], "sent")
            sent_count += 1
            log.logger.info(f"[Port {port_id}] Queue message #{msg['id']} sent.")
        except Exception as e:
            db.update_message_status(msg["id"], "failed", str(e))
            log.logger.error(
                f"[Port {port_id}] Failed to send queue message #{msg['id']}: {e}"
            )

    return sent_count


# ──────────────────────────────────────────────
#  DND Helper
# ──────────────────────────────────────────────


def _is_in_dnd(start_time_str, end_time_str):
    """判断当前时间是否在勿扰时段内"""
    now = datetime.datetime.now().time()
    start = datetime.datetime.strptime(start_time_str, "%H:%M").time()
    end = datetime.datetime.strptime(end_time_str, "%H:%M").time()

    if start <= end:
        return start <= now <= end
    else:
        # 跨午夜，例如 23:00 ~ 07:00
        return now >= start or now <= end


def send_test_notification(port_id):
    """
    发送测试通知，直接构造推送数据格式，跳过 TMDB 查询。
    用于验证推送渠道配置是否正确。
    """
    port_config = db.get_port(port_id)
    if not port_config:
        raise Exception(f"Port {port_id} not found")

    enabled_channels = db.get_enabled_channels(port_id)
    if not enabled_channels:
        raise Exception("No enabled channels")

    # 构造电影格式的测试数据
    test_movie = {
        "server_name": port_config.get("server_name", "Test Server"),
        "server_url": port_config.get("server_url", "http://localhost"),
        "media_type": "Movie",
        "media_name": "测试电影",
        "media_rating": 8.5,
        "media_rel": "2024-01-15",
        "media_intro": "这是一部测试电影，用于验证推送通知功能是否正常工作。如果您收到此消息，说明推送配置已成功设置。",
        "media_tmdburl": "https://www.themoviedb.org/movie/12345",
        "media_poster": "https://image.tmdb.org/t/p/w500/test_poster.jpg",
        "media_backdrop": "https://image.tmdb.org/t/p/w500/test_backdrop.jpg",
        "media_still": "https://image.tmdb.org/t/p/w500/test_still.jpg",
    }

    # 构造剧集格式的测试数据
    test_episode = {
        "server_name": port_config.get("server_name", "Test Server"),
        "server_url": port_config.get("server_url", "http://localhost"),
        "media_type": "Episode",
        "media_name": "测试剧集",
        "tv_season": 1,
        "tv_episode": 1,
        "tv_episode_name": "测试集",
        "media_rating": 9.0,
        "media_rel": "2024-02-20",
        "media_intro": "这是一部测试剧集的第一季第一集，用于验证推送通知功能是否正常工作。如果您收到此消息，说明推送配置已成功设置。",
        "media_tmdburl": "https://www.themoviedb.org/tv/67890",
        "media_poster": "https://image.tmdb.org/t/p/w500/test_tv_poster.jpg",
        "media_backdrop": "https://image.tmdb.org/t/p/w500/test_tv_backdrop.jpg",
        "media_still": "https://image.tmdb.org/t/p/w500/test_tv_still.jpg",
    }

    # 创建 Sender 并发送两种格式的测试消息
    sender = PortSender(
        port_id,
        port_config.get("server_name", ""),
        enabled_channels,
    )

    results = {}
    for ch in enabled_channels:
        ch_type = ch["channel_type"]
        try:
            if ch_type == "wechat_work":
                sender._send_wechat_news(test_movie)
                results["wechat_work_movie"] = "success"
                sender._send_wechat_news(test_episode)
                results["wechat_work_episode"] = "success"
            elif ch_type == "telegram":
                sender._send_telegram(test_movie)
                results["telegram_movie"] = "success"
                sender._send_telegram(test_episode)
                results["telegram_episode"] = "success"
            elif ch_type == "bark":
                sender._send_bark(test_movie)
                results["bark_movie"] = "success"
                sender._send_bark(test_episode)
                results["bark_episode"] = "success"
        except Exception as e:
            results[f"{ch_type}_error"] = str(e)
            log.logger.error(f"[Port {port_id}] Test notification failed for {ch_type}: {e}")

    return results

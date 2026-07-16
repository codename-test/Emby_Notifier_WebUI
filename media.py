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
            "tmdb_failed": False,
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
            log.logger.debug(f"TMDB ID already known: {existing_tmdb}")
            return

        log.logger.debug(f"Searching TMDB: {self.info_['Name']} ({self.info_['PremiereYear']})")
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
                log.logger.debug(f"TMDB ID matched via TVDB: {m['id']}")
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
                log.logger.debug(f"Name search failed, trying TVDB ID: {Tvdb_id}")
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
        self.info_["Episode"] = emby_media_info.get("IndexNumber", emby_media_info.get("EpisodeNumber", 0))
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
        s, e = self.info_["Season"], self.info_["Episode"]
        self.media_detail_["media_episode"] = f"第{s}季第{e}集" if s and e else ""

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
            log.logger.warning(f"Failed to get episode details, using fallback: {err}, using show info")
            ep_details = {}

        self.media_detail_["media_name"] = tv_details.get("name", self.info_["Name"])
        self.media_detail_["media_rating"] = tv_details.get("vote_average", 0)
        self.media_detail_["media_intro"] = ep_details.get("overview", tv_details.get("overview", "暂无简介"))
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
    """将 Jellyfin/Emby 消息格式统一为内部 Emby 格式

    支持三种格式：
    1. Jellyfin webhook: {NotificationType, ItemType, Name, Provider_*, ...}
    2. Emby webhook:     {Event, Item: {Type, Name, ProviderIds, ...}, Server: {...}}
    3. 已有 Emby 包装:   {Event, Emby: {Type, Name, ...}}
    """
    data = json.loads(msg)

    # --- Step 1: Normalize Event field ---
    if "NotificationType" in data and "Event" not in data:
        nt = data.get("NotificationType", "")
        if nt in ("ItemAdded",):
            data["Event"] = "library.new"

    # --- Step 2: Extract media fields ---
    # Emby webhook: Item contains the media object
    if "Item" in data and "Emby" not in data:
        data["Emby"] = data.pop("Item")
    # Legacy Jellyfin wrapper: {Jellyfin: {...}}
    elif "Emby" not in data and "Jellyfin" in data:
        data["Emby"] = data.pop("Jellyfin")
    # Already has Emby key (e.g. Emby server direct format)
    elif "Emby" in data:
        pass  # Already correct structure

    # --- Step 3: Common field mapping for Jellyfin flat format ---
    # (applies when fields are at top level, not yet wrapped)
    if "Emby" not in data:
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

    # --- Step 4: Wrap remaining top-level fields into Emby if not done ---
    if "Emby" not in data:
        emby_fields = {}
        for k, v in list(data.items()):
            if k not in ("Event",):
                emby_fields[k] = data.pop(k)
        data["Emby"] = emby_fields

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


def process_media(msg, port_id, skip_dnd=False):
    """
    处理媒体消息主入口。
    1. 解析 Webhook JSON
    2. 检查 DND 状态（skip_dnd=True 时跳过）
    3. DND 中 → 存入队列; 非 DND → 获取详情并推送
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    # 预处理 Jellyfin 消息
    msg = jellyfin_msg_preprocess(msg)
    data = json.loads(msg)

    if "Emby" not in data:
        log.logger.debug("No 'Emby' field in message, skipping.")
        return False

    emby_data = data["Emby"]
    event = data.get("Event", "")

    if event != "library.new":
        log.logger.debug(f"Event '{event}' is not 'library.new', skipping.")
        return False

    # 检查端口配置
    port_config = db.get_port(port_id)
    if port_config is None:
        log.logger.error(f"Port config not found for port_id={port_id}")
        return False

    # 覆盖 server_name
    if port_config.get("server_name"):
        emby_data["ServerName"] = port_config["server_name"]
    if port_config.get("server_url"):
        emby_data["ServerURL"] = port_config["server_url"]
    emby_data["ServerType"] = "Emby"

    # 检查 DND（skip_dnd 时跳过，用于队列刷新）
    if not skip_dnd:
        dnd = db.get_dnd_settings()
        if dnd["enabled"] and _is_in_dnd(dnd["start_time"], dnd["end_time"]):
            log.logger.info(
                f"[Port {port_id}] DND active, queuing message."
            )
            db.enqueue_message(port_id, json.dumps(emby_data, ensure_ascii=False))
            return False

    # 非 DND，处理并推送
    try:
        _fetch_and_send(emby_data, port_id)
        return True
    except Exception as e:
        log.logger.error(f"[Port {port_id}] Send failed: {e}")
        return False


def _fetch_and_send(emby_data, port_id):
    """获取媒体详情并推送
    
    Returns:
        bool: True if sent successfully to all channels, False otherwise
    """
    # 去重：同一 ItemId + Event 24小时内不重复推送
    item_id = emby_data.get("Id", "")
    if item_id and db.is_duplicate_webhook(item_id):
        log.logger.debug(f"[Port {port_id}] Duplicate webhook skipped: item_id={item_id}")
        return False

    media_type = emby_data.get("Type", "")
    media_obj = create_media(media_type)
    if media_obj is None:
        log.logger.error(f"Unsupported media type: {media_type}")
        return False

    media_obj.port_id_ = port_id
    media_obj.parse_info(emby_data)
    log.logger.debug(f"[Port {port_id}] Processing: {media_obj}")

    # 检查端口使用的模板是否无图，无图模板不需要 TMDB
    port_config = db.get_port(port_id)
    template = db.get_template(port_config.get("template_id", 1))
    skip_tmdb = template and not template.get("enable_image", 1)

    if skip_tmdb:
        log.logger.debug(f"[Port {port_id}] No-image template '{template['name']}', skipping TMDB fetch")
        media_obj.media_detail_["skip_tmdb"] = True
        media_obj.media_detail_["tmdb_failed"] = False
        media_obj.media_detail_["media_name"] = media_obj.info_.get("Name", "")
        media_obj.media_detail_["media_rel"] = str(media_obj.info_.get("PremiereYear", ""))
        media_obj.media_detail_["media_intro"] = emby_data.get("Overview", "")
        media_obj.media_detail_["media_rating"] = emby_data.get("CommunityRating", 0) or 0
        media_obj.media_detail_["media_tmdburl"] = ""
    else:
        try:
            media_obj.get_details()
        except Exception as e:
            log.logger.warning(f"[Port {port_id}] TMDB fetch failed: {e}, using fallback template")
            media_obj.media_detail_["tmdb_failed"] = True
            media_obj.media_detail_["skip_tmdb"] = False
            media_obj.media_detail_["media_name"] = media_obj.info_.get("Name", "")
            media_obj.media_detail_["media_rel"] = str(media_obj.info_.get("PremiereYear", ""))
            media_obj.media_detail_["media_intro"] = emby_data.get("Overview", "")
            media_obj.media_detail_["media_rating"] = emby_data.get("CommunityRating", 0) or 0
            media_obj.media_detail_["media_tmdburl"] = ""
            # fall through to push

    # 创建 Sender 并推送
    port_config = db.get_port(port_id)
    channel_ids = json.loads(port_config.get("channel_ids", "[]")) if port_config else []
    if not channel_ids:
        log.logger.error(f"[Port {port_id}] No channels configured, skipping push.")
        return False

    sender = PortSender(
        port_id,
        port_config.get("server_name", ""),
        channel_ids,
    )
    
    if not sender.has_channels():
        log.logger.error(f"[Port {port_id}] No channels available, cannot send.")
        return False
    
    ok = sender.send_media_details(media_obj.media_detail_)
    if ok:
        log.logger.debug(f"[Port {port_id}] Media details sent successfully.")
        if item_id:
            db.record_webhook(item_id)
    else:
        log.logger.error(f"[Port {port_id}] Some channels failed to send.")
    return ok


def flush_queue_for_port(port_id):
    """处理指定端口的队列消息，复用 _fetch_and_send 的完整推送逻辑"""
    messages = db.get_pending_messages(port_id)
    if not messages:
        return 0

    port_config = db.get_port(port_id)
    if port_config is None:
        return 0

    sent_count = 0
    for msg in messages:
        try:
            emby_data = json.loads(msg["media_json"])
            # 确保有 ServerType 和 ServerName
            if "ServerType" not in emby_data:
                emby_data["ServerType"] = "Emby"
            if "ServerName" not in emby_data and port_config.get("server_name"):
                emby_data["ServerName"] = port_config["server_name"]

            ok = _fetch_and_send(emby_data, port_id)
            if ok:
                db.delete_message(msg["id"])
                sent_count += 1
                log.logger.debug(f"[Port {port_id}] Queue message #{msg['id']} sent and deleted.")
            else:
                db.update_message_status(msg["id"], "failed", "Channel send failed (see logs)")
                log.logger.warning(f"[Port {port_id}] Queue message #{msg['id']} send failed.")
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

    channel_ids = json.loads(port_config.get("channel_ids", "[]")) if port_config else []
    if not channel_ids:
        raise Exception("No channels configured")

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
        channel_ids,
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

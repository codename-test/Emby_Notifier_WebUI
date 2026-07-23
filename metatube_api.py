#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
MetaTube API 客户端
调用 MetaTube Server 获取影片元数据

图片获取策略（逐级退避）：
  1. 原始 cover_url — 如果非防盗链域名，直接使用
  2. DMM/JAV321 源封面 — 搜索结果中优先选可外链的源
  3. 剧照 preview_images[0] — 保底方案
"""

import re
import requests
import log
import db


# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

def get_config():
    """从数据库读取 MetaTube 配置"""
    config = db.get_all_system_config()
    server = config.get("METATUBE_SERVER", "").strip()
    token = config.get("METATUBE_TOKEN", "").strip()
    return server, token


def get_headers():
    """获取请求头（含认证）"""
    _, token = get_config()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ──────────────────────────────────────────────
#  Number Extraction
# ──────────────────────────────────────────────

def extract_number(item):
    """从 webhook 数据中提取番号
    
    优先级：
    1. ProviderIds (JavBus/JavDB ID) → 直接查详情
    2. FileName (正则提取)
    3. Path (正则提取)
    4. Name (正则提取或全文搜索)
    
    Returns:
        tuple: (mode, value)
            mode: "direct" (直接查详情) 或 "search" (模糊搜索)
            value: 番号或关键词
    """
    # 1. ProviderIds (最准)
    providers = item.get("ProviderIds", {})
    if providers:
        for provider in ["JavBus", "JavDB", "FANZA", "MGStage"]:
            if provider in providers:
                pid = providers[provider]
                if pid:
                    log.logger.debug(f"Found {provider} ID: {pid}")
                    return "direct", (provider.lower(), pid)
    
    # 2. FileName
    filename = item.get("FileName", "")
    match = re.search(r'([A-Z]+-\d+)', filename.upper())
    if match:
        log.logger.debug(f"Extracted number from FileName: {match.group(1)}")
        return "search", match.group(1)
    
    # 3. Path
    path = item.get("Path", "")
    match = re.search(r'([A-Z]+-\d+)', path.upper())
    if match:
        log.logger.debug(f"Extracted number from Path: {match.group(1)}")
        return "search", match.group(1)
    
    # 4. Name (可能是标题，也可能是编号)
    name = item.get("Name", "")
    match = re.search(r'([A-Z]+-\d+)', name.upper())
    if match:
        log.logger.debug(f"Extracted number from Name: {match.group(1)}")
        return "search", match.group(1)
    
    # 5. 兜底：直接用 Name 搜索
    if name:
        log.logger.debug(f"Using Name as search keyword: {name}")
        return "search", name
    
    return None, None


# ──────────────────────────────────────────────
#  API Calls
# ──────────────────────────────────────────────

def search_movie(keyword):
    """搜索影片
    
    Args:
        keyword: 搜索关键词（番号或标题）
    
    Returns:
        list: 搜索结果列表，每个元素包含 id, number, title, provider, cover_url 等
    """
    server, _ = get_config()
    if not server:
        raise Exception("MetaTube Server not configured")
    
    url = f"{server.rstrip('/')}/v1/movies/search"
    params = {"q": keyword}
    
    log.logger.debug(f"MetaTube search: {url} q={keyword}")
    resp = requests.get(url, params=params, headers=get_headers(), timeout=30)
    resp.raise_for_status()
    
    data = resp.json()
    results = data.get("data", [])
    log.logger.debug(f"MetaTube search returned {len(results)} results")
    return results


def get_movie_detail(provider, movie_id):
    """获取影片详情
    
    Args:
        provider: 数据源名称（如 javbus, javdb）
        movie_id: 影片 ID
    
    Returns:
        dict: 影片详情，包含 title, summary, cover_url, score, release_date 等
    """
    server, _ = get_config()
    if not server:
        raise Exception("MetaTube Server not configured")
    
    url = f"{server.rstrip('/')}/v1/movies/{provider}/{movie_id}"
    
    log.logger.debug(f"MetaTube detail: {url}")
    resp = requests.get(url, headers=get_headers(), timeout=30)
    resp.raise_for_status()
    
    data = resp.json()
    detail = data.get("data", {})
    log.logger.debug(f"MetaTube detail: {detail.get('title', 'N/A')}")
    return detail


# ─────────────────────────────────────────────
#  Image URL — 逐级退避策略
# ──────────────────────────────────────────────

# 已知防盗链的域名（这些域名的图片外部无法访问）
_BLOCKED_DOMAINS = [
    "www.javbus.com",
    "www.javdb.com",
    "javbus.com",
    "javdb.com",
]

# 已知可外链的封面源（优先选用）
_ACCESSIBLE_COVER_PROVIDERS = ["JAV321", "FANZA"]


def _is_blocked_url(url):
    """检查 URL 是否在防盗链域名列表中"""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in _BLOCKED_DOMAINS)


def _find_accessible_cover(results):
    """从搜索结果中查找可外链的封面源（DMM/FANZA/JAV321）
    
    Args:
        results: 搜索结果列表
    
    Returns:
        dict: 影片详情（含可访问的 cover_url），或 None
    """
    # 按优先级排序：先试 ACCESSIBLE_COVER_PROVIDERS 里的源
    for preferred in _ACCESSIBLE_COVER_PROVIDERS:
        for result in results:
            if result.get("provider", "").upper() == preferred.upper():
                cover = result.get("cover_url", "")
                if cover and not _is_blocked_url(cover):
                    provider = result.get("provider", "")
                    movie_id = result.get("id", "")
                    if provider and movie_id:
                        try:
                            detail = get_movie_detail(provider, movie_id)
                            if detail and not _is_blocked_url(detail.get("cover_url", "")):
                                log.logger.debug(
                                    f"MetaTube: Found accessible cover from {provider}: "
                                    f"{detail.get('cover_url', '')}"
                                )
                                return detail
                        except Exception as e:
                            log.logger.debug(f"MetaTube: {provider} detail failed: {e}")
                            continue
    
    # 遍历所有结果，找第一个 cover_url 不在黑名单里的
    for result in results:
        cover = result.get("cover_url", "")
        if cover and not _is_blocked_url(cover):
            provider = result.get("provider", "")
            movie_id = result.get("id", "")
            if provider and movie_id:
                try:
                    detail = get_movie_detail(provider, movie_id)
                    if detail and not _is_blocked_url(detail.get("cover_url", "")):
                        log.logger.debug(
                            f"MetaTube: Found accessible cover from {provider}: "
                            f"{detail.get('cover_url', '')}"
                        )
                        return detail
                except Exception as e:
                    log.logger.debug(f"MetaTube: {provider} detail failed: {e}")
                    continue
    
    return None


def _fallback_to_preview(detail):
    """用剧照（preview_images）作为封面保底
    
    Args:
        detail: 影片详情 dict（会被原地修改）
    
    Returns:
        dict: 修改后的 detail
    """
    if not detail:
        return detail
    
    previews = detail.get("preview_images", [])
    if previews and len(previews) > 0:
        new_url = previews[0]
        log.logger.info(f"MetaTube: Using preview image as cover (fallback): {new_url}")
        detail["cover_url"] = new_url
        detail["big_cover_url"] = new_url
    else:
        log.logger.warning("MetaTube: No preview_images available for fallback, cover will be empty")
        detail["cover_url"] = ""
        detail["big_cover_url"] = ""
    
    # 清理 thumb_url 如果也是防盗链
    if _is_blocked_url(detail.get("thumb_url", "")):
        detail["thumb_url"] = detail.get("cover_url", "")
    
    return detail


def _resolve_cover_url(detail, keyword=None, search_results=None):
    """逐级退避解析封面 URL
    
    优先级：
      1. 原始 cover_url 可用 → 直接用
      2. 搜索 DMM/JAV321 源的封面 → 用其详情替换
      3. preview_images[0] 剧照 → 保底
    
    Args:
        detail: 已获取的影片详情
        keyword: 搜索关键词（用于降级搜索）
        search_results: 已有的搜索结果（避免重复请求）
    
    Returns:
        dict: 处理后的 detail
    """
    if not detail:
        return detail
    
    cover_url = detail.get("cover_url", "")
    
    # Level 1: cover_url 可用，直接用
    if cover_url and not _is_blocked_url(cover_url):
        log.logger.debug(f"MetaTube: Using original cover_url: {cover_url}")
        return detail
    
    # cover_url 被封或为空，进入退避
    if cover_url:
        log.logger.warning(f"MetaTube: cover_url blocked ({cover_url}), trying fallback...")
    
    # Level 2: 尝试找可外链的封面源
    results = search_results
    if results is None and keyword:
        try:
            results = search_movie(keyword)
        except Exception as e:
            log.logger.debug(f"MetaTube: Search for accessible cover failed: {e}")
            results = []
    
    if results:
        accessible = _find_accessible_cover(results)
        if accessible:
            return accessible
    
    # Level 3: 剧照保底
    log.logger.warning("MetaTube: No accessible cover found, using preview image as fallback")
    return _fallback_to_preview(detail)


# ─────────────────────────────────────────────
#  High-level Fetch
# ──────────────────────────────────────────────

def fetch_movie(item):
    """获取影片元数据（自动选择搜索或直接查询）
    
    图片采用逐级退避策略：
      1. 原始 cover_url 可用 → 直接用
      2. DMM/JAV321 源的封面 → 替换
      3. preview_images[0] 剧照 → 保底
    
    Args:
        item: webhook 中的 Item 对象
    
    Returns:
        dict: 影片详情，包含 title, summary, cover_url, score, release_date 等
        None: 如果获取失败
    """
    mode, value = extract_number(item)
    if not mode:
        log.logger.warning("MetaTube: Could not extract number from item")
        return None
    
    try:
        keyword = None
        
        if mode == "direct":
            # 直接查询详情
            provider, movie_id = value
            detail = get_movie_detail(provider, movie_id)
            if detail:
                keyword = movie_id
                return _resolve_cover_url(detail, keyword=keyword)
            log.logger.warning(f"MetaTube direct query returned nothing: {provider}/{movie_id}")
            # 降级到搜索
            keyword = movie_id
        else:
            keyword = value
        
        # 搜索模式
        results = search_movie(keyword)
        if not results:
            log.logger.warning(f"MetaTube search returned no results for: {keyword}")
            return None
        
        # 优先选择有封面的结果
        for result in results:
            if result.get("cover_url"):
                provider = result.get("provider", "")
                movie_id = result.get("id", "")
                if provider and movie_id:
                    detail = get_movie_detail(provider, movie_id)
                    if detail:
                        return _resolve_cover_url(detail, keyword=keyword, search_results=results)
        
        # 兜底：取第一个结果
        first = results[0]
        provider = first.get("provider", "")
        movie_id = first.get("id", "")
        if provider and movie_id:
            detail = get_movie_detail(provider, movie_id)
            if detail:
                return _resolve_cover_url(detail, keyword=keyword, search_results=results)
        
        log.logger.warning("MetaTube: All results failed to fetch detail")
        return None
        
    except requests.Timeout:
        log.logger.warning("MetaTube API request timeout (30s)")
        return None
    except requests.RequestException as e:
        log.logger.error(f"MetaTube API request failed: {e}")
        return None
    except Exception as e:
        log.logger.error(f"MetaTube fetch error: {e}")
        return None

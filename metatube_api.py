#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
MetaTube API 客户端
调用 MetaTube Server 获取影片元数据
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
    config = db.get_all_config()
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
#  High-level Fetch
# ──────────────────────────────────────────────

def fetch_movie(item):
    """获取影片元数据（自动选择搜索或直接查询）
    
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
        if mode == "direct":
            # 直接查询详情
            provider, movie_id = value
            detail = get_movie_detail(provider, movie_id)
            if detail and detail.get("cover_url"):
                return detail
            log.logger.warning(f"MetaTube direct query returned no cover: {provider}/{movie_id}")
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
                        return detail
        
        # 兜底：取第一个结果
        first = results[0]
        provider = first.get("provider", "")
        movie_id = first.get("id", "")
        if provider and movie_id:
            detail = get_movie_detail(provider, movie_id)
            if detail:
                return detail
        
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

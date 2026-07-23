#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
翻译模块
支持百度翻译和 Google 免费翻译
"""

import requests
import hashlib
import random
import log
import db


# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

def get_config():
    """从数据库读取翻译配置"""
    config = db.get_all_system_config()
    enabled = config.get("TRANSLATION_ENABLED", "0") == "1"
    engine = config.get("TRANSLATION_ENGINE", "google_free").lower()
    baidu_app_id = config.get("BAIDU_APP_ID", "").strip()
    baidu_app_key = config.get("BAIDU_APP_KEY", "").strip()
    return enabled, engine, baidu_app_id, baidu_app_key


# ──────────────────────────────────────────────
#  Google Free Translation
# ──────────────────────────────────────────────

def translate_google_free(text, target_lang="zh-CN"):
    """Google 免费翻译（无需 API key）
    
    Args:
        text: 待翻译文本
        target_lang: 目标语言（默认中文）
    
    Returns:
        str: 翻译后的文本
    """
    if not text:
        return text
    
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # 解析结果
        translated = ""
        if data and data[0]:
            for segment in data[0]:
                if segment[0]:
                    translated += segment[0]
        
        return translated
    except Exception as e:
        log.logger.warning(f"Google Free translation failed: {e}")
        return text


# ──────────────────────────────────────────────
#  Baidu Translation
# ──────────────────────────────────────────────

def translate_baidu(text, app_id, app_key, target_lang="zh"):
    """百度翻译
    
    Args:
        text: 待翻译文本
        app_id: 百度翻译 App ID
        app_key: 百度翻译 App Key
        target_lang: 目标语言（默认中文）
    
    Returns:
        str: 翻译后的文本
    """
    if not text:
        return text
    
    url = "https://api.fanyi.baidu.com/api/trans/vip/translate"
    
    # 生成随机盐
    salt = str(random.randint(32768, 65536))
    
    # 计算签名
    sign_str = app_id + text + salt + app_key
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    params = {
        "q": text,
        "from": "auto",
        "to": target_lang,
        "appid": app_id,
        "salt": salt,
        "sign": sign
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if "trans_result" in data:
            translated = ""
            for item in data["trans_result"]:
                if "dst" in item:
                    translated += item["dst"]
            return translated
        else:
            error_code = data.get("error_code", "unknown")
            error_msg = data.get("error_msg", "unknown")
            log.logger.warning(f"Baidu translation error: {error_code} - {error_msg}")
            return text
    except Exception as e:
        log.logger.warning(f"Baidu translation failed: {e}")
        return text


# ──────────────────────────────────────────────
#  High-level Translate
# ──────────────────────────────────────────────

def translate(text):
    """翻译文本（根据配置自动选择引擎）
    
    Args:
        text: 待翻译文本
    
    Returns:
        str: 翻译后的文本（如果翻译失败则返回原文）
    """
    enabled, engine, baidu_app_id, baidu_app_key = get_config()
    
    if not enabled:
        return text
    
    if engine == "baidu":
        if not baidu_app_id or not baidu_app_key:
            log.logger.warning("Baidu translation enabled but App ID/Key not configured")
            return text
        return translate_baidu(text, baidu_app_id, baidu_app_key)
    else:
        # 默认 Google Free
        return translate_google_free(text)


def translate_movie_data(detail):
    """翻译影片数据（标题 + 简介）
    
    Args:
        detail: MetaTube 返回的影片详情 dict
    
    Returns:
        dict: 翻译后的影片详情
    """
    if not detail:
        return detail
    
    enabled, _, _, _ = get_config()
    if not enabled:
        return detail
    
    # 翻译标题
    if detail.get("title"):
        detail["title"] = translate(detail["title"])
    
    # 翻译简介
    if detail.get("summary"):
        detail["summary"] = translate(detail["summary"])
    
    return detail

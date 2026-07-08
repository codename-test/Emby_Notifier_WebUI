#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
企业微信 API 封装
Token 缓存由调用方通过参数传入，支持多端口独立配置。
"""

import requests
import json
import time
import log

# 消息推送基础 URL
SEND_MSG_URL = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="


def _get_token_url(corp_id, corp_secret):
    return (
        f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?"
        f"corpid={corp_id}&corpsecret={corp_secret}"
    )


def get_access_token(corp_id, corp_secret, token_cache):
    """
    获取企业微信应用 access_token。
    token_cache: dict with keys {access_token, expires_in, expires_time}
    """
    current_time = time.time()
    if token_cache.get("access_token") and token_cache.get("expires_time", 0) > current_time:
        return token_cache["access_token"]

    try:
        url = _get_token_url(corp_id, corp_secret)
        res = requests.get(url)
        res.raise_for_status()
        if res.json()["errcode"] != 0:
            raise Exception(f"{res.text}")
        log.logger.debug(log.SensitiveData(res.text))

        token_cache["access_token"] = res.json()["access_token"]
        token_cache["expires_in"] = res.json()["expires_in"]
        token_cache["expires_time"] = current_time + token_cache["expires_in"]
        log.logger.info(f"Update WeChat access token successful. Token: {token_cache['access_token']}")
        return token_cache["access_token"]
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"Get access token failed. Check network connection: {e}")
        raise e
    except Exception as e:
        log.logger.error(f"Get access token failed. Error: {e}")
        raise e


def send_text(access_token, user_id, agent_id, content):
    """发送文本消息"""
    payload = {
        "touser": user_id,
        "agentid": agent_id,
        "safe": 0,
        "msgtype": "text",
        "text": {"content": content},
    }
    log.logger.debug(log.SensitiveData(json.dumps(payload, ensure_ascii=False)))

    send_msg_url = SEND_MSG_URL + access_token
    try:
        res = requests.post(send_msg_url, json=payload)
        res.raise_for_status()
        if res.json()["errcode"] != 0:
            raise Exception(res.text)
        log.logger.debug(f"Send text message successful. Response: {res.json()}")
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"Send text message failed. Check network connection: {e}")
        raise e
    except Exception as e:
        log.logger.error(f"Send text message failed. Error: {e}")
        raise e


def send_news(access_token, user_id, agent_id, title, description, url, picurl):
    """发送图文卡片消息"""
    payload = {
        "touser": user_id,
        "agentid": agent_id,
        "safe": 0,
        "msgtype": "news",
        "news": {
            "articles": [
                {
                    "title": title,
                    "description": description,
                    "url": url,
                    "picurl": picurl,
                }
            ]
        },
    }
    log.logger.debug(log.SensitiveData(json.dumps(payload, ensure_ascii=False)))

    send_msg_url = SEND_MSG_URL + access_token
    try:
        res = requests.post(send_msg_url, json=payload)
        res.raise_for_status()
        if res.json()["errcode"] != 0:
            raise Exception(res.text)
        log.logger.debug(f"Send news message successful. Response: {res.json()}")
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"Send news message failed. Check network connection: {e}")
        raise e
    except Exception as e:
        log.logger.error(f"Send news message failed. Error: {e}")
        raise e


def check_authorization(corp_id, corp_secret):
    """检查企业微信应用授权"""
    try:
        url = _get_token_url(corp_id, corp_secret)
        res = requests.get(url)
        res.raise_for_status()
        if res.json()["errcode"] != 0:
            raise Exception(f"{res.text}")
        log.logger.info(f"WeChat Work authorization successful. Corp ID: {corp_id}")
        return res.json()["access_token"]
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"WeChat Work authorization failed. Check network connection: {e}")
        raise e
    except Exception as e:
        log.logger.error(f"WeChat Work authorization failed. Error: {e}")
        raise e

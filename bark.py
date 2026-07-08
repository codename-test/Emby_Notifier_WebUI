#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Bark 推送 API 封装
"""

import requests
import json
import log


def send_message(server, device_keys, content: dict):
    """
    发送 Bark 推送消息。
    server: Bark 服务器地址
    device_keys: 设备 key 列表
    content: 推送内容 dict
    """
    if not server or not device_keys:
        log.logger.error("Bark server or device keys not set.")
        return

    url = f"{server}/push"
    payload = dict(content)
    payload["device_keys"] = device_keys
    log.logger.debug(f"Bark push payload: {payload}")
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"Bark connection error: {e}")
        raise
    except Exception as e:
        log.logger.error(f"Bark error sending message: {e}")
        raise

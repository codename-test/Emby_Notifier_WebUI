#!/usr/bin/python3
# -*- coding: UTF-8 -*-
"""
Telegram Bot API 封装
保留代码，默认不启用。通过 WebUI 可开启。
"""

import requests, json, os
import log


def _get_bot_url(bot_token):
    return f"https://api.telegram.org/bot{bot_token}/"


def send_message(bot_token, chat_id, text):
    payload = {
        "method": "sendMessage",
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    log.logger.debug(log.SensitiveData(json.dumps(payload, ensure_ascii=False)))
    try:
        res = requests.post(_get_bot_url(bot_token), json=payload)
        res.raise_for_status()
    except Exception as e:
        log.logger.error(json.dumps(payload, ensure_ascii=False))
        log.logger.debug(res.text)
        raise e


def send_photo(bot_token, chat_id, caption, photo):
    payload = {
        "method": "sendPhoto",
        "chat_id": chat_id,
        "photo": photo,
        "caption": caption,
        "parse_mode": "Markdown",
    }
    log.logger.debug(log.SensitiveData(json.dumps(payload, ensure_ascii=False)))
    try:
        res = requests.post(_get_bot_url(bot_token), json=payload)
        res.raise_for_status()
    except Exception as e:
        log.logger.error(json.dumps(payload, ensure_ascii=False))
        log.logger.debug(res.text)
        raise e


def bot_authorization(bot_token):
    try:
        res = requests.get(_get_bot_url(bot_token) + "getMe")
        res.raise_for_status()
        log.logger.debug(log.SensitiveData(res.text))
        log.logger.debug(
            f"Telegram bot authorization successful. Current bot: {res.json()['result']['username']}"
        )
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"Telegram bot authorization failed. Check network connection: {e}")
        raise e
    except Exception as e:
        log.logger.error(f"Telegram bot authorization failed. Error: {e}")
        raise e


def get_chat(bot_token, chat_id):
    payload = {
        "method": "getChat",
        "chat_id": chat_id,
    }
    try:
        res = requests.post(_get_bot_url(bot_token), json=payload)
        res.raise_for_status()
        log.logger.debug(log.SensitiveData(res.text))
        chat_type = res.json()['result']['type']
        if chat_type == 'private':
            log.logger.debug(
                f"Telegram getChat successful. Chat User: [{res.json()['result']['username']}], type: {chat_type}"
            )
        elif chat_type == 'channel':
            log.logger.debug(
                f"Telegram getChat successful. Chat title: [{res.json()['result']['title']}], type: {chat_type}"
            )
        else:
            log.logger.debug(
                f"Telegram getChat successful. Chat type: {chat_type}, Chat Detail: {res.json()['result']}"
            )
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"Telegram getChat failed. Check network connection: {e}")
        raise e
    except Exception as e:
        log.logger.error(json.dumps(payload, ensure_ascii=False))
        log.logger.error(f"Telegram getChat failed. Error: {e}")
        raise e

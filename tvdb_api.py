#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import requests, os
import log

TVDB_API = "https://api4.thetvdb.com/v4"

TVDB_API_KEY = os.getenv("TVDB_API_KEY")

TVDB_API_TOKEN = ""

TVDB_API_HEADERS = {
    "accept": "application/json",
    "Authorization": "Bearer {TVDB_API_TOKEN}",
}


def login():
    """
    Log in to the TVDB API and get an access token.
    """
    if not TVDB_API_KEY:
        log.logger.warning("TVDB_API_KEY not configured, skipping TVDB login.")
        return None, "TVDB_API_KEY not configured"

    login_url = f"{TVDB_API}/login"
    login_data = {"apikey": TVDB_API_KEY}
    try:
        response = requests.post(login_url, json=login_data, headers=TVDB_API_HEADERS)
        response.raise_for_status()
        log.logger.debug("TVDB login successful.")
        global TVDB_API_TOKEN
        TVDB_API_TOKEN = response.json().get("data", {}).get("token", "")
        log.logger.debug(response.json())
        TVDB_API_HEADERS["Authorization"] = f"Bearer {TVDB_API_TOKEN}"
        return TVDB_API_TOKEN, None
    except requests.exceptions.RequestException as e:
        if response.status_code == 401:
            log.logger.error(
                f"TVDB login failed. {response.json()['message']} Current API key: {TVDB_API_KEY}"
            )
        return None, f"TVDB login failed. Check network connection or API key: {e}"


def get_seriesid_by_episodeid(episode_id):
    """
    Get the series ID for a given episode ID.
    """
    if not TVDB_API_KEY:
        return None, "TVDB_API_KEY not configured"

    global TVDB_API_TOKEN
    log.logger.debug(f"TVDB_API_TOKEN: {TVDB_API_TOKEN}, TVDB_API_KEY: {TVDB_API_KEY}")
    for _ in range(2):
        if TVDB_API_TOKEN == "" or TVDB_API_TOKEN is None:
            TVDB_API_TOKEN, err = login()
            if err:
                return None, err
        episode_url = f"{TVDB_API}/episodes/{episode_id}"
        try:
            response = requests.get(episode_url, headers=TVDB_API_HEADERS)
            response.raise_for_status()
            return response.json().get("data", {}).get("seriesId"), None
        except requests.exceptions.RequestException as e:
            if e.response.status_code == 401:
                TVDB_API_TOKEN = ""
                continue
            else:
                return None, f"TVDB episode ID {episode_id} not found: {e}"
    return None, f"TVDB episode ID {episode_id} not found"


def search_series(series_name, year):
    """
    Search for a TV series by name and year.
    """
    if not TVDB_API_KEY:
        return None, "TVDB_API_KEY not configured"

    global TVDB_API_TOKEN
    for _ in range(2):
        if TVDB_API_TOKEN == "" or TVDB_API_TOKEN is None:
            TVDB_API_TOKEN, err = login()
            if err:
                return None, err
        search_url = f"{TVDB_API}/search?query={series_name}&type=series&year={year}"
        try:
            response = requests.get(search_url, headers=TVDB_API_HEADERS)
            response.raise_for_status()
            results = response.json().get("data", [])
            if results:
                return results[0].get("tvdb_id"), None
            return None, f"TVDB search for {series_name} ({year}) returned no results"
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response.status_code == 401:
                TVDB_API_TOKEN = ""
                continue
            else:
                return None, f"TVDB search for {series_name} failed: {e}"
    return None, f"TVDB search for {series_name} failed after retries"

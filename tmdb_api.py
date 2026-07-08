#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import requests, os, log
import db

TMDB_API = "https://api.themoviedb.org/3"

TMDB_IMAGE_DOMAIN = os.getenv("TMDB_IMAGE_DOMAIN", "https://image.tmdb.org")

TMDB_LANG = "zh-CN"


def get_tmdb_token():
    """从数据库获取 TMDB API Token"""
    return db.get_system_config("TMDB_API_TOKEN")


def get_headers():
    """获取 TMDB API 请求头"""
    token = get_tmdb_token()
    if not token:
        return None
    return {
        "accept": "application/json",
        "Authorization": "Bearer {}".format(token),
    }


TMDB_MEDIA_TYPES = {
    "Movie": "movie",
    "Episode": "tv",
}


def login():
    """
    Logs in to the TMDB API.
    """
    headers = get_headers()
    if not headers:
        log.logger.error("TMDB_API_TOKEN not configured! Please set it in WebUI.")
        return False
    
    login_url = f"{TMDB_API}/authentication"
    try:
        response = requests.get(login_url, headers=headers, timeout=5)
        response.raise_for_status()
        log.logger.info("TMDB login successful.")
        return True
    except requests.exceptions.ConnectionError as e:
        log.logger.error(f"TMDB login failed. Check network connection: {e}")
        return False
    except requests.exceptions.RequestException as e:
        log.logger.error(
            f"TMDB login failed. {response.json()['status_message']}"
        )
        return False


def search_media(media_type, name, year):
    """
    Search for movies or TV shows on TMDB API.
    """
    headers = get_headers()
    if not headers:
        return [], "TMDB_API_TOKEN not configured"
    
    media_type = (
        TMDB_MEDIA_TYPES[media_type] if media_type in TMDB_MEDIA_TYPES else media_type
    )
    search_url = f"{TMDB_API}/search/{media_type}?query={name}&language={TMDB_LANG}&page=1"
    if year != -1:
        search_url += f"&year={year}"
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        return response.json().get("results", []), None
    except requests.exceptions.RequestException as e:
        return (
            [],
            f"TMDB search for {name} failed. Check network connection or API token: {e}",
        )


def get_external_ids(media_type, tmdb_id):
    """
    Fetches the external IDs for a given media type and TMDB ID.
    """
    headers = get_headers()
    if not headers:
        return {}, "TMDB_API_TOKEN not configured"
    
    media_type = (
        TMDB_MEDIA_TYPES[media_type] if media_type in TMDB_MEDIA_TYPES else media_type
    )
    external_ids_url = (
        f"{TMDB_API}/{media_type}/{tmdb_id}/external_ids?language={TMDB_LANG}"
    )
    try:
        response = requests.get(external_ids_url, headers=headers)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return (
            {},
            f"TMDB get external IDs for {media_type}/{tmdb_id} failed: {e}",
        )


def get_movie_details(movie_id):
    """
    Fetches the details for a given movie ID.
    """
    headers = get_headers()
    if not headers:
        return {}, "TMDB_API_TOKEN not configured"
    
    details_url = f"{TMDB_API}/movie/{movie_id}?language={TMDB_LANG}"
    try:
        response = requests.get(details_url, headers=headers)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return (
            {},
            f"TMDB get movie details for {movie_id} failed: {e}",
        )


def get_tv_details(tv_id):
    """
    Fetches the details for a given TV ID.
    """
    headers = get_headers()
    if not headers:
        return {}, "TMDB_API_TOKEN not configured"
    
    details_url = f"{TMDB_API}/tv/{tv_id}?language={TMDB_LANG}"
    try:
        response = requests.get(details_url, headers=headers)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return (
            {},
            f"TMDB get TV details for {tv_id} failed: {e}",
        )


def get_tv_episode_details(tv_id, season_number, episode_number):
    """
    Fetches the details for a given TV episode.
    """
    headers = get_headers()
    if not headers:
        return {}, "TMDB_API_TOKEN not configured"
    
    episode_url = (
        f"{TMDB_API}/tv/{tv_id}/season/{season_number}/episode/{episode_number}"
        f"?language={TMDB_LANG}"
    )
    try:
        response = requests.get(episode_url, headers=headers)
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return (
            {},
            f"TMDB get TV episode details for {tv_id}/S{season_number}E{episode_number} failed: {e}",
        )


def get_poster_url(poster_path, size="w500"):
    """
    Returns the full poster URL for a given poster path.
    """
    return f"{TMDB_IMAGE_DOMAIN}/t/p/{size}{poster_path}"


def get_still_url(still_path, size="w500"):
    """
    Returns the full still URL for a given still path.
    """
    return f"{TMDB_IMAGE_DOMAIN}/t/p/{size}{still_path}"

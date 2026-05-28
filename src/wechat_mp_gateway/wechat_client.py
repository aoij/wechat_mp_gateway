from __future__ import annotations

import base64
import json
import time
from typing import Any

import requests
from fastapi import HTTPException

from .config import Settings, get_settings
from .schemas import DraftArticleRequest, ImagePayload


WECHAT_API_BASE = "https://api.weixin.qq.com"
TOKEN_SKEW_SECONDS = 300

_token_cache: dict[str, Any] = {"access_token": "", "expires_at": 0.0}


class WechatAPIError(RuntimeError):
    pass


def _settings(settings: Settings | None = None) -> Settings:
    return settings or get_settings()


def ensure_wechat_config(settings: Settings | None = None) -> Settings:
    config = _settings(settings)
    if not config.wechat_appid or not config.wechat_appsecret:
        raise HTTPException(status_code=500, detail="WECHAT_APPID/WECHAT_APPSECRET is not configured")
    return config


def _raise_for_wechat_error(data: dict[str, Any], action: str) -> None:
    errcode = data.get("errcode")
    if errcode not in (None, 0):
        errmsg = data.get("errmsg") or "unknown error"
        raise WechatAPIError(f"{action} failed: {errcode} {errmsg}")


def get_access_token(settings: Settings | None = None, force_refresh: bool = False) -> str:
    config = ensure_wechat_config(settings)
    now = time.time()
    if not force_refresh and _token_cache.get("access_token") and now < float(_token_cache.get("expires_at") or 0):
        return str(_token_cache["access_token"])

    response = requests.get(
        f"{WECHAT_API_BASE}/cgi-bin/token",
        params={
            "grant_type": "client_credential",
            "appid": config.wechat_appid,
            "secret": config.wechat_appsecret,
        },
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    _raise_for_wechat_error(data, "get access_token")
    access_token = data.get("access_token")
    if not access_token:
        raise WechatAPIError("get access_token failed: access_token missing")
    expires_in = int(data.get("expires_in") or 7200)
    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + max(60, expires_in - TOKEN_SKEW_SECONDS)
    return str(access_token)


def _post_json(path: str, payload: dict[str, Any], action: str, settings: Settings | None = None) -> dict[str, Any]:
    config = ensure_wechat_config(settings)
    token = get_access_token(config)
    response = requests.post(
        f"{WECHAT_API_BASE}{path}",
        params={"access_token": token},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errcode") in (40001, 42001):
        token = get_access_token(config, force_refresh=True)
        response = requests.post(
            f"{WECHAT_API_BASE}{path}",
            params={"access_token": token},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    _raise_for_wechat_error(data, action)
    return data


def _image_file_tuple(image: ImagePayload) -> tuple[str, bytes, str]:
    return image.filename, base64.b64decode(image.content_base64), image.content_type


def _upload_file(
    path: str,
    image: ImagePayload,
    params: dict[str, Any],
    action: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    config = ensure_wechat_config(settings)
    token = get_access_token(config)
    query = {"access_token": token, **params}
    response = requests.post(
        f"{WECHAT_API_BASE}{path}",
        params=query,
        files={"media": _image_file_tuple(image)},
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errcode") in (40001, 42001):
        token = get_access_token(config, force_refresh=True)
        query["access_token"] = token
        response = requests.post(
            f"{WECHAT_API_BASE}{path}",
            params=query,
            files={"media": _image_file_tuple(image)},
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    _raise_for_wechat_error(data, action)
    return data


def upload_cover_material(image: ImagePayload, settings: Settings | None = None) -> str:
    data = _upload_file(
        "/cgi-bin/material/add_material",
        image=image,
        params={"type": "thumb"},
        action="upload thumb material",
        settings=settings,
    )
    media_id = data.get("media_id")
    if not media_id:
        raise WechatAPIError("upload thumb material failed: media_id missing")
    return str(media_id)


def upload_content_image(image: ImagePayload, settings: Settings | None = None) -> str:
    data = _upload_file(
        "/cgi-bin/media/uploadimg",
        image=image,
        params={},
        action="upload content image",
        settings=settings,
    )
    url = data.get("url")
    if not url:
        raise WechatAPIError("upload content image failed: url missing")
    return str(url)


def add_draft(request: DraftArticleRequest, settings: Settings | None = None) -> dict[str, Any]:
    config = ensure_wechat_config(settings)
    content_html = request.content_html
    uploaded_count = 0
    for image in request.images:
        if not image.placeholder:
            continue
        url = upload_content_image(image, config)
        content_html = content_html.replace(image.placeholder, url)
        uploaded_count += 1

    thumb_media_id = upload_cover_material(request.cover_image, config)
    author = (request.author or config.default_author or "").strip()
    article: dict[str, Any] = {
        "title": request.title[:64],
        "author": author[:8],
        "digest": request.digest[:120],
        "content": content_html,
        "content_source_url": request.content_source_url,
        "thumb_media_id": thumb_media_id,
        "need_open_comment": request.need_open_comment,
        "only_fans_can_comment": request.only_fans_can_comment,
    }
    article = {key: value for key, value in article.items() if value not in ("", None)}
    data = _post_json("/cgi-bin/draft/add", {"articles": [article]}, "add draft", config)
    return {
        "media_id": data.get("media_id"),
        "thumb_media_id": thumb_media_id,
        "uploaded_image_count": uploaded_count,
        "wechat_response": data,
    }

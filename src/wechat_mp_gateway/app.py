from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .runtime_log import append_log, read_logs
from .schemas import DraftArticleRequest, DraftArticleResponse
from .wechat_client import WechatAPIError, add_draft, get_access_token

app = FastAPI(
    title="WeChat MP Gateway",
    description="独立微信公众号 API 转发网关。当前支持把文章转发到微信公众号草稿箱，后续可扩展素材、发布、商品卡片等能力。",
    version="0.1.0",
)


def require_gateway_auth(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.gateway_token:
        raise HTTPException(status_code=500, detail="GATEWAY_TOKEN is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.gateway_token:
        raise HTTPException(status_code=403, detail="invalid bearer token")


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "ok": True,
        "service": "wechat-mp-gateway",
        "wechat_appid_configured": bool(settings.wechat_appid),
        "wechat_appsecret_configured": bool(settings.wechat_appsecret),
        "gateway_token_configured": bool(settings.gateway_token),
    }


@app.get("/api/logs", dependencies=[Depends(require_gateway_auth)])
def logs(limit: int = Query(default=80, ge=1, le=500)) -> JSONResponse:
    return JSONResponse({"logs": read_logs(limit=limit)}, media_type="application/json; charset=utf-8")


@app.post("/api/wechat/token/check", dependencies=[Depends(require_gateway_auth)])
def check_token() -> JSONResponse:
    try:
        get_access_token()
    except Exception as exc:
        append_log("error", "access_token check failed", {"error": str(exc)})
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    append_log("success", "access_token check success")
    return JSONResponse({"ok": True}, media_type="application/json; charset=utf-8")


@app.post("/api/wechat/drafts", response_model=DraftArticleResponse, dependencies=[Depends(require_gateway_auth)])
def create_draft(payload: DraftArticleRequest) -> DraftArticleResponse:
    append_log("info", "create draft start", {"title": payload.title, "image_count": len(payload.images)})
    try:
        result = add_draft(payload)
    except WechatAPIError as exc:
        append_log("error", "create draft failed", {"title": payload.title, "error": str(exc)})
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        append_log("error", "create draft unexpected failed", {"title": payload.title, "error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    append_log(
        "success",
        "create draft success",
        {
            "title": payload.title,
            "media_id": result.get("media_id"),
            "uploaded_image_count": result.get("uploaded_image_count"),
        },
    )
    return DraftArticleResponse(ok=True, **result)

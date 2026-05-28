from __future__ import annotations

import base64
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ImagePayload(BaseModel):
    filename: str = Field(default="image.png", max_length=160)
    content_type: str = Field(default="image/png", max_length=80)
    content_base64: str = Field(min_length=1)
    placeholder: str | None = Field(default=None, max_length=300)

    @field_validator("content_base64")
    @classmethod
    def validate_base64(cls, value: str) -> str:
        try:
            base64.b64decode(value, validate=True)
        except Exception as exc:
            raise ValueError(f"invalid base64: {exc}") from exc
        return value


class DraftArticleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content_html: str = Field(min_length=1)
    digest: str = Field(default="", max_length=120)
    author: str = Field(default="", max_length=32)
    content_source_url: str = Field(default="", max_length=300)
    cover_image: ImagePayload
    images: list[ImagePayload] = Field(default_factory=list)
    need_open_comment: int = Field(default=0, ge=0, le=1)
    only_fans_can_comment: int = Field(default=0, ge=0, le=1)


class DraftArticleResponse(BaseModel):
    ok: bool
    media_id: str | None = None
    thumb_media_id: str | None = None
    uploaded_image_count: int = 0
    wechat_response: dict[str, Any] = Field(default_factory=dict)

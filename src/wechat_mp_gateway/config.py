from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    gateway_token: str
    wechat_appid: str
    wechat_appsecret: str
    default_author: str = ""
    timeout_seconds: int = 60
    runtime_dir: str = "runtime"

    @property
    def runtime_path(self) -> Path:
        return Path(self.runtime_dir)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def get_settings() -> Settings:
    timeout_raw = _env("WECHAT_TIMEOUT_SECONDS", "60")
    try:
        timeout_seconds = max(5, int(timeout_raw))
    except ValueError:
        timeout_seconds = 60
    return Settings(
        gateway_token=_env("GATEWAY_TOKEN"),
        wechat_appid=_env("WECHAT_APPID"),
        wechat_appsecret=_env("WECHAT_APPSECRET"),
        default_author=_env("WECHAT_DEFAULT_AUTHOR"),
        timeout_seconds=timeout_seconds,
        runtime_dir=_env("RUNTIME_DIR", "runtime"),
    )

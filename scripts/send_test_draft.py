from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

import requests


def image_payload(path: Path, placeholder: str | None = None) -> dict:
    return {
        "placeholder": placeholder,
        "filename": path.name,
        "content_type": "image/png" if path.suffix.lower() == ".png" else "image/jpeg",
        "content_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a simple draft payload to WeChat MP Gateway")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--title", default="网关测试草稿")
    parser.add_argument("--cover", required=True, type=Path)
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()

    placeholder = "gateway://image/01"
    content_html = f"<h1>{args.title}</h1><p>这是一篇来自 WeChat MP Gateway 的测试草稿。</p>"
    images = []
    if args.image:
        content_html += f'<p><img src="{placeholder}" /></p>'
        images.append(image_payload(args.image, placeholder=placeholder))

    payload = {
        "title": args.title,
        "digest": "网关测试草稿",
        "content_html": content_html,
        "cover_image": image_payload(args.cover),
        "images": images,
    }
    response = requests.post(
        f"{args.base_url.rstrip('/')}/api/wechat/drafts",
        json=payload,
        headers={"Authorization": f"Bearer {args.token}"},
        timeout=180,
    )
    print(response.status_code)
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(response.text)
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

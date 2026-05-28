# WeChat MP Gateway

独立微信公众号 API 转发网关。当前目标是把外部系统生成的文章、封面和正文图片转发到微信公众号草稿箱；后续可继续扩展素材管理、发布、商品卡片、发布状态查询等能力。

## 当前能力

- 网关 Bearer Token 鉴权。
- 获取并缓存微信公众号 `access_token`。
- 上传正文图片到微信，拿微信返回图片 URL。
- 上传封面图为永久缩略图素材，拿 `thumb_media_id`。
- 调用微信公众号 `draft/add` 新增草稿。
- 草稿 JSON 使用 UTF-8 原文发送，避免中文在公众号后台显示成 `\uXXXX`。
- 运行日志 JSONL 记录。
- Docker / docker compose 部署。
- Docker healthcheck 与 `./runtime` 日志目录持久化。

## 适用前提

公众号后台需要具备草稿管理相关接口权限，例如：

- 草稿箱开关设置
- 新增草稿
- 更新草稿
- 获取草稿列表 / 详情

服务器公网 IP 需要加入微信公众号后台 IP 白名单。

## 本地启动

```powershell
cd C:\ai_work\wechat_mp_gateway
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
$env:PYTHONPATH=(Resolve-Path .\src).Path
$env:GATEWAY_TOKEN="your-local-token"
$env:WECHAT_APPID="你的AppID"
$env:WECHAT_APPSECRET="你的AppSecret"
python -m uvicorn wechat_mp_gateway.app:app --host 127.0.0.1 --port 8080
```

健康检查：

```bash
curl http://127.0.0.1:8080/health
```

## Docker 部署

```bash
cp .env.example .env
# 编辑 .env，填入 GATEWAY_TOKEN、WECHAT_APPID、WECHAT_APPSECRET
docker compose up -d --build
```

建议百度服务器前面加 Nginx + HTTPS，反代到本服务 `127.0.0.1:8080`。

## API

### 创建微信公众号草稿

```http
POST /api/wechat/drafts
Authorization: Bearer <GATEWAY_TOKEN>
Content-Type: application/json; charset=utf-8
```

请求示例：

```json
{
  "title": "文章标题",
  "author": "作者",
  "digest": "摘要，最多 120 字",
  "content_html": "<h1>标题</h1><p>正文</p><img src=\"hotrank://image/01\">",
  "cover_image": {
    "filename": "cover.png",
    "content_type": "image/png",
    "content_base64": "..."
  },
  "images": [
    {
      "placeholder": "hotrank://image/01",
      "filename": "img_01.png",
      "content_type": "image/png",
      "content_base64": "..."
    }
  ]
}
```

返回示例：

```json
{
  "ok": true,
  "media_id": "草稿media_id",
  "thumb_media_id": "封面素材media_id",
  "uploaded_image_count": 1,
  "wechat_response": {}
}
```

### 检查 access_token

```http
POST /api/wechat/token/check
Authorization: Bearer <GATEWAY_TOKEN>
```

返回只表示检查是否成功，不回显微信 `access_token`。

### 查看日志

```http
GET /api/logs?limit=80
Authorization: Bearer <GATEWAY_TOKEN>
```

## 安全建议

- 不要提交 `.env`。
- `GATEWAY_TOKEN` 使用 32 位以上随机字符串。
- `WECHAT_APPSECRET` 只放服务器。
- 服务器防火墙只开放必要端口。
- 生产环境强烈建议通过 HTTPS 暴露。

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TIMEOUT=120 \
    PIP_RETRIES=5 \
    PYTHONPATH=/app/src

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY src /app/src
COPY scripts /app/scripts

EXPOSE 8080
CMD ["uvicorn", "wechat_mp_gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]
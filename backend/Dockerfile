FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# asyncpg / argon2 휠은 미리 빌드돼 있지만, 혹시 몰라 curl과 빌드 도구를 둔다.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# 컨테이너 수준의 생존 점검. 앱 수준 /api/ready는 DB까지 확인한다.
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

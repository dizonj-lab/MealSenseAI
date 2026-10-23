# ---- web: build the React frontend
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- runtime: FastAPI API + built frontend + vision models (CPU)
FROM ubuntu:24.04 AS runtime
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3.12 python3.12-venv \
        libegl1 libgles2 libgl1 libglib2.0-0t64 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* && python3.12 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY datasets/nutrition/ datasets/nutrition/
COPY ml/models/ ml/models/
COPY --from=web /web/dist frontend/dist
RUN test -f ml/models/efficientnet_lite0.tflite || ./ml/models/fetch_models.sh
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 CMD curl -fs localhost:8000/api/v1/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

# ---- test: runtime + test fixtures (pytest is already in requirements)
FROM runtime AS test
CMD ["python", "-m", "pytest", "-q", "-W", "ignore", "tests"]

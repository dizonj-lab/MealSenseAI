# MealSenseAI backend: FastAPI + EXP-002 food classifier (ONNX Runtime) + migrations.
# Build context: repository root.   CPU (default):  --target cpu    GPU (optional):  --target gpu
# All model files are copied into the image; nothing is downloaded at runtime.

# ---------- CPU (default)
FROM python:3.12-slim AS cpu
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DATA_DIR=/data INFERENCE_DEVICE=auto
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ backend/
COPY datasets/nutrition/foods.json datasets/nutrition/foods.json
COPY ml/models/exp002/ ml/models/exp002/
COPY ml/models/yolo11n-seg.onnx ml/models/yolo11n-seg.onnx
RUN python -c "import json,pathlib;c=json.loads(pathlib.Path('ml/models/exp002/model_card.json').read_text());assert c['num_classes']==320" \
    && useradd --uid 10001 --create-home app && mkdir -p /data && chown app /data
USER app
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=4).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

# ---------- test image (CPU + pytest)
FROM cpu AS test
USER root
COPY requirements-dev.txt /app/
RUN pip install -r /app/requirements-dev.txt
USER app
CMD ["python", "-m", "pytest", "-q", "-W", "ignore", "tests"]

# ---------- GPU (optional): CUDA 12 + cuDNN 9 runtime, onnxruntime-gpu picks CUDA automatically
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04 AS gpu
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DATA_DIR=/data INFERENCE_DEVICE=auto
RUN apt-get update && apt-get install -y --no-install-recommends python3.12 python3.12-venv \
    && rm -rf /var/lib/apt/lists/* && python3.12 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY requirements.txt .
RUN sed 's/^onnxruntime$/onnxruntime-gpu/' requirements.txt > requirements-gpu.txt && pip install -r requirements-gpu.txt
COPY backend/ backend/
COPY datasets/nutrition/foods.json datasets/nutrition/foods.json
COPY ml/models/exp002/ ml/models/exp002/
COPY ml/models/yolo11n-seg.onnx ml/models/yolo11n-seg.onnx
RUN useradd --uid 10001 --create-home app && mkdir -p /data && chown app /data
USER app
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=4).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

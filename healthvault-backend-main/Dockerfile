# Production Dockerfile for HealthVault AI Backend on Google Cloud Run
FROM python:3.11-slim

# Set environment variables for Python, pip optimization, and Cloud Run
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    ENVIRONMENT=production \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install minimal system runtime dependencies required for OpenCV, EasyOCR, and PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip once
RUN pip install --no-cache-dir --upgrade pip

# Layer 1: Install CPU-only PyTorch and torchvision directly from official PyTorch CPU wheel repo.
# This prevents downloading >5GB of NVIDIA CUDA 12 / cuDNN GPU libraries.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Layer 2: Install remaining application requirements (PyTorch/torchvision are already satisfied)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Layer 3: Copy backend application and runtime AI pipeline
COPY backend ./backend
COPY ai_pipeline ./ai_pipeline

# Cloud Run defaults to listening on port 8080 or the PORT environment variable
EXPOSE 8080

# Production startup command using uvicorn binding to 0.0.0.0 and dynamic $PORT
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]

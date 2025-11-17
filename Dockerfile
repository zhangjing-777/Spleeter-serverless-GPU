FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

# ---------------------------
# Install system dependencies
# ---------------------------
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------
# Install Python Dependencies
# ---------------------------
RUN pip install --upgrade pip && \
    pip install runpod && \
    pip install spleeter==2.4.0 && \
    pip install tensorflow==2.5.0

# ---------------------------
# Pre-download models (重要：避免运行时下载)
# ---------------------------
RUN python3 -c "from spleeter.separator import Separator; Separator('spleeter:2stems')" || true
RUN python3 -c "from spleeter.separator import Separator; Separator('spleeter:4stems')" || true
RUN python3 -c "from spleeter.separator import Separator; Separator('spleeter:5stems')" || true

# ---------------------------
# Set working directory
# ---------------------------
WORKDIR /app

# ---------------------------
# Copy source code
# ---------------------------
COPY src/ ./src/

# ---------------------------
# Serverless entrypoint
# ---------------------------
CMD ["python3", "-u", "src/handler.py"]

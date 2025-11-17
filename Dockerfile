FROM python:3.8-slim

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
    pip install runpod \
    spleeter==2.4.0 \
    pydub

# ---------------------------
# Pre-download Spleeter models (避免运行时下载)
# ---------------------------
RUN python3 -c "from spleeter.separator import Separator; Separator('spleeter:2stems', multiprocess=False)" && \
    python3 -c "from spleeter.separator import Separator; Separator('spleeter:4stems', multiprocess=False)" && \
    python3 -c "from spleeter.separator import Separator; Separator('spleeter:5stems', multiprocess=False)"

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

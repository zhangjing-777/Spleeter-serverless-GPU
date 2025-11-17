FROM python:3.9-slim

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
# Pre-download models
# ---------------------------
ENV MODEL_PATH=/models
RUN mkdir -p $MODEL_PATH && \
    python3 -c "from spleeter.separator import Separator; Separator('spleeter:2stems', multiprocess=False)" && \
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

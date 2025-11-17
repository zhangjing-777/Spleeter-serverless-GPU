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
    pip install runpod spleeter

# ---------------------------
# Pre-download models
# ---------------------------
RUN python3 -c "from spleeter.separator import Separator; Separator('spleeter:2stems')"
RUN python3 -c "from spleeter.separator import Separator; Separator('spleeter:4stems')"
RUN python3 -c "from spleeter.separator import Separator; Separator('spleeter:5stems')"

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

# ── Hugging Face Spaces — FastAPI Backend ─────────────────────
# HF Spaces uses port 7860 by default
FROM python:3.11-slim

WORKDIR /code

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY internhunter/ ./internhunter/
COPY app/          ./app/

# Create data directories
RUN mkdir -p data/digest logs assets

# HF Spaces runs as non-root — ensure writable
RUN chmod -R 777 data logs

# Expose HF Spaces default port
EXPOSE 7860

# Start FastAPI on HF port
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
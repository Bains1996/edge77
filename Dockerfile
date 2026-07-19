FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r edge77 && useradd -r -g edge77 -d /app -s /sbin/nologin edge77

# Copy requirements first (for Docker cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set ownership
RUN chown -R edge77:edge77 /app

# Switch to non-root user
USER edge77

# Expose port
EXPOSE 8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run with uvicorn
CMD exec uvicorn v1_ingestion.main_gateway:app --host 0.0.0.0 --port 8080 --timeout-keep-alive 300

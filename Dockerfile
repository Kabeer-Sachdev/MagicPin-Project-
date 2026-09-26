# Use slim official Python base image
FROM python:3.11-slim

# Prevent Python from writing .pyc files to disk and buffer output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

# Set working directory
WORKDIR /app

# Install system dependencies if any needed (clean up after)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies first for efficient layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/

# Expose port
EXPOSE 8080

# Health check using curl
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/v1/healthz || exit 1

# Start Uvicorn with single worker to preserve state consistency
CMD exec uvicorn app.main:app --host ${HOST} --port ${PORT} --workers 1

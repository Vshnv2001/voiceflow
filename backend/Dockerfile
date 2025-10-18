# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libasound2-dev \
    portaudio19-dev \
    python3-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
# Use environment variables for host and port, with defaults
CMD ["sh", "-c", "if [ \"$DEBUG\" = \"True\" ]; then uvicorn main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers 1 --reload; else uvicorn main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers 1; fi"]

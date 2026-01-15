# Redis FastAPI KV Store
FROM python:3.12-slim

# Build arguments
ARG USER_ID=1000
ARG GROUP_ID=1000
ARG APP_USER=fastapi
ARG APP_HOME=/app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC \
    APP_PORT=7776 \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR ${APP_HOME}

# Copy requirements.txt first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create user
RUN groupadd -g ${GROUP_ID} ${APP_USER} && \
    useradd -u ${USER_ID} -g ${APP_USER} -m -s /bin/bash ${APP_USER}

# Copy application code
COPY --chown=${USER_ID}:${GROUP_ID} app/ .

# Create necessary directories
RUN mkdir -p /logs && \
    chown -R ${USER_ID}:${GROUP_ID} /logs

# Switch to non-root user
USER ${USER_ID}

# Expose port
EXPOSE ${APP_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT}/health || exit 1

# Labels
LABEL maintainer="your-name" \
      description="FastAPI Redis KV Store Service" \
      version="1.0.0"

# Entrypoint
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7776"]
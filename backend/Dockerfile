# Stage 1: Builder
FROM python:3.14-slim@sha256:9b81fe9acff79e61affb44aaf3b6ff234392e8ca477cb86c9f7fd11732ce9b6a AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files and README (needed by pyproject.toml)
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -e .

# Stage 2: Production
FROM python:3.14-slim@sha256:9b81fe9acff79e61affb44aaf3b6ff234392e8ca477cb86c9f7fd11732ce9b6a AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# SECURITY: Remove unnecessary binaries from base image that carry CVEs
# - gosu: Go binary for privilege dropping (17 CVEs from Go stdlib)
#   We use the USER instruction instead, gosu is never invoked
# - pip/setuptools: Not needed at runtime (UV installs in builder stage)
#   Eliminates pip path traversal CVE
RUN rm -f /usr/local/bin/gosu /usr/local/sbin/gosu && \
    pip uninstall -y pip setuptools 2>/dev/null || true && \
    rm -rf /usr/lib/python3*/ensurepip

# Create non-root user with explicit UID/GID
RUN groupadd -r -g 1000 kidney-api && \
    useradd -r -u 1000 -g kidney-api -m -s /bin/bash kidney-api

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Remove pip/setuptools from the virtual environment copied from builder
RUN rm -rf /opt/venv/lib/python3*/site-packages/pip* \
           /opt/venv/lib/python3*/site-packages/setuptools* \
           /opt/venv/bin/pip*

# Copy application code
COPY --chown=kidney-api:kidney-api . .

# Switch to non-root user
USER kidney-api

# Health check using Python instead of curl (no curl in production image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]

EXPOSE 8000

# Uvicorn command (port 8000 requires NO special capabilities)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

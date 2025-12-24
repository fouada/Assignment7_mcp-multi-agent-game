# MCP Multi-Agent Game System
# Production-grade Docker image with UV

# ============================================================================
# Base stage with UV
# ============================================================================
FROM python:3.14-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

# Create app user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set work directory
WORKDIR /app

# Install system dependencies and UV
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add UV to PATH
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files for dependency installation
COPY pyproject.toml .
COPY README.md .

# Install dependencies with UV (production only)
RUN uv pip install --system -e .

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default command
CMD ["python", "-m", "src.main"]

# ============================================================================
# Development stage
# ============================================================================
FROM base as development

USER root

# Install dev dependencies with UV
RUN uv pip install --system -e ".[dev,llm]"

# Copy tests
COPY tests/ ./tests/

USER appuser

CMD ["python", "-m", "pytest", "tests/", "-v"]

# ============================================================================
# Production stage
# ============================================================================
FROM base as production

# No additional changes needed for production
CMD ["python", "-m", "src.main", "--run"]


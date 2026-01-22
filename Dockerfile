# CHUK MCP Solver Dockerfile
# ========================================
# Multi-stage build for optimal image size
# Based on chuk-mcp-server patterns

# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management (fixed path)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    echo "uv installed to /root/.local/bin"
ENV PATH="/root/.local/bin:${PATH}"

# Copy project configuration
COPY pyproject.toml README.md ./
COPY src ./src

# Install the package with all dependencies using full path (force fresh install with 0.16.4)
RUN /root/.local/bin/uv pip install --system --no-cache -e .

# Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/src ./src
COPY --from=builder /app/README.md ./
COPY --from=builder /app/pyproject.toml ./

# Create non-root user for security
RUN useradd -m -u 1000 mcpuser && \
    chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); import chuk_mcp_solver; print('OK')" || exit 1

# Default command - run MCP server in HTTP mode for Docker
CMD ["python", "-m", "chuk_mcp_solver.server", "http"]

# Expose port for HTTP mode
EXPOSE 8000

# Labels for metadata
LABEL maintainer="info@chuk.ai" \
      description="CHUK MCP Solver - General-purpose constraint and optimization solver" \
      version="0.5.0" \
      org.opencontainers.image.source="https://github.com/chuk-ai/chuk-mcp-solver" \
      org.opencontainers.image.title="CHUK MCP Solver" \
      org.opencontainers.image.description="MCP server for constraint satisfaction and optimization using OR-Tools" \
      org.opencontainers.image.authors="CHUK AI <info@chuk.ai>"

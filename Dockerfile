FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose port for Streamable HTTP
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check (usa $PORT que EasyPanel configura)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; import httpx; httpx.get(f'http://localhost:{os.getenv(\"PORT\", 8000)}/health', timeout=5)" || exit 1

# Run the server
CMD ["mcp-reportes"]

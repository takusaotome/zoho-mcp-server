FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/
COPY docs/ ./docs/

# Create non-root user
RUN useradd --create-home --shell /bin/bash zoho
RUN chown -R zoho:zoho /app
USER zoho

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Run application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
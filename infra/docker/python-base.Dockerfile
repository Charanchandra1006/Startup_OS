FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared types first (dependency for all Python services)
COPY packages/shared-types/python /app/packages/shared-types/python

# Install shared types
RUN pip install --no-cache-dir -e /app/packages/shared-types/python

# Default command (overridden per service)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

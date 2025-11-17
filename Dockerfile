# Multi-stage Dockerfile for Cross-Chain Price Checker

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-full.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements-full.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY cross_chain_price_checker ./cross_chain_price_checker
COPY setup.py .
COPY README.md .
COPY requirements-full.txt .

# Install the package
RUN pip install --no-cache-dir -e .

# Make PATH include local bin
ENV PATH=/root/.local/bin:$PATH

# Expose ports
EXPOSE 8000 9090

# Default command (can be overridden)
CMD ["uvicorn", "cross_chain_price_checker.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

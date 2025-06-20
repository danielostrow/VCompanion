# Use Python 3.11 alpine base image
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Create virtual environment
RUN python -m venv /opt/venv

# Make sure to use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Install system dependencies (Alpine Linux packages)
RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    && rm -rf /var/cache/apk/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies in virtual environment
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Create necessary directories
RUN mkdir -p memory
RUN mkdir -p static/avatars

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /opt/venv

# Switch to non-root user
USER appuser

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 
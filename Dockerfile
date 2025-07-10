FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies and system packages
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the entire project
COPY . .

# Verify the file structure
RUN ls -la /app && ls -la /app/app && test -f /app/app/main.py

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "-m", "app.main"]

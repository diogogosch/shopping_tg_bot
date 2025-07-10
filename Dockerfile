FROM python:3.11-slim

# Set working directory to root
WORKDIR /

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies and system packages
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy all application files
COPY . .

# Verify the main file exists
RUN test -f /app/main.py

# Set Python path to include the current directory
ENV PYTHONPATH=/

# Run the application from root directory
CMD ["python", "app/main.py"]

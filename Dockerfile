FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . .

# fail early if the file is missing
RUN test -f /app/main.py

CMD ["python", "/app/main.py"]

WORKDIR /app
CMD ["python", "main.py"]   # if /app/main.py exists

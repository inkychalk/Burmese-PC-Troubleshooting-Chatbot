FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Copy the seed data
COPY troubleshooting_data.json /app/database/troubleshooting_data.json

# Create data directory for SQLite persistence
RUN mkdir -p /data

EXPOSE 5000

ENV DATABASE_PATH=/data/db.sqlite
ENV FLASK_ENV=production
ENV PORT=5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--preload", "app:app"]

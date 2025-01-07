FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    lilypond \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Create temp directory with proper permissions
RUN mkdir -p /app/temp && chmod 777 /app/temp

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Run the application
CMD uvicorn app:app --host 0.0.0.0 --port $PORT 
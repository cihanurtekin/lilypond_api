FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    lilypond \
    imagemagick \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick to allow PDF conversion
RUN mkdir -p /etc/ImageMagick-6 && \
    echo '<policy domain="coder" rights="read | write" pattern="PDF" />' > /etc/ImageMagick-6/policy.xml

# Create temp directory with proper permissions
RUN mkdir -p /app/temp && \
    chmod 777 /app/temp && \
    chown -R nobody:nogroup /app/temp

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Ensure temp directory permissions after copy
RUN chmod 777 /app/temp && \
    chown -R nobody:nogroup /app/temp && \
    chmod -R 777 /etc/ImageMagick-6

# Run the application
CMD uvicorn app:app --host 0.0.0.0 --port $PORT 
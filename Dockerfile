FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs

# Set file permissions for database directory
RUN chmod 700 /app/data

# Run as non-root user for security
RUN useradd -m -u 1000 jambot && chown -R jambot:jambot /app
USER jambot

# Set environment variable defaults
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "-m", "src.main"]

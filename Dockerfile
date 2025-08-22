# Dockerfile for SC Referral Bot
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY server_requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r server_requirements.txt

# Copy project files
COPY . .

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=5000
ENV DATABASE_PATH=/app/data/bot.db

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the bot
CMD ["python", "start_server.py"]
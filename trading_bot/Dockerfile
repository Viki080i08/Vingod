# Trading AI Telegram bot - production image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY trading_bot/requirements.txt /app/trading_bot/requirements.txt
RUN pip install --no-cache-dir -r /app/trading_bot/requirements.txt

# Copy the application package.
COPY trading_bot /app/trading_bot

# Persist the SQLite database outside the image.
ENV DATABASE_PATH=/data/trading_bot.db
VOLUME ["/data"]

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data && chown -R appuser:appuser /data /app
USER appuser

CMD ["python", "-m", "trading_bot.main"]

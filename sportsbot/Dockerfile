FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for psycopg2 runtime are bundled in psycopg2-binary, so we only
# need build essentials if compiling; the binary wheel avoids that.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run both the Telegram bot and the admin dashboard.
EXPOSE 8080
CMD ["python", "-m", "sportsbot", "all"]

# Small, production-ready image for Google Cloud Run (or any container host).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run injects PORT (usually 8080). Default to 8080 for local runs.
ENV PORT=8080
EXPOSE 8080

# 1 worker with threads is plenty — the bot is I/O bound (it just calls
# the Graph API) and Cloud Run scales by adding instances, not workers.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 30 app:app

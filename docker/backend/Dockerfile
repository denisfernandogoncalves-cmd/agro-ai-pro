FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements /tmp/requirements
RUN pip install --no-cache-dir -r /tmp/requirements/dev.txt

COPY backend /app/backend
COPY .env.example /app/.env.example

EXPOSE 8000

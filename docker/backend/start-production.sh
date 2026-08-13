#!/bin/sh
set -eu

attempt=1
max_attempts="${MIGRATION_MAX_ATTEMPTS:-12}"

until python manage.py migrate --noinput; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Falha ao aplicar migrations após ${max_attempts} tentativas." >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  echo "Banco indisponível; nova tentativa de migration em 5 segundos (${attempt}/${max_attempts})." >&2
  sleep 5
done

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --create-home --uid 10001 appuser
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "python scripts/cloud_bootstrap.py && exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 60 --access-logfile - wsgi:app"]

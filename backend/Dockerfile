FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/ /app/

RUN groupadd --system --gid 10001 hometogether \
    && useradd --system --uid 10001 --gid hometogether --home-dir /app hometogether \
    && mkdir -p /app/staticfiles /private_uploads \
    && chown -R hometogether:hometogether /app /private_uploads
USER hometogether

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]

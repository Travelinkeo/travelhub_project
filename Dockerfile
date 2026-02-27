FROM python:3.13-slim

# Instalar dependencias del sistema para WeasyPrint y Postgres
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    libglib2.0-0 \
    shared-mime-info \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requerimientos e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Copiar y preparar entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# El comando por defecto se sobreescribirá en docker-compose.yml
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["gunicorn", "travelhub.wsgi:application", "--bind", "0.0.0.0:8000"]

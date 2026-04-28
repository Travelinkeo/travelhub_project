# Usamos una imagen oficial de Python ligera pero completa (Python 3.12 / Bookworm)
FROM python:3.12-slim-bookworm

# Prevenir que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE 1
# Prevenir que Python haga buffering en la salida estándar (para ver los logs en tiempo real)
ENV PYTHONUNBUFFERED 1

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del Sistema Operativo necesarias para WeasyPrint (PDFs), PostgreSQL y Celery
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2-dev \
    libffi-dev \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    pkg-config \
    python3-dev \
    libldap2-dev \
    libsasl2-dev \
    netcat-openbsd \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de dependencias de Python y las instalamos
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Instalar Gunicorn (el servidor web para producción en Python)
RUN pip install gunicorn

# Copiar todo el código fuente del proyecto al contenedor
COPY . /app/

# Dar permisos de ejecución al script de entrada y convertir CRLF a LF (Prevención de Error \r en Windows)
RUN chmod +x /app/entrypoint.sh && sed -i 's/\r$//' /app/entrypoint.sh
# Exponer el puerto interno 8000
EXPOSE 8000

# Punto de entrada por defecto
ENTRYPOINT ["/app/entrypoint.sh"]

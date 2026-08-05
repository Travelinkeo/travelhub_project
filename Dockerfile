# syntax=docker/dockerfile:1
# Stage 1: builder — compile assets and install Python deps
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev gcc libpango-1.0-0 libpangocairo-1.0-0 \
    libffi-dev shared-mime-info curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 -r requirements/prod.txt --prefix=/install
RUN pip install --no-cache-dir "setuptools<70" --prefix=/install

COPY travelhub/ ./travelhub/
COPY core/ ./core/
COPY apps/ ./apps/
COPY manage.py ./
COPY static/ ./static/
COPY templates/ ./templates/
COPY locale/ ./locale/
COPY compose/ ./compose/
COPY docs/ ./docs/
COPY tests/ ./tests/
COPY fixtures/ ./fixtures/
COPY tailwind.config.js ./

COPY compilar.sh ./compilar.sh

RUN chmod +x ./compilar.sh && sed -i 's/\r$//' ./compilar.sh && bash ./compilar.sh || true

RUN PYTHONPATH=/install/lib/python3.12/site-packages \
    DJANGO_SETTINGS_MODULE=travelhub.settings \
    SECRET_KEY=build-placeholder-key-not-used-in-production-1234567890 \
    DATABASE_URL=sqlite:///tmp/build.db \
    DEBUG=False \
    python manage.py collectstatic --noinput || true

RUN mkdir -p /build/staticfiles

# Stage 2: runtime — minimal image
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev libpango-1.0-0 libpangocairo-1.0-0 shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --from=builder /build/travelhub ./travelhub/
COPY --from=builder /build/core ./core/
COPY --from=builder /build/apps ./apps/
COPY --from=builder /build/manage.py ./
COPY --from=builder /build/static ./static/
COPY --from=builder /build/staticfiles ./staticfiles/
COPY --from=builder /build/templates ./templates/
COPY --from=builder /build/locale ./locale/
COPY --from=builder /build/compose ./compose/
COPY --from=builder /build/docs ./docs/
COPY --from=builder /build/tests ./tests/
COPY --from=builder /build/fixtures ./fixtures/
RUN pip install --no-cache-dir "setuptools<70"
COPY entrypoint.sh ./entrypoint.sh

RUN chmod +x ./entrypoint.sh && sed -i 's/\r$//' ./entrypoint.sh && groupadd -r appgroup && useradd -r -g appgroup appuser && chown -R appuser:appgroup /app

EXPOSE 8000

# Entrypoint runs as root to fix permissions, then drops to appuser
# USER appuser  # removed — applied via su in entrypoint.sh
ENV APP_USER=appuser

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "travelhub.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

# Stage 3: test — runtime + test dependencies
FROM python:3.12-slim AS test

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev libpango-1.0-0 libpangocairo-1.0-0 shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --from=builder /build/travelhub ./travelhub/
COPY --from=builder /build/core ./core/
COPY --from=builder /build/apps ./apps/
COPY --from=builder /build/manage.py ./
COPY --from=builder /build/static ./static/
COPY --from=builder /build/staticfiles ./staticfiles/
COPY --from=builder /build/templates ./templates/
COPY --from=builder /build/locale ./locale/
COPY --from=builder /build/docs ./docs/

RUN pip install --no-cache-dir coverage pytest pytest-django pytest-cov pytest-timeout psycopg2-binary

COPY conftest.py ./conftest.py
COPY pytest.ini ./pytest.ini
COPY tests/ ./tests/
COPY fixtures/ ./fixtures/
COPY docs/HARDENING_BASELINE.md ./docs/HARDENING_BASELINE.md

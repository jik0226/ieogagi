# Backend image: hash-pinned dependencies, non-root user, no dev tools or tests.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/backend

COPY requirements.lock requirements-build.lock ./
RUN pip install --require-hashes -r requirements.lock -r requirements-build.lock

COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN pip install --no-deps --no-build-isolation . \
    && useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin ieogagi

USER ieogagi
EXPOSE 8000

# Only the reverse proxy (fixed address on the internal network) may set X-Forwarded-For.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "172.28.0.10", \
     "--no-server-header", "--no-access-log"]

FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS frontend

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-alpine@sha256:25976e9d34a0fab1f278cae931f34c8303d97bf0c0d7f85b6b4dcf641d7702a4 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend/src \
    CAREERPILOT_DATA_DIR=/app/data \
    CAREERPILOT_FRONTEND_ORIGIN=http://127.0.0.1:9999 \
    CAREERPILOT_STATIC_DIR=/app/frontend-dist

WORKDIR /app
COPY backend/requirements/linux-runtime.lock ./backend/requirements/linux-runtime.lock
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: \
    --requirement ./backend/requirements/linux-runtime.lock
COPY backend/pyproject.toml backend/alembic.ini ./backend/
COPY backend/migrations/ ./backend/migrations/
COPY backend/src/ ./backend/src/
RUN python -m pip install --no-cache-dir --no-deps --no-build-isolation ./backend \
    && adduser -D -u 10001 careerpilot \
    && mkdir -p /app/data \
    && chown -R careerpilot:careerpilot /app
COPY --from=frontend --chown=careerpilot:careerpilot /build/frontend/dist/ ./frontend-dist/

USER careerpilot
EXPOSE 9998
VOLUME ["/app/data"]

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9998/api/v1/health', timeout=2).read()"]

CMD ["python", "-m", "uvicorn", "careerpilot.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "9998"]

FROM runtime AS test
USER root
COPY backend/requirements/linux-dev.lock ./backend/requirements/linux-dev.lock
RUN apk add --no-cache git
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: \
    --requirement ./backend/requirements/linux-dev.lock
USER careerpilot
WORKDIR /app/backend
CMD ["python", "-m", "pytest", "tests", "-q"]

FROM test AS security
USER root
COPY backend/requirements/linux-security.lock ./backend/requirements/linux-security.lock
RUN python -m pip install --no-cache-dir --require-hashes --only-binary=:all: \
    --requirement ./backend/requirements/linux-security.lock
USER careerpilot
CMD ["python", "-m", "pip_audit"]

FROM runtime AS final

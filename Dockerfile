# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd -r bridge && useradd -r -g bridge -d /app -s /sbin/nologin bridge

WORKDIR /app

COPY pyproject.toml bridge/__init__.py ./
COPY bridge/ ./bridge/
RUN pip install --no-cache-dir . \
    && mkdir -p /config && chown bridge:bridge /config

USER bridge

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', 8888)); s.close()" || exit 1

ENTRYPOINT ["python", "-m", "bridge"]
CMD ["--config", "/config/config.yaml"]

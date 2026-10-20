FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /opt/mirror
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && groupadd --gid 10001 vanta \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin vanta
USER 10001:10001

FROM runtime AS portal
COPY app/ ./app/
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).close()"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-tmp-dir", "/tmp", "--timeout", "15", "--access-logfile", "-", "--error-logfile", "-", "app.app:create_app()"]

FROM runtime AS catalog
COPY services/__init__.py services/catalog.py ./services/
EXPOSE 9080
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9080/healthz', timeout=3).close()"
CMD ["gunicorn", "--bind", "0.0.0.0:9080", "--workers", "1", "--worker-tmp-dir", "/tmp", "--timeout", "15", "--access-logfile", "-", "--error-logfile", "-", "services.catalog:create_app()"]

FROM runtime AS relay
COPY services/__init__.py services/relay.py ./services/
EXPOSE 9090
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9090/healthz', timeout=3).close()"
CMD ["gunicorn", "--bind", "0.0.0.0:9090", "--workers", "1", "--worker-tmp-dir", "/tmp", "--timeout", "15", "--access-logfile", "-", "--error-logfile", "-", "services.relay:create_app()"]

FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/phantom
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && groupadd --gid 10001 vanta \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin vanta

# create_app reads this file one directory above app/app.py at startup.
COPY challenge.yml ./
COPY app/ ./app/
USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).close()"

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--preload", "--worker-tmp-dir", "/tmp", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "app.app:create_app()"]

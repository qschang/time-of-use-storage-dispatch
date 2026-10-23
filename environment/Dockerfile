FROM python:3.13.15-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1
COPY wheels/ /opt/wheels/
COPY app/ /app/
RUN python3 -m pip install --no-cache-dir --no-index --find-links=/opt/wheels pytest==8.4.1
RUN mkdir -p /logs/verifier && chmod 0755 /app/storage_dispatch.py /logs/verifier
WORKDIR /app
CMD ["sleep", "infinity"]

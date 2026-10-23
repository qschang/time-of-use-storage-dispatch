#!/usr/bin/env bash
set -Eeuo pipefail
install -m 0755 /solution/reference.py /app/storage_dispatch.py
exec python3 /app/storage_dispatch.py "$@"

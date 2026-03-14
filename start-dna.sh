#!/bin/bash
# BetApp production startup
export PYTHONPATH=/data/.openclaw/workspace/DNA:/data/.openclaw/workspace/DNA/dna-matrix:$PYTHONPATH
cd /data/.openclaw/workspace/DNA
python3 -m alembic upgrade head
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

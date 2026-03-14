web: sh -c 'PYTHONPATH=.:./dna-matrix:$PYTHONPATH alembic upgrade head && PYTHONPATH=.:./dna-matrix:$PYTHONPATH uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'

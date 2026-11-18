#!/usr/bin/env bash
set -e
uvicorn backend.fastapi_app:app --host 127.0.0.1 --port 8080 &
sleep 2
streamlit run frontend/streamlit_app_3.py --server.port "${PORT:-8501}" --server.address 0.0.0.0

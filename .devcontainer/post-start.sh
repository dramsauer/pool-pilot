#!/bin/sh
set -e

# Start the Streamlit app in the background so the devcontainer user can
# preview it via http://localhost:8501 without blocking the terminal.
nohup streamlit run Wasserrechner.py \
  --server.headless=true \
  --server.port=8501 \
  > /tmp/streamlit.log 2>&1 &

sleep 2
echo '→ PoolPilot: http://localhost:8501'

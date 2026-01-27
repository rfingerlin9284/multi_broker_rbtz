#!/usr/bin/env bash
# RBOTzilla LLM Gate systemd service installer
set -euo pipefail

REPO="${REPO:-/home/ing/RICK/MULTI_BROKER_PHOENIX}"
GATEDIR="$REPO/llm_gate"
PORT="${LLM_GATE_PORT:-6060}"
VENV="$REPO/.venv"
SERVICE_NAME="rbotzilla-llm-gate"

echo "== RBOTzilla LLM Gate Service Installer =="
echo "Repo: $REPO"
echo "Port: $PORT"

# Ensure venv exists
if [[ ! -d "$VENV" ]]; then
    echo "ERROR: Virtual environment not found at $VENV"
    echo "Create it with: python3 -m venv $VENV"
    exit 1
fi

# Install FastAPI/uvicorn if not present
"$VENV/bin/pip" install --quiet fastapi uvicorn pydantic 2>/dev/null || true

# Create systemd unit
cat > /tmp/${SERVICE_NAME}.service <<SERVICE
[Unit]
Description=RBOTzilla LLM Gate (local brain HTTP service)
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$REPO
Environment=OLLAMA_URL=http://127.0.0.1:11434
Environment=OLLAMA_MODEL=llama3.1:8b
Environment=PYTHONPATH=$REPO
ExecStart=$VENV/bin/uvicorn llm_gate.gate_service:app --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
SERVICE

echo "== Installing systemd unit =="
sudo cp /tmp/${SERVICE_NAME}.service /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}.service

echo ""
echo "✅ Service installed: $SERVICE_NAME"
echo ""
echo "Commands:"
echo "  sudo systemctl start $SERVICE_NAME    # Start the service"
echo "  sudo systemctl status $SERVICE_NAME   # Check status"
echo "  sudo systemctl stop $SERVICE_NAME     # Stop the service"
echo "  curl http://127.0.0.1:$PORT/health    # Health check"
echo ""
echo "To start now: sudo systemctl start $SERVICE_NAME"

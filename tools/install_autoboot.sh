#!/usr/bin/env bash
# Installs the rbotzilla systemd unit and helper scripts.
# Idempotent: overwrites the unit and helper if present.
set -euo pipefail
PROJECT_ROOT="/home/ing/RICK/MULTI_BROKER_PHOENIX"
SERVICE_NAME="rbotzilla"
UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
EXEC_WRAPPER="$PROJECT_ROOT/tools/rbot_env_exec.sh"
CTL_SCRIPT="$PROJECT_ROOT/tools/rbotctl.sh"

if [ "$(id -un)" != "ing" ]; then
  echo "Please run this installer as user 'ing' (or run with sudo to manage systemd)"
fi

echo "Installing service unit to $UNIT_PATH (requires sudo)"
sudo tee "$UNIT_PATH" > /dev/null <<'UNIT'
[Unit]
Description=RBOTzilla Headless Runner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ing
WorkingDirectory=/home/ing/RICK/MULTI_BROKER_PHOENIX
ExecStart=/home/ing/RICK/MULTI_BROKER_PHOENIX/tools/rbot_env_exec.sh
Restart=always
RestartSec=3
StartLimitIntervalSec=0
KillMode=process
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

# Ensure wrapper is executable
chmod +x "$EXEC_WRAPPER"
chmod +x "$CTL_SCRIPT"

# Set safe defaults in .env if missing
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
  if ! grep -q '^TRADING_MODE=' "$ENV_FILE"; then
    echo "TRADING_MODE=PAPER" >> "$ENV_FILE"
    echo "Added TRADING_MODE=PAPER to .env (safe default)"
  fi
  if ! grep -q '^ALLOW_PAPER_WITHOUT_HIVE=' "$ENV_FILE"; then
    echo "ALLOW_PAPER_WITHOUT_HIVE=0" >> "$ENV_FILE"
    echo "Added ALLOW_PAPER_WITHOUT_HIVE=0 to .env (explicitly deny simple HIVE by default)"
  fi
else
  echo "TRADING_MODE=PAPER" > "$ENV_FILE"
  echo "ALLOW_PAPER_WITHOUT_HIVE=0" >> "$ENV_FILE"
  echo "Created .env with safe defaults (TRADING_MODE=PAPER, ALLOW_PAPER_WITHOUT_HIVE=0)"
fi

# Install systemd unit templates (broker link + engine paper + engine live template)
echo "Installing systemd units (may require sudo)"
sudo cp "$PROJECT_ROOT/tools/systemd/rbotzilla-broker-link.service" /etc/systemd/system/
sudo cp "$PROJECT_ROOT/tools/systemd/rbotzilla-engine-paper.service" /etc/systemd/system/
sudo cp "$PROJECT_ROOT/tools/systemd/rbotzilla-engine-live.service" /etc/systemd/system/ || true

# Reload systemd and enable default (paper) services
echo "Reloading systemd and enabling broker-link + engine-paper (paper default)"
sudo systemctl daemon-reload
sudo systemctl enable --now rbotzilla-broker-link.service
sudo systemctl enable --now rbotzilla-engine-paper.service

# Do NOT enable live service by default (must be PIN-gated via engine_mode.sh)
sudo systemctl disable rbotzilla-engine-live.service || true

# Generate a PIN for enabling LIVE trading (stored under the user's rbot folder)
RBOT_DIR="$HOME/.rbotzilla"
if [ ! -d "$RBOT_DIR" ]; then
  mkdir -p "$RBOT_DIR"
  chown "$USER:$USER" "$RBOT_DIR" || true
fi
PIN_FILE="$RBOT_DIR/live_pin.txt"
if [ ! -f "$PIN_FILE" ]; then
  PIN=$(shuf -n1 -i 100000-999999)
  echo "$PIN" > "$PIN_FILE"
  chmod 600 "$PIN_FILE"
  echo "Generated LIVE PIN at $PIN_FILE (keep it safe)"
else
  echo "Existing LIVE PIN found at $PIN_FILE"
fi

echo "Installation complete. Useful commands:"
echo "  sudo systemctl status $SERVICE_NAME"
echo "  sudo journalctl -u $SERVICE_NAME -f"
echo "  $PROJECT_ROOT/tools/rbotctl.sh"
echo "  $PROJECT_ROOT/tools/engine_mode.sh --help"

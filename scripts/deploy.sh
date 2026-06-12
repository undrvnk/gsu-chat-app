#!/usr/bin/env bash
# Run on the server after git pull (manually or via the Deploy workflow).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing Python dependencies"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "==> Ensuring database schema exists"
python3 -c 'import app; app.init_db()'

if systemctl is-active --quiet gsu-chat-app 2>/dev/null; then
  echo "==> Restarting gsu-chat-app systemd service"
  sudo systemctl restart gsu-chat-app
elif systemctl list-unit-files gsu-chat-app.service >/dev/null 2>&1; then
  echo "==> Starting gsu-chat-app systemd service"
  sudo systemctl start gsu-chat-app
else
  echo "==> No gsu-chat-app systemd unit found."
  echo "    Install deploy/gsu-chat-app.service, or start manually: python3 app.py"
fi

echo "==> Deploy finished."

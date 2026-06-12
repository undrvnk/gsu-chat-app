#!/usr/bin/env bash
# Run on the server after git pull (manually or via the Deploy workflow).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Ensuring gunicorn is available"
if ! command -v gunicorn >/dev/null; then
  echo "Run: sudo apt install gunicorn"
fi

echo "==> Ensuring database schema exists"
python3 -c 'import app; app.init_db()'

if systemctl is-active --quiet gsu-chat-app 2>/dev/null; then
  echo "==> Restarting gsu-chat-app systemd service"
  sudo systemctl restart gsu-chat-app
  if systemctl is-active --quiet nginx 2>/dev/null; then
    sudo systemctl reload nginx
  fi
elif systemctl list-unit-files gsu-chat-app.service >/dev/null 2>&1; then
  echo "==> Starting gsu-chat-app systemd service"
  sudo systemctl start gsu-chat-app
else
  echo "==> No gsu-chat-app systemd unit found."
  echo "    Run: bash scripts/setup-nginx.sh"
fi

echo "==> Deploy finished."

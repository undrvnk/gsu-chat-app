#!/usr/bin/env bash
# Production setup: gunicorn + nginx on your existing port (default 5000).
# Keeps your current router NAT rule — no port-forward changes needed.
# Usage: bash scripts/setup-nginx.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=gsu-chat-app
PUBLIC_PORT="${PORT:-5000}"

if [[ -f "$ROOT/.env" ]]; then
  line="$(grep -E '^PORT=' "$ROOT/.env" 2>/dev/null | tail -1 || true)"
  if [[ -n "$line" ]]; then
    PUBLIC_PORT="${line#PORT=}"
    PUBLIC_PORT="${PUBLIC_PORT//\"/}"
    PUBLIC_PORT="${PUBLIC_PORT//\'/}"
  fi
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

USER_NAME="${SUDO_USER:-jason}"

echo "==> Public port: ${PUBLIC_PORT} (matches your existing router rule)"

echo "==> Installing gunicorn (if missing)"
if ! command -v gunicorn >/dev/null; then
  apt-get update -qq
  apt-get install -y gunicorn
fi

echo "==> Stopping old app on port ${PUBLIC_PORT}"
systemctl stop "$SERVICE" 2>/dev/null || true
fuser -k "${PUBLIC_PORT}/tcp" 2>/dev/null || true
sleep 1

echo "==> Installing systemd unit (gunicorn on 127.0.0.1:8000)"
cp "$ROOT/deploy/gsu-chat-app.service" "/etc/systemd/system/${SERVICE}.service"
sed -i "s|/home/jason/gsu-chat-app|${ROOT}|g" "/etc/systemd/system/${SERVICE}.service"
sed -i "s/User=jason/User=${USER_NAME}/" "/etc/systemd/system/${SERVICE}.service"

echo "==> Allowing nginx (www-data) to read static files under /home/${USER_NAME}"
chmod o+x "/home/${USER_NAME}"

echo "==> Installing nginx site (port ${PUBLIC_PORT})"
cp "$ROOT/deploy/nginx-gsu-chat-app.conf" /etc/nginx/sites-available/${SERVICE}
sed -i "s|/home/jason/gsu-chat-app|${ROOT}|g" /etc/nginx/sites-available/${SERVICE}
sed -i "s/listen 5000/listen ${PUBLIC_PORT}/g" /etc/nginx/sites-available/${SERVICE}
ln -sf /etc/nginx/sites-available/${SERVICE} /etc/nginx/sites-enabled/${SERVICE}
rm -f /etc/nginx/sites-enabled/default
nginx -t

SUDOERS="/etc/sudoers.d/${SERVICE}"
cat > "$SUDOERS" <<EOF
${USER_NAME} ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE}, /bin/systemctl start ${SERVICE}, /bin/systemctl stop ${SERVICE}, /bin/systemctl status ${SERVICE}, /bin/systemctl reload nginx, /bin/systemctl restart nginx
EOF
chmod 440 "$SUDOERS"
visudo -cf "$SUDOERS"

systemctl daemon-reload
systemctl enable "$SERVICE" nginx
systemctl restart "$SERVICE"
systemctl restart nginx

echo ""
systemctl status "$SERVICE" --no-pager | head -12
echo ""
curl -o /dev/null -s -w "Local test http://127.0.0.1:${PUBLIC_PORT}/ → %{time_total}s\n" "http://127.0.0.1:${PUBLIC_PORT}/" || true
echo ""
echo "Done. Keep your existing router rule (external ${PUBLIC_PORT} → this PC ${PUBLIC_PORT})."
echo "  At home:    http://192.168.1.165:${PUBLIC_PORT}"
echo "  Anywhere:   http://70.133.221.153:${PUBLIC_PORT}"

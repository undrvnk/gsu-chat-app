#!/usr/bin/env bash
# One-time setup: run on the server with sudo access.
# Usage: bash scripts/install-systemd.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=gsu-chat-app

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

# whoami is root after sudo; SUDO_USER is the real login (e.g. jason).
USER_NAME="${SUDO_USER:-$(whoami)}"

echo "==> Installing systemd unit for $SERVICE"
cp "$ROOT/deploy/gsu-chat-app.service" "/etc/systemd/system/${SERVICE}.service"
sed -i "s|/home/jason/gsu-chat-app|${ROOT}|g" "/etc/systemd/system/${SERVICE}.service"
sed -i "s/User=jason/User=${USER_NAME}/" "/etc/systemd/system/${SERVICE}.service"

echo "==> Stopping manual python on port 5000 (if any)"
fuser -k 5000/tcp 2>/dev/null || true
sleep 1

echo "==> Enabling passwordless systemctl for deploy user"
SUDOERS="/etc/sudoers.d/${SERVICE}"
cat > "$SUDOERS" <<EOF
${USER_NAME} ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE}, /bin/systemctl start ${SERVICE}, /bin/systemctl stop ${SERVICE}, /bin/systemctl status ${SERVICE}
EOF
chmod 440 "$SUDOERS"
visudo -cf "$SUDOERS"

systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo ""
systemctl status "$SERVICE" --no-pager || true
echo ""
echo "Done. Check http://$(hostname -I | awk '{print $1}'):5000 or your public IP."

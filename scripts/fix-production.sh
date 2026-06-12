#!/usr/bin/env bash
# Apply production fixes (run once after pulling latest code):
#   bash scripts/fix-production.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE=gsu-chat-app

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Re-running with sudo..."
  exec sudo -E bash "$0" "$@"
fi

USER_NAME="${SUDO_USER:-jason}"

echo "==> Updating systemd unit (User=${USER_NAME}, FLASK_DEBUG=0)"
cp "$ROOT/deploy/gsu-chat-app.service" "/etc/systemd/system/${SERVICE}.service"
sed -i "s|/home/jason/gsu-chat-app|${ROOT}|g" "/etc/systemd/system/${SERVICE}.service"
sed -i "s/User=jason/User=${USER_NAME}/" "/etc/systemd/system/${SERVICE}.service"

SUDOERS="/etc/sudoers.d/${SERVICE}"
cat > "$SUDOERS" <<EOF
${USER_NAME} ALL=(ALL) NOPASSWD: /bin/systemctl restart ${SERVICE}, /bin/systemctl start ${SERVICE}, /bin/systemctl stop ${SERVICE}, /bin/systemctl status ${SERVICE}
EOF
chmod 440 "$SUDOERS"
visudo -cf "$SUDOERS"

systemctl daemon-reload
systemctl restart "$SERVICE"
sleep 1
systemctl status "$SERVICE" --no-pager
echo ""
echo "Local speed check:"
curl -o /dev/null -s -w "  / → %{time_total}s\n" http://127.0.0.1:5000/

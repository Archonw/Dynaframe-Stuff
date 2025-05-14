#!/bin/bash

# === INTERAKTIVE ABFRAGEN ===
read -rp "🔧 Raspberry Pi IP oder Hostname: " PI_HOST
read -rp "👤 Benutzername [default: pi]: " PI_USER
PI_USER=${PI_USER:-pi}

# === KONSTANTEN ===
REPO_URL="https://github.com/Archonw/Dynaframe-Stuff.git"
CLONE_DIR="/home/${PI_USER}/temp_dynaframe_repo"
TARGET_DIR="/home/${PI_USER}/Dynaframe/Assets/dfplugins"
PLUGIN_DIR="${TARGET_DIR}/youtube-player"
SERVICE_NAME="youtube-player"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_PATH="${PLUGIN_DIR}/youtube-player.py"

# === SYSTEMD SERVICE-DEFINITION ===
read -r -d '' SERVICE_CONTENT <<EOF
[Unit]
Description=Youtube-Player
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${SCRIPT_PATH}
WorkingDirectory=${PLUGIN_DIR}
Restart=always
User=${PI_USER}

[Install]
WantedBy=multi-user.target
EOF

# === SSH-LOGIK ===
echo "🔐 Verbinde zu ${PI_USER}@${PI_HOST} ..."

ssh "${PI_USER}@${PI_HOST}" bash -s <<EOF
set -e

echo "⬇️ Klone Repository ..."
rm -rf ${CLONE_DIR}
git clone ${REPO_URL} ${CLONE_DIR}

echo "📂 Kopiere youtube-player Plugin ..."
mkdir -p ${TARGET_DIR}
rm -rf ${PLUGIN_DIR}
mv ${CLONE_DIR}/youtube-player ${PLUGIN_DIR}

echo "🧹 Lösche restliches Repository ..."
rm -rf ${CLONE_DIR}

# Prüfe, ob das Python-Skript existiert
if [ ! -f "${SCRIPT_PATH}" ]; then
    echo "❌ Fehler: Python-Skript nicht gefunden: ${SCRIPT_PATH}"
    exit 1
fi

echo "🛠️ Erstelle systemd-Dienstdatei unter ${SERVICE_FILE} ..."
echo '${SERVICE_CONTENT}' | sudo tee ${SERVICE_FILE} > /dev/null

echo "🔄 Lade systemd neu ..."
sudo systemctl daemon-reload

echo "✅ Aktiviere Dienst ${SERVICE_NAME} ..."
sudo systemctl enable ${SERVICE_NAME}.service

echo "🚀 Starte Dienst ${SERVICE_NAME} ..."
sudo systemctl restart ${SERVICE_NAME}.service

echo "📋 Status:"
sudo systemctl status ${SERVICE_NAME}.service --no-pager
EOF

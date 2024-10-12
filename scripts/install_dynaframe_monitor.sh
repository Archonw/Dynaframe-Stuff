#!/bin/bash

# Verzeichnisse erstellen
mkdir -p /opt/dynaframe

# Herunterladen des Monitor-Skripts von GitHub
wget -O /opt/dynaframe/dynaframe_monitor.sh https://raw.githubusercontent.com/Archonw/Dynaframe-Stuff/main/scripts/dynaframe_monitor.sh
chmod +x /opt/dynaframe/dynaframe_monitor.sh

# Systemd-Dienstdatei erstellen
cat <<EOT > /etc/systemd/system/dynaframe-monitor.service
[Unit]
Description=Überwachung des Dynaframe-Prozesses

[Service]
ExecStart=/opt/dynaframe/dynaframe_monitor.sh
Restart=always

[Install]
WantedBy=multi-user.target
EOT

# Dienst aktivieren und starten
systemctl daemon-reload
systemctl enable dynaframe-monitor.service
systemctl start dynaframe-monitor.service

echo "Dynaframe-Monitor-Dienst wurde erfolgreich eingerichtet und gestartet."

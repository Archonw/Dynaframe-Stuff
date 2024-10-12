#!/bin/bash

# Name des Prozesses, den du überwachen möchtest
PROCESS_NAME="Dynaframe"
LOG_FILE="/home/pi/Dynaframe/dynaframe_monitor.log"
CHECK_INTERVAL=10  # Prüfintervall in Sekunden

# Warte 2 Minuten, bevor das Monitoring startet
sleep 120

while true
do
    # Überprüfen, ob der Prozess läuft
    if ! pgrep -x "$PROCESS_NAME" > /dev/null
    then
        # Prozess läuft nicht, Datum und Uhrzeit ins Log schreiben
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $PROCESS_NAME abgestürzt, Neustart wird durchgeführt" >> $LOG_FILE

        # Warte 5 Sekunden, um sicherzustellen, dass Logs korrekt geschrieben werden
        sleep 5

        # Neustart des Systems erzwingen
        sudo reboot

        # Das Log nach dem Neustart (wird wahrscheinlich nicht erreicht)
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $PROCESS_NAME neu gestartet" >> $LOG_FILE
    fi

    # Warten für das definierte Intervall
    sleep $CHECK_INTERVAL
done

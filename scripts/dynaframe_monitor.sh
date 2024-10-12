#!/bin/bash

# Name des Prozesses, den du überwachen möchtest
PROCESS_NAME="Dynaframe"
LOG_FILE="/home/pi/Dynaframe/dynaframe_monitor.log"
CHECK_INTERVAL=10  # Prüfintervall in Sekunden

while true
do
    # Überprüfen, ob der Prozess läuft
    if ! pgrep -x "$PROCESS_NAME" > /dev/null
    then
        # Prozess läuft nicht, Datum und Uhrzeit ins Log schreiben
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $PROCESS_NAME abgestürzt, Neustart wird durchgeführt" >> $LOG_FILE

        # Programm neu starten
        reboot &

        echo "$(date '+%Y-%m-%d %H:%M:%S') - $PROCESS_NAME neu gestartet" >> $LOG_FILE
    fi

    # Warten für das definierte Intervall
    sleep $CHECK_INTERVAL
done

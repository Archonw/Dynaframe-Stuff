#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gpiozero import Button
from signal import pause
import os
import subprocess

CAMERA_STOP_FILE = "/tmp/camera_stop"
START_SCRIPT = "/home/pi/camera-service/start.sh"
STOP_SCRIPT = "/home/pi/camera-service/stop.sh"

def toggle_camera_service():
    """Turns off the camera service based on the existence of /tmp/camera_stop."""
    if os.path.exists(CAMERA_STOP_FILE):
        print(f"{CAMERA_STOP_FILE} found. Start {START_SCRIPT}...")
        subprocess.run(["bash", START_SCRIPT], check=True)
        # Remove file to change state
        try:
            os.remove(CAMERA_STOP_FILE)
            print(f"{CAMERA_STOP_FILE} removed.")
        except FileNotFoundError:
            print(f"{CAMERA_STOP_FILE} does not exist, no deletion required.")
    else:
        print(f"{CAMERA_STOP_FILE} not found. Start {STOP_SCRIPT}...")
        subprocess.run(["bash", STOP_SCRIPT], check=True)
	# Create file to change state
        with open(CAMERA_STOP_FILE, "w") as file:
            file.write("Stop file created by toggle_camera_service script.\n")
        print(f"{CAMERA_STOP_FILE} was created.")

# button-setup
button = Button(21)  # Number indicates the GPIO pin used

button.when_pressed = toggle_camera_service

print("Ready to monitor buttons...")

#Waiting for events
pause()

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gpiozero import Button
from subprocess import check_call
from signal import pause
import os
import requests
import json

Button.was_held = False

APP_SETTINGS_PATH = "/home/pi/Dynaframe/appsettings.json"

def get_current_volume():
    """Reads the current volume from the appsettings.json."""
    try:
        with open(APP_SETTINGS_PATH, "r") as file:
            settings = json.load(file)
        return settings.get("SystemVolumeLevel", 0)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading file {APP_SETTINGS_PATH}: {e}")
        return 0  # Default value if an error occurs

def toggle_volume():
    """Toggles the volume between 0 and 100."""
    current_volume = get_current_volume()
    if current_volume > 0:
        response = requests.get("http://127.0.0.1/command/?COMMAND=SystemVolumeLevel&VALUE=0")
        print("Volume set to 0")
    else:
        response = requests.get("http://127.0.0.1/command/?COMMAND=SystemVolumeLevel&VALUE=100")
        print("Volume set to 100")

def shutdown():
    """Shuts down the system."""
    print("System is shutting down")
    os.system('sudo shutdown now')

def held(btn):
    """Called when the button is held."""
    btn.was_held = True
    print("Button was held, not just pressed")
    shutdown()

def released(btn):
    """Called when the button is released."""
    if not btn.was_held:
        toggle_volume()
    btn.was_held = False

# Button-Setup
btn = Button(20, hold_time=4)  # Set the hold_time to the desired time in seconds

btn.when_held = held
btn.when_released = released

# Waiting
pause()

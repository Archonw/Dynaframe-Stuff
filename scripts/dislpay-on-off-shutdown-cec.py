#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gpiozero import Button
from subprocess import call
from signal import pause
import os

Button.was_held = False
button_state = {"last_command": "as"}

def toggle_cec_command():
    if button_state["last_command"] == "standby":
        call("echo 'as' 0 | cec-client -s -d 1", shell=True)
        button_state["last_command"] = "as"
        print("Command executed: as 0")
    else:
        call("echo 'standby' 0 | cec-client -s -d 1", shell=True)
        button_state["last_command"] = "standby"
        print("Command executed: standby 0")

def shutdown():
    print("Shutdown function called")
    os.system('sudo shutdown now')

def held(btn):
    btn.was_held = True
    print("Button was held, not just pressed")
    shutdown()

def released(btn):
    if not btn.was_held:
        toggle_cec_command()
    btn.was_held = False

btn = Button(26, hold_time=6)  # Setze die hold_time auf die gewünschte Zeit in Sekunden

btn.when_held = held
btn.when_released = released

# Warten
pause()


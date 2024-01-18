#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gpiozero import Button
from subprocess import check_call
from signal import pause
import os
import requests

Button.was_held = False
button_pressed_time = None

def get_display_power_status():
    result = os.popen('vcgencmd display_power').read()
    return int(result.split('=')[1])

def toggle_display():
    current_status = get_display_power_status()
    if current_status == 1:
        response = requests.get("http://127.0.0.1/command/?COMMAND=SCREENSTATE&VALUE=false")
        print("Display off")
    else:
        response = requests.get("http://127.0.0.1/command/?COMMAND=SCREENSTATE&VALUE=true")
        print("Dislpay on")

def shutdown():
    print("Shutdown function called")
    os.system('sudo shutdown now')

def held(btn):
    btn.was_held = True
    print("Button was held, not just pressed")
    shutdown()

def released(btn):
    if not btn.was_held:
        toggle_display()
    btn.was_held = False

btn = Button(19, hold_time=4)  # Set your GPIO number and hold time here

btn.when_held = held
btn.when_released = released

# Warten
pause()

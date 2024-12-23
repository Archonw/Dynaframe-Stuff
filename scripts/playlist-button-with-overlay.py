#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import time
import RPi.GPIO as GPIO
import os
import json

# Configure GPIO pin (use the correct pin)
button_pin = 21
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# URL for the HTTP command
url = "http://127.0.0.1/command/"

folder_index = 0

def get_directory_list():
    # Command to retrieve the dynamic directory list
    get_list_params = {"COMMAND": "GETSTRINGSUBDIRECTORIES"}

    try:
        list_response = requests.get(url, params=get_list_params)
        if list_response.status_code == 200:
            return list_response.text.split(";")
        else:
            print("Error retrieving directory list.")
            return None
    except Exception as e:
        print("Error retrieving directory list:", e)
        return None

def update_playlist_info(playlist_name):
    # File path to the JSON file
    json_file_path = "/home/pi/Dynaframe/Assets/Overlays/Playlist_Info.json"
    try:
        # Load the current JSON content
        with open(json_file_path, 'r') as json_file:
            json_data = json.load(json_file)

        # Update the SIMPLETEXTVALUE field with the new playlist name
        json_data[0]['Settings']['SIMPLETEXTVALUE'] = playlist_name

        # Write the updated JSON back to the file
        with open(json_file_path, 'w') as json_file:
            json.dump(json_data, json_file, indent=4)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def enable_overlay():
    # Enable the overlay
    enable_params = {"COMMAND": "EnableOverlay", "VALUE": "true"}
    requests.get(url, params=enable_params)
    time.sleep(10)
    # Disable the overlay after 10 seconds
    disable_params = {"COMMAND": "EnableOverlay", "VALUE": "false"}
    requests.get(url, params=disable_params)

def simulate_button_press():
    global folder_index

    # Command to retrieve the directory list
    directory_list = get_directory_list()

    if directory_list:
        while True:
            if folder_index < len(directory_list):
                # Extract information for the current index
                directory_info = directory_list[folder_index].split(",")

                if len(directory_info) >= 2:
                    folder = directory_info[0]
                    folder_path = directory_info[1]

                    # Manually construct the URL to avoid unwanted encoding
                    set_params = f"COMMAND=SETSUBDIRECTORIES&VALUE={folder_path}"
                    set_url = f"{url}?{set_params}"

                    try:
                        set_response = requests.get(set_url)
                        if set_response.status_code == 200:
                            print(f"SETSUBDIRECTORIES command executed successfully for {folder}.")
                            
                            # Update the playlist info JSON file
                            update_playlist_info(folder)
                            
                            # Enable the overlay
                            enable_overlay()
                            
                        else:
                            print(f"Error executing SETSUBDIRECTORIES command for {folder}.")
                    except Exception as e:
                        print(f"Error executing SETSUBDIRECTORIES command for {folder}:", e)

                    # Increment the index for the next button press
                    folder_index = (folder_index + 1) % len(directory_list)
                    break  # Exit the loop if valid directory information is found
                else:
                    print("Error: Invalid directory information.")
                    # Increment the index for the next button press
                    folder_index = (folder_index + 1) % len(directory_list)
            else:
                # If the index is outside the valid range, start from the beginning
                folder_index = 0
                print("Starting from the beginning of the list.")
                break  # Exit the loop to wait for another button press

        print("Waiting for another button press...")

def button_callback(channel):
    print("Button pressed.")
    simulate_button_press()

GPIO.add_event_detect(button_pin, GPIO.FALLING, callback=button_callback, bouncetime=700)

def list_subdirectories(base_directory):
    return [d for d in os.listdir(base_directory) if os.path.isdir(os.path.join(base_directory, d))]

try:
    print("Waiting for button press...")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()

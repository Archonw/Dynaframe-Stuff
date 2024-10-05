import json
import requests
import time
import argparse
from datetime import datetime
import urllib.parse
import os
import uuid  # Für das Erstellen einer eindeutigen ID

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process time and command parameters.')
    parser.add_argument('--timeInput', type=str, help='A time input parameter', required=False)
    parser.add_argument('--commandandparam', type=str, help='A comma delimited value for command and param', required=False)
    parser.add_argument('--deleteId', type=str, help='The ID of the entry to delete', required=False)  # Neue Option zum Löschen nach ID

    args = parser.parse_args()

    if args.commandandparam is None:
        command = None
        args.timeInput = None
        param = None
    else:
        print(f"command and param are: {args.commandandparam}")
        command, param = args.commandandparam.split(',')
    return args.timeInput, command, param, args.deleteId  # Rückgabe von deleteId

def read_schedule(filename):
    full_path = os.path.join(SCRIPT_DIR, filename)
    try:
        with open(full_path, 'r') as file:
            schedule = json.load(file)
        return schedule
    except FileNotFoundError:
        print(f"Schedule file not found: {full_path}")
        return []

def write_schedule(filename, data):
    full_path = os.path.join(SCRIPT_DIR, filename)
    with open(full_path, 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)

def send_http_request(ip_address, command, cparam):
    url = f"http://{ip_address}/command/?COMMAND={command}&VALUE={urllib.parse.quote(cparam)}"
    response = requests.get(url)
    print(f"HTTP request sent to {url}. Response: {response.text}")

def clear_json_file(filename):
    full_path = os.path.join(SCRIPT_DIR, filename)
    with open(full_path, 'w') as f:
        json.dump([], f)

def delete_entry_by_id(filename, delete_id):
    schedule = read_schedule(filename)
    updated_schedule = [entry for entry in schedule if entry['id'] != delete_id]  # Filtert Eintrag nach ID heraus

    if len(schedule) == len(updated_schedule):
        print(f"No entry found with ID: {delete_id}")
    else:
        print(f"Entry with ID: {delete_id} deleted.")
        write_schedule(filename, updated_schedule)

def main():
    targetTime, command, param, deleteId = parse_arguments()

    print(f'Time: {targetTime}')
    print(f'Command: {command}')
    print(f'Param: {param}')
    print(f'Delete ID: {deleteId}')  # Zeigt die zu löschende ID an

    filename = 'schedule.json'

    if deleteId is not None:
        delete_entry_by_id(filename, deleteId)  # Löscht Eintrag nach ID
        exit()

    if command == 'clear':
        print("Clearing out files!")
        clear_json_file(filename)
        exit()

    if targetTime is not None:
        entry_id = str(uuid.uuid4())  # Erstellt eine eindeutige ID
        data = {"id": entry_id, "time": targetTime, "command": command, "parameter": param}

        try:
            with open(os.path.join(SCRIPT_DIR, filename), 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = []

        if existing_data == {}:
            existing_data = []

        existing_data.append(data)

        write_schedule(filename, existing_data)

        print(f"Entry added with ID: {entry_id}")  # Zeigt die ID des neuen Eintrags an
        exit()

    ip_address = 'localhost'

    while True:
        current_time = datetime.now().strftime('%H:%M')
        print(f"Time is: {current_time}")
        try:
            schedule = read_schedule(filename)
            for entry in schedule:
                if entry['time'] == current_time:
                    print(f"Sending command {entry['command']} with param: {entry['parameter']}")
                    send_http_request(ip_address, entry['command'], entry['parameter'])
        except Exception as e:
            print(f"An error occurred: {e}")
        print("Sleeping")
        time.sleep(60)

if __name__ == "__main__":
    main()


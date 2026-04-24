#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import time
import RPi.GPIO as GPIO
import os
import signal
import sys
from threading import Timer
import threading
import queue
import tkinter as tk

# ─────────────────────────────────────────────
# Konfiguration
# ─────────────────────────────────────────────
BUTTON_PIN = 21
BASE_URL = "http://127.0.0.1:5000"
INACTIVITY_TIMEOUT = 10.0
MENU_WIDTH = 700
ITEM_HEIGHT = 55
FONT_NAME = "Helvetica"
FONT_SIZE = 28
DISPLAY = ":0"
VISIBLE_ITEMS = 6

# ─────────────────────────────────────────────
# GPIO Setup
# ─────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ─────────────────────────────────────────────
# Dynaframe REST API Funktionen
# ─────────────────────────────────────────────
def get_directory_list():
    try:
        response = requests.get(f"{BASE_URL}/api/DirectoryAPI/GetDirectories")
        if response.status_code == 200:
            data = response.json()
            # Nur "echte" Ordner, keine Sync/System-Ordner
            return [e for e in data if e.get("directoryType") == 0]
    except Exception as e:
        print("Fehler beim Laden der Verzeichnisliste:", e)
    return []

def get_active_index(directory_list):
    for idx, entry in enumerate(directory_list):
        if entry.get("enabled"):
            return idx
    return 0

def activate_playlist(entry):
    try:
        response = requests.post(
            f"{BASE_URL}/api/DirectoryAPI/SetPlaylistDirectories",
            params={"DisableOthers": "true"},
            json=[entry["fullPath"]]
        )
        if response.status_code == 200:
            print(f"Playlist aktiviert: {entry['friendlyName']}")
        else:
            print(f"Fehler beim Aktivieren: HTTP {response.status_code}")
    except Exception as e:
        print("Fehler beim Aktivieren der Playlist:", e)

# ─────────────────────────────────────────────
# Menü Klasse
# ─────────────────────────────────────────────
class PlaylistMenu:
    def __init__(self, directory_list, start_index):
        self.directory_list = directory_list
        self.names = [e["friendlyName"] for e in directory_list]
        self.current_index = start_index
        self.inactivity_timer = None
        self.root = None
        self.canvas = None
        self.closed = False
        self._cmd_queue = queue.Queue()

    def _process_queue(self):
        try:
            while True:
                cmd = self._cmd_queue.get_nowait()
                if cmd == "next":
                    self.current_index = (self.current_index + 1) % len(self.names)
                    self._draw()
                    self._reset_timer()
                elif cmd == "close":
                    self._do_close()
        except queue.Empty:
            pass
        if not self.closed and self.root:
            self.root.after(50, self._process_queue)

    def _draw(self):
        if not self.canvas or self.closed:
            return
        self.canvas.delete("all")
        scroll_offset = max(0, min(self.current_index - VISIBLE_ITEMS // 2,
                                   len(self.names) - VISIBLE_ITEMS))
        canvas_height = VISIBLE_ITEMS * ITEM_HEIGHT

        for i, name in enumerate(self.names):
            y = (i - scroll_offset) * ITEM_HEIGHT
            if y < -ITEM_HEIGHT or y > canvas_height:
                continue
            if i == self.current_index:
                self.canvas.create_rectangle(0, y, MENU_WIDTH, y + ITEM_HEIGHT,
                                             fill="#1a73e8", outline="")
                self.canvas.create_text(20, y + ITEM_HEIGHT // 2,
                                        text=f"▶  {name}", anchor="w",
                                        font=(FONT_NAME, FONT_SIZE, "bold"),
                                        fill="white")
            else:
                self.canvas.create_rectangle(0, y, MENU_WIDTH, y + ITEM_HEIGHT,
                                             fill="#1e1e1e", outline="")
                self.canvas.create_text(20, y + ITEM_HEIGHT // 2,
                                        text=f"    {name}", anchor="w",
                                        font=(FONT_NAME, FONT_SIZE),
                                        fill="#cccccc")
            self.canvas.create_line(0, y + ITEM_HEIGHT - 1, MENU_WIDTH,
                                    y + ITEM_HEIGHT - 1, fill="#333333")

        if len(self.names) > VISIBLE_ITEMS:
            bar_h = max(20, canvas_height * VISIBLE_ITEMS // len(self.names))
            bar_y = canvas_height * scroll_offset // len(self.names)
            self.canvas.create_rectangle(MENU_WIDTH - 6, bar_y,
                                         MENU_WIDTH - 2, bar_y + bar_h,
                                         fill="#555555", outline="")

    def next(self):
        if not self.closed:
            self._cmd_queue.put("next")

    def close(self):
        if not self.closed:
            self._cmd_queue.put("close")

    def _reset_timer(self):
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
        self.inactivity_timer = Timer(INACTIVITY_TIMEOUT, self._on_timeout)
        self.inactivity_timer.start()

    def _on_timeout(self):
        print(f"Timeout – aktiviere: {self.names[self.current_index]}")
        activate_playlist(self.directory_list[self.current_index])
        self._cmd_queue.put("close")

    def _do_close(self):
        if self.closed:
            return
        self.closed = True
        if self.inactivity_timer:
            self.inactivity_timer.cancel()
            self.inactivity_timer = None
        self.canvas = None
        if self.root:
            self.root.withdraw()
            self.root.after(100, self._destroy)

    def _destroy(self):
        if self.root:
            self.root.quit()

    def run(self):
        os.environ["DISPLAY"] = DISPLAY
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e1e")

        win_height = VISIBLE_ITEMS * ITEM_HEIGHT + 34
        screen_width = self.root.winfo_screenwidth()
        x = (screen_width - MENU_WIDTH) // 2
        self.root.geometry(f"{MENU_WIDTH}x{win_height}+{x}+20")

        tk.Label(self.root,
                 text="Playlist auswählen",
                 font=(FONT_NAME, 16, "bold"),
                 fg="#888888", bg="#111111", pady=6).pack(fill="x")

        self.canvas = tk.Canvas(self.root, bg="#1e1e1e",
                                highlightthickness=0,
                                width=MENU_WIDTH,
                                height=VISIBLE_ITEMS * ITEM_HEIGHT)
        self.canvas.pack(fill="both", expand=True)

        self._draw()
        self._reset_timer()
        self.root.after(50, self._process_queue)
        self.root.mainloop()
        print("Menü geschlossen.")


# ─────────────────────────────────────────────
# Globaler Menü-Zustand
# ─────────────────────────────────────────────
active_menu = None

def button_callback(channel):
    global active_menu
    print("Button gedrückt.")
    print(f"  → active_menu={active_menu}, closed={active_menu.closed if active_menu else 'N/A'}")

    if active_menu is not None and not active_menu.closed:
        active_menu.next()
        return

    directory_list = get_directory_list()
    if not directory_list:
        print("Keine Playlists gefunden.")
        return
    start_index = get_active_index(directory_list)
    menu = PlaylistMenu(directory_list, start_index)
    active_menu = menu
    threading.Thread(target=menu.run, daemon=True).start()

GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=button_callback, bouncetime=300)

# ─────────────────────────────────────────────
# Strg+C Handler
# ─────────────────────────────────────────────
def signal_handler(sig, frame):
    print("\nBeende...")
    if active_menu:
        active_menu.close()
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ─────────────────────────────────────────────
# Hauptprogramm
# ─────────────────────────────────────────────
print("Warte auf Button-Druck...")
while True:
    time.sleep(1)


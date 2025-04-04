from flask import Flask, render_template, request, jsonify
import yt_dlp
import threading
import time
import subprocess
import urllib.parse
import os
import re

app = Flask(__name__)
VIDEO_URLS_FILE = "video-urls.txt"  # Pfad zur Datei mit den URLs
selected_videos = []
is_playing = False  # Variable, die angibt, ob die Wiedergabe läuft
playback_thread = None  # Verweis auf den Wiedergabe-Thread

# Funktion zum Laden der URLs
def load_urls():
    if not os.path.exists(VIDEO_URLS_FILE):
        return []
    
    try:
        with open(VIDEO_URLS_FILE, 'r') as file:
            links = [line.strip() for line in file if line.strip()]
            print("URLs geladen:", links)  # Debugging-Ausgabe
        return links
    except Exception as e:
        print(f"Fehler beim Laden der URLs: {e}")  # Fehlerprotokollierung
        return []

# Funktion zum Abrufen des Titels eines Videos
def get_video_title(url):
    try:
        # Wenn es sich um eine RTSP-URL handelt
        if url.startswith("rtsp://"):
            # Extrahiere die IP-Adresse oder den Hostnamen aus der URL
            match = re.match(r"rtsp://([^/]+)", url)
            if match:
                ip_address = match.group(1)
                return f"RTSP - {ip_address}"  # Nur die IP-Adresse nach "RTSP -"
            else:
                return "RTSP - Unknown IP"  # Falls keine IP gefunden wurde
        else:
            # Standard Titel mit yt-dlp für andere URLs
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "noplaylist": True,
                "force_generic_extractor": True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info.get('title', 'Unknown')
    except Exception:
        return "Error retrieving title"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_videos', methods=['GET'])
def load_videos():
    links = load_urls()
    if not links:
        return jsonify({"status": "error", "message": "No valid URLs found."})
    
    video_data = [{"url": link, "title": get_video_title(link), "time": 120} for link in links]
    print("Video-Daten:", video_data)  # Debugging-Ausgabe
    return jsonify(video_data)

@app.route('/set_videos', methods=['POST'])
def set_videos():
    global selected_videos
    selected_videos = request.json.get("videos", [])
    print(f"Selected Videos: {selected_videos}")  # Debugging-Ausgabe
    return jsonify({"status": "success"})

@app.route('/play', methods=['POST'])
def play_videos():
    global is_playing, playback_thread
    if is_playing:
        return jsonify({"status": "already playing"})
    
    def play_thread():
        global is_playing
        is_playing = True
        while True:
            if not selected_videos:
                break
            
            for video in selected_videos:
                if not is_playing:  # Wenn die Wiedergabe gestoppt wurde, beenden wir die Schleife
                    break

                encoded_url = urllib.parse.quote(video['url'], safe='')
                cmd = [
                    "curl", "-X", "GET",
                    f"http://localhost:5000/api/PlayFileAPI/PlayFullDirectVideoUrl?URL={encoded_url}&TurnOffAutomaticMode=true",
                    "-H", "accept: */*"
                ]
                subprocess.run(cmd)
                time.sleep(int(video['time']))

        is_playing = False  # Setze is_playing auf False, wenn die Wiedergabe beendet ist

    playback_thread = threading.Thread(target=play_thread, daemon=True)
    playback_thread.start()
    return jsonify({"status": "playing"})

@app.route('/stop', methods=['POST'])
def stop_playback():
    global is_playing
    is_playing = False  # Stoppe die Wiedergabe

    # Optional: Stelle sicher, dass keine weiteren Videos mehr abgespielt werden
    subprocess.run(["curl", "-X", "GET", "http://localhost:5000/api/PlaylistAPI/GoNext", "-H", "accept: */*"])
    subprocess.run(["curl", "-X", "POST", "http://localhost:5000/api/AppSettingAPI/SetAppSetting?name=AutomaticMode&value=true", "-H", "accept: */*", "-d", ""])

    return jsonify({"status": "stopped"})

@app.route('/edit-urls', methods=['GET', 'POST'])
def edit_urls():
    if request.method == 'POST':
        data = request.get_json()  # Hole die JSON-Daten der Anfrage
        if 'delete' in data:
            urls_to_delete = data['delete']  # Liste der zu löschenden URLs
            urls = load_urls()
            urls = [url for url in urls if url not in urls_to_delete]  # Entferne die URLs
            save_urls(urls)  # Speichere die aktualisierte URL-Liste

        if 'new-url' in data:
            new_url = data['new-url']
            urls = load_urls()
            if new_url and new_url not in urls:
                urls.append(new_url)  # Füge die neue URL hinzu
                save_urls(urls)  # Speichere die aktualisierte URL-Liste

        return jsonify({"status": "success"})

    # GET-Methode: Lade URLs und übergebe sie an das Template
    urls = load_urls()
    return render_template('edit_urls.html', urls=urls)

def save_urls(urls):
    try:
        with open(VIDEO_URLS_FILE, 'w') as file:
            for url in urls:
                file.write(url + "\n")
    except Exception as e:
        print(f"Fehler beim Speichern der URLs: {e}")  # Fehlerprotokollierung

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

from flask import Flask, render_template, request, jsonify
import yt_dlp
import threading
import time
import subprocess
import urllib.parse
import os

app = Flask(__name__)
VIDEO_URLS_FILE = "video-urls.txt"  # Pfad zur Datei mit den URLs
selected_videos = []

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

# Funktion zum Speichern der URLs
def save_urls(urls):
    try:
        with open(VIDEO_URLS_FILE, 'w') as file:
            for url in urls:
                file.write(url + '\n')
    except Exception as e:
        print(f"Fehler beim Speichern der URLs: {e}")  # Fehlerprotokollierung

# Funktion zum Abrufen des Titels eines Videos
def get_video_title(url):
    try:
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
    return jsonify({"status": "success"})

@app.route('/play', methods=['POST'])
def play_videos():
    def play_thread():
        while True:
            if not selected_videos:
                break
            
            for video in selected_videos:
                encoded_url = urllib.parse.quote(video['url'], safe='')
                cmd = [
                    "curl", "-X", "GET",
                    f"http://localhost:5000/api/PlayFileAPI/PlayFullDirectVideoUrl?URL={encoded_url}&TurnOffAutomaticMode=true",
                    "-H", "accept: */*"
                ]
                subprocess.run(cmd)
                time.sleep(int(video['time']))
    
    threading.Thread(target=play_thread, daemon=True).start()
    return jsonify({"status": "playing"})

@app.route('/stop', methods=['POST'])
def stop_playback():
    subprocess.run(["curl", "-X", "GET", "http://localhost:5000/api/PlaylistAPI/GoNext", "-H", "accept: */*"])
    subprocess.run(["curl", "-X", "POST", "http://localhost:5000/api/AppSettingAPI/SetAppSetting?name=AutomaticMode&value=true", "-H", "accept: */*", "-d", ""])  
    return jsonify({"status": "stopped"})

# Neue Route zum Bearbeiten der URLs
@app.route('/edit-urls', methods=['GET', 'POST'])
def edit_urls():
    if request.method == 'POST':
        # Verarbeite die POST-Daten wie gehabt
        data = request.get_json()  # Hole die JSON-Daten der Anfrage
        if 'delete' in data:
            urls_to_delete = data['delete']  # Liste der zu löschenden URLs
            urls = load_urls()
            urls = [url for url in urls if url not in urls_to_delete]  # Entferne die URLs
            save_urls(urls)  # Speichere die aktualisierte URL-Liste

        # Neue URL hinzufügen (falls vorhanden)
        if 'new-url' in data:
            new_url = data['new-url']
            urls = load_urls()
            if new_url and new_url not in urls:
                urls.append(new_url)
                save_urls(urls)

        return jsonify({"status": "success"})

    # Nach der Bearbeitung die URLs neu laden
    urls = load_urls()
    return render_template('edit_urls.html', urls=urls)  # URLs ans Template übergeben

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

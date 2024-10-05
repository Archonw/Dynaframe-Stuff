from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import requests  # Library to send HTTP requests

app = Flask(__name__)

# Funktion zur Ermittlung der lokalen IP-Adresse über ein Bash-Skript
def get_local_ip():
    try:
        result = subprocess.run(['bash', '-c', "ip addr show | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | cut -d'/' -f1"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "127.0.0.1"  # Fallback auf localhost bei Fehlern

# Funktion zum Ersetzen der IP-Adresse in der index.html
def update_index_html_with_ip():
    ip_address = get_local_ip()  # Lokale IP-Adresse ermitteln
    index_file_path = '/home/pi/Dynaframe/Assets/dfplugins/share-config/index.html'
    
    # Aktuellen Inhalt der index.html laden
    with open(index_file_path, 'r') as file:
        content = file.read()

    # Suche nach dem bestehenden IP-Abschnitt und ersetze ihn durch die aktuelle IP
    new_content = content.replace(content[content.find('//')+2:content.find(':5000')], ip_address)

    # Neuen Inhalt in die Datei schreiben
    with open(index_file_path, 'w') as file:
        file.write(new_content)
    
    print(f"Updated index.html with IP address: {ip_address}")

# Route to serve the main HTML page
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')  # Ensure index.html is in the same directory as the script

# Function to get currently mounted SMB/NFS shares
def get_mounted_shares():
    mounted_shares = []
    with open('/proc/mounts', 'r') as mounts:
        for line in mounts:
            parts = line.split()
            mount_path = parts[1]
            share_path = parts[0]
            fs_type = parts[2]  # Dateisystemtyp (z. B. nfs, cifs)

            # Filter nur SMB und NFS Shares
            if 'cifs' in fs_type or 'nfs' in fs_type:
                share_type = 'smb' if 'cifs' in fs_type else 'nfs'
                mounted_shares.append({
                    'sharePath': share_path,
                    'mountPath': mount_path,
                    'shareType': share_type  # Füge den ShareType hinzu
                })
    return mounted_shares

# Function to add mount path using external HTTP request
def add_directory_via_http(mount_directory):
    full_mount_path = f"/home/pi/{mount_directory}"
    url = f"http://127.0.0.1/command/?COMMAND=ADDROOTDIRECTORY&VALUE={full_mount_path}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Successfully added directory {full_mount_path} via HTTP")
        else:
            print(f"Failed to add directory {full_mount_path} via HTTP. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error adding directory via HTTP: {e}")

# Function to remove mount path using external HTTP request
def remove_directory_via_http(mount_directory):
    full_mount_path = f"/home/pi/{mount_directory}"
    url = f"http://127.0.0.1/command/?COMMAND=REMOVEROOTDIRECTORY&VALUE={full_mount_path}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Successfully removed directory {full_mount_path} via HTTP")
        else:
            print(f"Failed to remove directory {full_mount_path} via HTTP. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error removing directory via HTTP: {e}")

# Route to get mounted shares
@app.route('/mounted-shares', methods=['GET'])
def mounted_shares():
    try:
        shares = get_mounted_shares()
        return jsonify(shares), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to unmount a share
@app.route('/unmount-share', methods=['POST'])
def unmount_share():
    data = request.get_json()
    mount_path = data.get('mountPath')

    try:
        # Unmount the share
        subprocess.run(['sudo', 'umount', mount_path], check=True)

        # Remove the corresponding entry from /etc/fstab
        with open('/etc/fstab', 'r') as fstab:
            lines = fstab.readlines()

        with open('/etc/fstab', 'w') as fstab:
            for line in lines:
                # Only write lines that don't match the mount path
                if mount_path not in line:
                    fstab.write(line)

        # Remove the mount directory if it exists
        if os.path.exists(mount_path):
            os.rmdir(mount_path)

        # Remove from appsettings.json via HTTP request
        remove_directory_via_http(mount_path.replace("/home/pi/", ""))

        return jsonify({"message": "Share unmounted, directory removed, and fstab entry deleted"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route to mount a share
@app.route('/mount-share', methods=['POST'])
def mount_share():
    data = request.get_json()
    share_path = data.get('sharePath')
    mount_directory = data.get('mountPath')  # User provides only the directory name
    share_type = data.get('shareType', '').lower()  # Konvertiere zu Kleinbuchstaben
    username = data.get('username')
    password = data.get('password')

    if share_type not in ['nfs', 'smb']:
        return jsonify({"error": "Invalid or missing shareType. Must be 'nfs' or 'smb'."}), 400

    try:
        # Ensure the mount directory exists
        full_mount_path = f"/home/pi/{mount_directory}"
        if not os.path.exists(full_mount_path):
            os.makedirs(full_mount_path)

        # Construct the mount command based on share type
        mount_cmd = []
        if share_type == "nfs":
            mount_cmd = ['sudo', 'mount', '-t', 'nfs', share_path, full_mount_path]
        elif share_type == "smb":
            mount_cmd = ['sudo', 'mount', '-t', 'cifs', share_path, full_mount_path]
            if username and password:
                mount_cmd += ['-o', f"username={username},password={password}"]

        # Attempt to mount the share
        subprocess.run(mount_cmd, check=True)

        # Only after successful mount, write to /etc/fstab
        fstab_line = ""
        if share_type == "nfs":
            fstab_line = f"{share_path} {full_mount_path} nfs defaults 0 0\n"
        elif share_type == "smb":
            if username and password:
                fstab_line = f"//{share_path} {full_mount_path} cifs username={username},password={password},defaults 0 0\n"
            else:
                fstab_line = f"//{share_path} {full_mount_path} cifs defaults 0 0\n"

        with open('/etc/fstab', 'a') as fstab:
            fstab.write(fstab_line)

        # Add to appsettings.json via HTTP request
        add_directory_via_http(mount_directory)

        return jsonify({"message": "Share mounted successfully!"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve static files (e.g., CSS, JavaScript)
@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory('assets', filename)

if __name__ == "__main__":
    update_index_html_with_ip()  # IP-Adresse beim Start aktualisieren
    app.run(host='0.0.0.0', port=5000)


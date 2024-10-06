from flask import Flask, request, jsonify, send_from_directory
import subprocess
import os
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Serve the index.html file
@app.route('/')
def index():
    return send_from_directory('/home/pi/Dynaframe/Assets/dfplugins/fixedip', 'index.html')

# Serve static JavaScript files
@app.route('/assets/js/<path:path>')
def send_js(path):
    return send_from_directory('/home/pi/Dynaframe/Assets/js', path)

def get_interface_config(interface):
    """ Get current IP configuration of the given interface """
    try:
        result = subprocess.run(f"ifconfig {interface}", shell=True, check=True, stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        # Extract IP address, netmask, and gateway from the ifconfig output
        ip, netmask = None, None
        for line in output.split('\n'):
            if 'inet ' in line and not 'inet6' in line:  # Get IPv4 address
                parts = line.split()
                ip = parts[1]
                netmask = parts[3]  # Subnet mask

        # Get default gateway (route -n can be used to find it)
        result = subprocess.run("route -n", shell=True, stdout=subprocess.PIPE)
        route_output = result.stdout.decode('utf-8')
        gateway = None
        for line in route_output.split('\n'):
            if line.startswith('0.0.0.0') and interface in line:
                gateway = line.split()[1]

        # DNS (from /etc/resolv.conf)
        dns = None
        with open('/etc/resolv.conf', 'r') as dns_file:
            for line in dns_file:
                if line.startswith('nameserver'):
                    dns = line.split()[1]
                    break

        return {"ip": ip, "netmask": netmask, "gateway": gateway, "dns": dns}
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting interface config for {interface}: {e}")
        return None

def is_dhcp_active(interface):
    """ Check if DHCP is active for the given interface """
    try:
        with open(f"/etc/dhcpcd.conf", 'r') as dhcp_conf:
            dhcp_active = f"interface {interface}" not in dhcp_conf.read()
        return dhcp_active
    except FileNotFoundError:
        logging.error(f"DHCPCD config file not found")
        return False

@app.route('/get_ip_settings', methods=['GET'])
def get_ip_settings():
    eth0_config = get_interface_config('eth0')
    wlan0_config = get_interface_config('wlan0')

    # Check if DHCP is active for eth0 and wlan0
    dhcp_active_eth0 = is_dhcp_active('eth0')
    dhcp_active_wlan0 = is_dhcp_active('wlan0')

    return jsonify({
        'eth0': eth0_config,
        'wlan0': wlan0_config,
        'dhcp_active_eth0': dhcp_active_eth0,
        'dhcp_active_wlan0': dhcp_active_wlan0
    })

@app.route('/set_ip', methods=['POST'])
def set_ip():
    data = request.json
    interface = data.get('interface')
    ip = data.get('ip')
    netmask = data.get('netmask')
    gateway = data.get('gateway')
    dns = data.get('dns')
    use_dhcp = data.get('useDHCP', False)

    dhcp_conf_path = "/etc/dhcpcd.conf"

    try:
        if use_dhcp:
            # Remove static IP configuration for the specific interface from /etc/dhcpcd.conf
            with open(dhcp_conf_path, "r") as file:
                lines = file.readlines()
            with open(dhcp_conf_path, "w") as file:
                inside_interface_block = False
                for line in lines:
                    if line.strip() == f"interface {interface}":
                        inside_interface_block = True
                    elif inside_interface_block and line.startswith("static "):
                        continue  # Skip static IP configuration for this interface
                    else:
                        inside_interface_block = False
                        file.write(line)

            subprocess.run("sudo systemctl restart dhcpcd", shell=True, check=True)
            return jsonify({"message": f"Switched {interface} to DHCP successfully"}), 200

        else:
            # Validate IP address and netmask format before writing to config
            if not validate_ip(ip) or not validate_netmask(netmask):
                return jsonify({"error": "Invalid IP address or netmask format"}), 400

            # Add or modify static IP configuration for the specific interface in /etc/dhcpcd.conf
            with open(dhcp_conf_path, "r") as file:
                lines = file.readlines()
            with open(dhcp_conf_path, "w") as file:
                interface_found = False
                for line in lines:
                    file.write(line)
                    if line.strip() == f"interface {interface}":
                        interface_found = True
                        file.write(f"static ip_address={ip}/{netmask}\n")
                        file.write(f"static routers={gateway}\n")
                        file.write(f"static domain_name_servers={dns}\n")

                if not interface_found:
                    file.write(f"\ninterface {interface}\n")
                    file.write(f"static ip_address={ip}/{netmask}\n")
                    file.write(f"static routers={gateway}\n")
                    file.write(f"static domain_name_servers={dns}\n")

            subprocess.run("sudo systemctl restart dhcpcd", shell=True, check=True)
            return jsonify({"message": f"Static IP settings for {interface} applied successfully"}), 200

    except subprocess.CalledProcessError as e:
        logging.error(f"Error setting IP for {interface}: {e}")
        return jsonify({"error": str(e)}), 500

def validate_ip(ip):
    """ Validate IP address format """
    parts = ip.split('.')
    return len(parts) == 4 and all(part.isdigit() and 0 <= int(part) < 256 for part in parts)

def validate_netmask(netmask):
    """ Validate netmask format """
    try:
        int(netmask)  # Check if it's an integer
        return 0 <= int(netmask) <= 32  # Typical netmask range
    except ValueError:
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5010)


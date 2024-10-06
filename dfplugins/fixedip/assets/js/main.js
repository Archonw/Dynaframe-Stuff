document.addEventListener('DOMContentLoaded', function () {
    // Fetch current IP settings when the page is loaded
    fetch('/get_ip_settings')
        .then(response => response.json())
        .then(data => {
            // Get current settings for both eth0 and wlan0
            const eth0 = data.eth0;
            const wlan0 = data.wlan0;

            // Set eth0 settings initially
            if (eth0) {
                document.getElementById('eth0-ip').value = eth0.ip || '';
                document.getElementById('eth0-netmask').value = eth0.netmask || '';
                document.getElementById('eth0-gateway').value = eth0.gateway || '';
                document.getElementById('eth0-dns').value = eth0.dns || '';
            }

            // Set wlan0 settings initially
            if (wlan0) {
                document.getElementById('wlan0-ip').value = wlan0.ip || '';
                document.getElementById('wlan0-netmask').value = wlan0.netmask || '';
                document.getElementById('wlan0-gateway').value = wlan0.gateway || '';
                document.getElementById('wlan0-dns').value = wlan0.dns || '';
            }
        });
});

function submitIPSettings() {
    // Get values from the form
    const eth0_ip = document.getElementById('eth0-ip').value;
    const eth0_netmask = document.getElementById('eth0-netmask').value;
    const eth0_gateway = document.getElementById('eth0-gateway').value;
    const eth0_dns = document.getElementById('eth0-dns').value;

    const wlan0_ip = document.getElementById('wlan0-ip').value;
    const wlan0_netmask = document.getElementById('wlan0-netmask').value;
    const wlan0_gateway = document.getElementById('wlan0-gateway').value;
    const wlan0_dns = document.getElementById('wlan0-dns').value;

    // Prepare the data for eth0
    const eth0Data = {
        interface: 'eth0',
        ip: eth0_ip,
        netmask: eth0_netmask,
        gateway: eth0_gateway,
        dns: eth0_dns
    };

    // Send POST request to update eth0 settings
    fetch('/set_ip', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(eth0Data)
    }).then(response => response.json())
      .then(data => console.log('Eth0 settings updated:', data))
      .catch(error => console.error('Error updating eth0 settings:', error));

    // Prepare the data for wlan0
    const wlan0Data = {
        interface: 'wlan0',
        ip: wlan0_ip,
        netmask: wlan0_netmask,
        gateway: wlan0_gateway,
        dns: wlan0_dns
    };

    // Send POST request to update wlan0 settings
    fetch('/set_ip', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(wlan0Data)
    }).then(response => response.json())
      .then(data => console.log('Wlan0 settings updated:', data))
      .catch(error => console.error('Error updating wlan0 settings:', error));
}


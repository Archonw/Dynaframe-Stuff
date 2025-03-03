#!/bin/bash
# hide mouse in wayland raspbian

sudo apt install -y interception-tools interception-tools-compat
sudo apt install -y cmake
cd ~
git clone https://gitlab.com/interception/linux/plugins/hideaway.git
cd hideaway
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
sudo cp /home/pi/hideaway/build/hideaway /usr/bin
sudo chmod +x /usr/bin/hideaway

cd ~
wget https://raw.githubusercontent.com/ugotapi/wayland-pagepi/main/config.yaml
sudo cp /home/pi/config.yaml /etc/interception/udevmon.d/config.yaml
sudo systemctl restart udevmon

# Cronjob hinzufügen, falls nicht schon vorhanden
if ! sudo crontab -l 2>/dev/null | grep -q "@reboot systemctl restart udevmon"; then
    (sudo crontab -l 2>/dev/null; echo "@reboot systemctl restart udevmon") | sudo crontab -
fi

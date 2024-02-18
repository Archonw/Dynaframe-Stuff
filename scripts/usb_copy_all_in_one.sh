
#!/bin/bash

log_message() {
    echo "$(date "+%F %T"): $1" >> /tmp/usb_copy_all_in_one.log
}

log_message "Script is being executed"

# Destination directory for the pictures from the USB stick
destination_dir="/home/pi/Pictures/Stick"

# Check if a USB stick is connected and if files are present
if [ "$(sudo /usr/bin/ls -A /media/pi/ 2>/dev/null)" ]; then
    log_message "USB stick detected and files found"

    # Copy new files from the USB stick to the destination directory
    rsync -av --ignore-existing /media/pi/ "$destination_dir"

    # Optional: Print a success message
    log_message "New files successfully copied to $destination_dir"

    # Unmount the USB stick
    umount /media/pi/*
    log_message "USB stick successfully ejected"

sleep 10

# Aufrufen der ersten URL
curl -s "http://127.0.0.1/command/?COMMAND=SELECTOVERLAY&VALUE=usb_copy.json" >/dev/null

# Aufrufen der zweiten URL
curl -s "http://127.0.0.1/command/?COMMAND=EnableOverlay&VALUE=true" >/dev/null

log_message "URLs successfully called"

sleep 10

curl -s "http://127.0.0.1/command/?COMMAND=EnableOverlay&VALUE=false" >/dev/null

else
    log_message "No USB stick found or no new files present"
fi


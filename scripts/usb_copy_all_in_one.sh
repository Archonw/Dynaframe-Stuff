#!/bin/bash


# Destination directory for the pictures from the USB stick
destination_dir="/home/pi/Pictures/Stick"

log_message() {
    echo "$(date "+%F %T"): $1" >> /tmp/usb_copy_all_in_one.log
}

log_message "Script is being executed"

# Lock-file
lock_file="/tmp/usb_copy.lock"

# Verify that the lock file exists
if [ -f "$lock_file" ]; then
    echo "Script is already running. Exiting."
    exit 1
fi

# Creating the lock file
touch "$lock_file"



# Check if usb_copy.json exists, if not, create it
overlay_file="/home/pi/Dynaframe/Assets/Overlays/usb_copy.json"
if [ ! -f "$overlay_file" ]; then
    log_message "Creating usb_copy.json overlay file"
    cat <<EOF > "$overlay_file"
[
  {
    "OverlayControlName": "SimpleText",
    "Id": "0",
    "JSONFile": "$overlay_file",
    "Settings": {
      "FRIENDLYNAME": "usb_copy_finished",
      "FADEBETWEENIMAGES": "false",
      "SIMPLETEXTVALUE": "copy done",
      "FOREGROUNDOPACITY": "1",
      "FONTSIZE": "100",
      "FOREGROUNDCOLOR": "#ffffff",
      "BACKGROUNDCOLOR": "#FF0000",
      "CLOCKTIMEFORMAT": "hh:mm:ss dddd, dd MMMM yyyy",
      "TEXTPREFIX": "",
      "TEXTPOSTFIX": "",
      "BACKGROUNDMARGINRIGHT": "0",
      "BACKGROUNDMARGINBOTTOM": "0",
      "BACKGROUNDHORIZONTALALIGNMENT": "Center",
      "BACKGROUNDVERTICALALIGNMENT": "Center",
      "HORIZONTALALIGNMENT": "Right",
      "VERTICALALIGNMENT": "Top",
      "FOREGROUNDFONTFAMILY": "Arial",
      "MARGINTOP": "0",
      "MARGINLEFT": "0",
      "MARGINRIGHT": "0",
      "MARGINBOTTOM": "0",
      "BACKGROUNDMARGINTOP": "0",
      "BACKGROUNDMARGINLEFT": "0",
      "ENABLEBACKGROUND": "false",
      "BACKGROUNDFONTSIZE": "50",
      "BACKGROUNDFONTFAMILY": "Arial",
      "BACKGROUNDOFFSETX": "3",
      "BACKGROUNDOFFSETY": "3",
      "PADDINGLEFT": "0",
      "PADDINGRIGHT": "0",
      "PADDINGTOP": "0",
      "PADDINGBOTTOM": "0",
      "BACKGROUNDOPACITY": "0"
    }
  }
]
EOF
    log_message "usb_copy.json created successfully"
fi

# Continue with the rest of the script

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

    # Read current overlay values from appsettings.json
    default_overlay=$(jq -r '.DefaultOverlay' /home/pi/Dynaframe/appsettings.json)
    enable_overlay=$(jq -r '.EnableOverlay' /home/pi/Dynaframe/appsettings.json)

    log_message "Read values from appsettings.json: DefaultOverlay=$default_overlay, EnableOverlay=$enable_overlay"

    sleep 3

    # set copy done overlay
    curl -s "http://127.0.0.1/command/?COMMAND=SELECTOVERLAY&VALUE=usb_copy.json" >/dev/null

    # activate copy done overlay
    curl -s "http://127.0.0.1/command/?COMMAND=EnableOverlay&VALUE=true" >/dev/null

    log_message "URLs successfully called"

    sleep 15

#    if [ "$enable_overlay" = "true" ]; then
        # set last overlay with values from appsettings.json
        curl -s "http://127.0.0.1/command/?COMMAND=SELECTOVERLAY&VALUE=$default_overlay" >/dev/null

        # set last overlay status with the value from EnableOverlay
        curl -s "http://127.0.0.1/command/?COMMAND=EnableOverlay&VALUE=$enable_overlay" >/dev/null

        log_message "URLs successfully called with values from appsettings.json"
#    fi
else
    log_message "No USB stick found or no new files present"
fi

# Remove the lock-file
rm "$lock_file"

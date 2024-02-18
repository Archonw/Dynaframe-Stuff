#!/bin/bash


# Directory for the the New_Files_ folder
pictures_dir="/home/pi/Pictures"



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
fi


# Check if a USB stick is connected and if files are present
if [ "$(sudo /usr/bin/ls -A /media/pi/ 2>/dev/null)" ]; then

    # Find the latest directory
    latest_dir=$(ls -d $pictures_dir/New_Files_* 2>/dev/null | tail -n 1)
    if [ -z "$latest_dir" ]; then
        latest_num=0
    else
        latest_num=$(echo "$latest_dir" | grep -o '[0-9]*$')
    fi

    # Increment the number for the new directory
    new_num=$((latest_num + 1))

    # Create a new directory
    new_dir="$pictures_dir/New_Files_$new_num"
    mkdir -p "$new_dir"

    # Copy files from the USB stick to the new directory
    cp -r /media/pi/* "$new_dir"


    # Unmount the USB stick
    umount /media/pi/*

    # Read current overlay values from appsettings.json
    default_overlay=$(jq -r '.DefaultOverlay' /home/pi/Dynaframe/appsettings.json)
    enable_overlay=$(jq -r '.EnableOverlay' /home/pi/Dynaframe/appsettings.json)


    sleep 10

    # set copy done overlay
    curl -s "http://127.0.0.1/command/?COMMAND=SELECTOVERLAY&VALUE=usb_copy.json" >/dev/null

    # activate copy done overlay
    curl -s "http://127.0.0.1/command/?COMMAND=EnableOverlay&VALUE=true" >/dev/null


    sleep 10

    # set last overlay with values from appsettings.json
    curl -s "http://127.0.0.1/command/?COMMAND=SELECTOVERLAY&VALUE=$default_overlay" >/dev/null

    # set last overlay status with the value from EnableOverlay
    curl -s "http://127.0.0.1/command/?COMMAND=EnableOverlay&VALUE=$enable_overlay" >/dev/null

fi

# Remove the lock-file
rm "$lock_file"

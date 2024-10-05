document.addEventListener('DOMContentLoaded', function () {
    UpdateTimeChart();
    loadPlaylists();
});

function UpdateTimeChart() {
    console.log("Updating time chart");
    fetch('schedule.json', {cache: "no-store"})
        .then(response => response.json())
        .then(data => {
            displayJsonContent(data);
        })
        .catch(error => console.error('Error loading JSON file:', error));
}

function displayJsonContent(data) {
    var jsonTable = document.getElementById('json-table');
    var tbody = jsonTable.querySelector('tbody');
    tbody.innerHTML = '';

    data.forEach((entry) => {
        var row = tbody.insertRow();
        var timeCell = row.insertCell(0);
        var commandCell = row.insertCell(1);
        var parameterCell = row.insertCell(2);
        var deleteCell = row.insertCell(3);  // Cell for delete button

        timeCell.textContent = entry.time;
        commandCell.textContent = entry.command;
        parameterCell.textContent = entry.parameter;

        // Create delete button
        var deleteButton = document.createElement('button');
        deleteButton.textContent = 'Delete';
        deleteButton.className = 'btn btn-danger';
        deleteButton.addEventListener('click', function () {
            deleteEntry(entry.time, entry.command, entry.parameter); // Pass details instead of index
        });
        deleteCell.appendChild(deleteButton);
    });
}

function deleteEntry(time, command, parameter) {
    fetch('schedule.json', {cache: "no-store"})
        .then(response => response.json())
        .then(data => {
            // Find the entry that matches time, command, and parameter
            const updatedData = data.filter(entry => 
                !(entry.time === time && entry.command === command && entry.parameter === parameter)
            );

            // Send the updated data back to the server (or save it locally)
            fetch('save-schedule', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedData),
            })
            .then(response => response.text())
            .then(() => {
                UpdateTimeChart(); // Refresh the table after deletion
            })
            .catch(error => console.error('Error saving updated schedule:', error));
        })
        .catch(error => console.error('Error loading schedule for deletion:', error));
}


function sendMessage(url) {
    fetch(url, {
        method: 'GET'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.text();
    })
    .then(data => {
        console.log('Server response:', data);
        sleep(250).then(() => { 
            UpdateTimeChart(); 
            console.log("Updated chart from sendmessage");
        });
    })
    .catch(error => {
        console.error('Error during fetch:', error);
    });
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function addTime() {
    var timeInputValue = document.getElementById('timeInput').value;
    var commandParamValue = document.getElementById('commandandparam').value;
    
    var url = 'index.html';
    url += '?timeInput=' + encodeURIComponent(timeInputValue);
    url += '&action=command';
    url += '&commandandparam=' + encodeURIComponent(commandParamValue);
    sendMessage(url);
}

function addPlaylist() {
    var timeInputValue = document.getElementById('playlistTimeInput').value;
    var playlistValue = document.getElementById('playlistSelect').value;
    
    var url = 'index.html';
    url += '?timeInput=' + encodeURIComponent(timeInputValue);
    url += '&action=command';
    url += '&commandandparam=SETSUBDIRECTORIES,' + encodeURIComponent(playlistValue);
    sendMessage(url);
}

function clearTime() {
    var url = 'index.html';
    url += '?timeInput=12:00&action=command&commandandparam=clear,clear';
    sendMessage(url);
}

function loadPlaylists() {
    fetch('http://192.168.178.58/command/?COMMAND=GETSTRINGSUBDIRECTORIES&VALUE')
        .then(response => response.text())
        .then(data => {
            let playlists = data.split(';').map(item => {
                const [name, path, isDefault] = item.split(',');
                return { name, path };
            });

            // Check and remove "SUBDIRS_" from the first playlist if it exists
            if (playlists.length > 0 && playlists[0].name.startsWith("SUBDIRS_")) {
                playlists[0].name = playlists[0].name.replace("SUBDIRS_", "");
            }

            // Clear existing options in the playlist select dropdown
            const select = document.getElementById('playlistSelect');
            select.innerHTML = ""; // Clear out any previous options

            // Populate the dropdown with the updated playlist names
            playlists.forEach(playlist => {
                const option = document.createElement('option');
                option.value = playlist.path;
                option.textContent = playlist.name;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading playlists:', error));
}

document.getElementById('clearButton').addEventListener('click', clearTime);
document.getElementById('addTime').addEventListener('click', addTime);
document.getElementById('addPlaylist').addEventListener('click', addPlaylist);


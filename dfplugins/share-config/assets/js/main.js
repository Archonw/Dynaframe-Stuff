document.addEventListener('DOMContentLoaded', function () {
    // Fetch the JSON file
    UpdateTimeChart();
});

function UpdateTimeChart()
{
    console.log("Updating time chart");
     fetch('schedule.json', {cache: "no-store"})
        .then(response => response.json())
        .then(data => {
            // Display the JSON content in a table            
            displayJsonContent(data);
        })
        .catch(error => console.error('Error loading JSON file:', error));
    
}

function displayJsonContent(data) {
    // Assuming you want to display the content in a table with the id "json-table"
    var jsonTable = document.getElementById('json-table');
    var tbody = jsonTable.querySelector('tbody');

    // Clear existing rows from the table
    tbody.innerHTML = '';

    // Iterate through the JSON data and create a row for each entry
    data.forEach(entry => {
        var row = tbody.insertRow();
        var timeCell = row.insertCell(0);
        var commandCell = row.insertCell(1);
        var parameterCell = row.insertCell(2);

        // Set the content of each cell
        timeCell.textContent = entry.time;
        commandCell.textContent = entry.command;
        parameterCell.textContent = entry.parameter;
    });
}
function sendMessage(url)
{
            // Send an asynchronous HTTP GET request
        fetch(url, {
            method: 'GET'
        })
        .then(response => {
            // Check if the request was successful
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            // Process the response
            return response.text();
        })
        .then(data => {
            // Handle the data received from the server
            console.log('Server response:', data);
            // 'true' here prevents loading a cached page...
            sleep(250).then(() => { 
                UpdateTimeChart(); 
                console.log("Updated chart from sendmessage");
            });
            
            //window.location.href=window.location.href
        })
        .catch(error => {
            // Handle errors during the fetch
            console.error('Error during fetch:', error);
        });
    
}
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

function addTime() {
    // Get values from input fields
    var timeInputValue = document.getElementById('timeInput').value;
    var commandParamValue = document.getElementById('commandandparam').value;
    

    // Construct the URL with parameters
    var url = '/dfplugins/scheduler/index.html';
    url += '?timeInput=' + encodeURIComponent(timeInputValue);
    url += '&action=command';
    url += '&commandandparam=' + encodeURIComponent(commandParamValue);
    sendMessage(url);

}

function clearTime()
{
    var url = '/dfplugins/scheduler/index.html';
    url    += '?timeInput=12:00&action=command&commandandparam=clear,clear';
    sendMessage(url);
}

document.getElementById('clearButton').addEventListener('click', clearTime);
document.getElementById('addTime').addEventListener('click', addTime);


const API_BASE = 'http://localhost:10000';

async function apiCall(endpoint, method = 'GET', body = null) {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API call failed:', error);
        return { error: error.message };
    }
}

async function getInterfaceStatus() {
    const data = await apiCall('/interface?interface_name=wlan0');
    document.getElementById('interface-status').textContent = JSON.stringify(data, null, 2);
}

async function scanNetworks() {
    const networksDiv = document.getElementById('networks-list');
    networksDiv.innerHTML = '<p>Scanning...</p>';
    
    const data = await apiCall('/scan_wifi?interface_name=wlan0');
    
    if (data.error) {
        networksDiv.innerHTML = `<p>Error: ${data.error}</p>`;
        return;
    }
    
    if (data.length === 0) {
        networksDiv.innerHTML = '<p>No networks found</p>';
        return;
    }
    
    let html = '<h3>Available Networks:</h3>';
    data.forEach(network => {
        html += `
            <div onclick="fillSSID('${network.ssid}')" style="cursor: pointer; border: 1px solid #ccc; padding: 10px; margin: 5px;">
                <strong>${network.ssid}</strong><br>
                Signal: ${network.signal}dBm<br>
                Security: ${network.auth}<br>
                BSSID: ${network.bssid}
            </div>
        `;
    });
    networksDiv.innerHTML = html;
}

function fillSSID(ssid) {
    document.getElementById('ssid').value = ssid;
}

async function connectToNetwork(event) {
    event.preventDefault();
    
    const ssid = document.getElementById('ssid').value;
    const password = document.getElementById('password').value;
    const interface_name = document.getElementById('interface').value;
    
    const resultDiv = document.getElementById('connection-result');
    resultDiv.innerHTML = '<p>Connecting...</p>';
    
    const data = await apiCall('/connect_wifi', 'POST', {
        ssid,
        password,
        interface_name
    });
    
    if (data.connected) {
        resultDiv.innerHTML = `<p style="color: green;">Successfully connected to ${ssid}</p>`;
        // Auto-refresh status after connection
        setTimeout(getInterfaceStatus, 2000);
    } else {
        resultDiv.innerHTML = `<p style="color: red;">Failed to connect to ${ssid}</p>`;
    }
}

async function getCurrentWifi() {
    const data = await apiCall('/current_wifi');
    document.getElementById('current-wifi').textContent = JSON.stringify(data, null, 2);
}

// Auto-load interface status on page load
window.onload = function() {
    getInterfaceStatus();
};
const API_BASE = `http://${window.location.hostname}:10000`;
let availableNetworks = [];
let selectedInterface = 'wlan0';

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

async function loadInterfaces() {
    const interfaceSelect = document.getElementById('interface-select');
    const interfaceForm = document.getElementById('interface');
    
    // Show loading state
    interfaceSelect.innerHTML = '<option value="">Loading interfaces...</option>';
    
    try {
        const data = await apiCall('/interfaces');
        console.log('Interfaces data:', data); // Debug log
        
        if (data.error) {
            console.error('Interface loading error:', data.error);
            interfaceSelect.innerHTML = '<option value="">Error loading interfaces</option>';
            return;
        }
        
        if (Array.isArray(data) && data.length > 0) {
            interfaceSelect.innerHTML = '';
            interfaceForm.innerHTML = '';
            
            data.forEach(iface => {
                // Handle both string and object interfaces
                const ifaceName = typeof iface === 'string' ? iface : iface.name || iface.interface || JSON.stringify(iface);
                
                const option = document.createElement('option');
                option.value = ifaceName;
                option.textContent = ifaceName;
                interfaceSelect.appendChild(option);
                
                const formOption = document.createElement('option');
                formOption.value = ifaceName;
                formOption.textContent = ifaceName;
                interfaceForm.appendChild(formOption);
            });
            
            selectedInterface = typeof data[0] === 'string' ? data[0] : data[0].name || data[0].interface || 'wlan0';
            interfaceSelect.value = selectedInterface;
            interfaceForm.value = selectedInterface;
        } else {
            console.log('No interfaces found, using default wlan0');
            interfaceSelect.innerHTML = '<option value="wlan0">wlan0</option>';
            interfaceForm.innerHTML = '<option value="wlan0">wlan0</option>';
            selectedInterface = 'wlan0';
        }
    } catch (error) {
        console.error('Failed to load interfaces:', error);
        interfaceSelect.innerHTML = '<option value="wlan0">wlan0 (fallback)</option>';
        interfaceForm.innerHTML = '<option value="wlan0">wlan0 (fallback)</option>';
        selectedInterface = 'wlan0';
    }
}

function onInterfaceChange() {
    const interfaceSelect = document.getElementById('interface-select');
    selectedInterface = interfaceSelect.value;
    document.getElementById('interface').value = selectedInterface;
    // Clear current data
    document.getElementById('interface-status').innerHTML = '<div class="status-placeholder">Click "Refresh Status" to load interface details...</div>';
    document.getElementById('networks-list').innerHTML = '<div class="status-placeholder">Click "Scan Networks" to discover available WiFi networks...</div>';
}

async function getInterfaceStatus() {
    const statusDiv = document.getElementById('interface-status');
    statusDiv.innerHTML = '<div class="loading"><i data-lucide="loader-2"></i> Loading interface status...</div>';
    lucide.createIcons();
    
    const data = await apiCall(`/interface?interface_name=${selectedInterface}`);
    
    if (data.error) {
        statusDiv.innerHTML = `<div class="result-error"><i data-lucide="x-circle"></i> Error: ${data.error}</div>`;
        lucide.createIcons();
        return;
    }
    
    statusDiv.innerHTML = createInterfaceStatusDisplay(data);
    lucide.createIcons();
}

function createInterfaceStatusDisplay(data) {
    console.log('Interface data:', data); // Debug log
    
    let statusItems = [
        {
            icon: 'network',
            label: 'Interface',
            value: data.name || selectedInterface
        },
        {
            icon: 'activity',
            label: 'Status',
            value: data.status || 'Unknown'
        },
        {
            icon: 'globe',
            label: 'IP Address',
            value: data.ip_address || 'Not assigned'
        }
    ];
    
    // Add MAC address if available
    if (data.mac_address) {
        statusItems.push({
            icon: 'hash',
            label: 'MAC Address',
            value: data.mac_address
        });
    }
    
    const statusItemsHtml = statusItems.map(item => `
        <div class="status-item">
            <div class="icon">
                <i data-lucide="${item.icon}"></i>
            </div>
            <div class="content">
                <div class="label">${item.label}</div>
                <div class="value">${item.value}</div>
            </div>
        </div>
    `).join('');
    
    return `<div class="status-grid">${statusItemsHtml}</div>`;
}

async function scanNetworks() {
    const networksDiv = document.getElementById('networks-list');
    networksDiv.innerHTML = '<p class="loading"><i data-lucide="loader-2"></i> Scanning for networks...</p>';
    lucide.createIcons();
    
    const data = await apiCall(`/network/scan?interface_name=${selectedInterface}`);
    
    console.log('Scan data:', data); // Debug log
    
    if (data.error) {
        networksDiv.innerHTML = `<div class="result-error"><i data-lucide="x-circle"></i> Error: ${data.error}</div>`;
        lucide.createIcons();
        return;
    }
    
    if (!data || data.length === 0) {
        networksDiv.innerHTML = '<p><i data-lucide="wifi-off"></i> No networks found</p>';
        lucide.createIcons();
        return;
    }
    
    availableNetworks = data;
    updateNetworkSelect();
    
    let html = '';
    data.forEach(network => {
        console.log('Network:', network); // Debug log
        const signalBars = createSignalBars(network.signal);
        const securityIcon = network.auth !== 'Open' ? 'lock' : 'unlock';
        
        html += `
            <div class="network-item" onclick="fillSSID('${network.ssid}')">
                <div class="network-ssid">
                    <div class="network-name">
                        <i data-lucide="${securityIcon}"></i>
                        ${network.ssid}
                    </div>
                    <div class="signal-strength">
                        ${signalBars}
                        <span>${network.signal || 'N/A'}dBm</span>
                    </div>
                </div>
                <div class="network-details">
                    <span>Security: ${network.auth || 'Open'}</span>
                    ${network.bssid && network.bssid !== 'N/A' ? `<span>BSSID: ${network.bssid.replace(/\\:/g, ':').replace(/\\$/g, '')}</span>` : ''}
                    ${network.frequency && network.frequency !== 'N/A' ? `<span>Freq: ${network.frequency.toString().includes('MHz') ? network.frequency : network.frequency + ' MHz'}</span>` : ''}
                </div>
            </div>
        `;
    });
    networksDiv.innerHTML = html;
    lucide.createIcons();
}

function createSignalBars(signal) {
    // Handle cases where signal might be null/undefined
    if (!signal || signal === 'N/A') {
        return '<div class="signal-bars"><div class="signal-bar"></div><div class="signal-bar"></div><div class="signal-bar"></div><div class="signal-bar"></div></div>';
    }
    
    const strength = getSignalStrength(signal);
    let bars = '<div class="signal-bars">';
    
    for (let i = 1; i <= 4; i++) {
        const activeClass = i <= strength ? 'active' : '';
        bars += `<div class="signal-bar ${activeClass}"></div>`;
    }
    
    bars += '</div>';
    return bars;
}

function getSignalStrength(signal) {
    // Handle string or number input
    const signalNum = parseInt(signal) || -100;
    if (signalNum > -50) return 4;
    if (signalNum > -60) return 3;
    if (signalNum > -70) return 2;
    return 1;
}


function updateNetworkSelect() {
    const networkSelect = document.getElementById('network-select');
    networkSelect.innerHTML = '<option value="">Select from scanned networks...</option>';
    
    availableNetworks.forEach(network => {
        const option = document.createElement('option');
        option.value = network.ssid;
        option.textContent = `${network.ssid} (${network.signal}dBm)`;
        option.dataset.auth = network.auth;
        networkSelect.appendChild(option);
    });
    
    const manualOption = document.createElement('option');
    manualOption.value = 'manual';
    manualOption.textContent = 'Enter manually';
    networkSelect.appendChild(manualOption);
}

function onNetworkSelect() {
    const networkSelect = document.getElementById('network-select');
    const ssidInput = document.getElementById('ssid');
    const passwordInput = document.getElementById('password');
    
    if (networkSelect.value === 'manual' || networkSelect.value === '') {
        ssidInput.value = '';
        ssidInput.disabled = false;
        passwordInput.required = true;
    } else {
        ssidInput.value = networkSelect.value;
        ssidInput.disabled = true;
        
        const selectedOption = networkSelect.options[networkSelect.selectedIndex];
        const authType = selectedOption.dataset.auth;
        
        // If network is open, password is not required
        if (authType === 'Open') {
            passwordInput.required = false;
            passwordInput.value = '';
            passwordInput.placeholder = 'No password required for open network';
        } else {
            passwordInput.required = true;
            passwordInput.placeholder = 'Enter network password';
        }
    }
}

function fillSSID(ssid) {
    const networkSelect = document.getElementById('network-select');
    
    // Find the network in the dropdown
    for (let i = 0; i < networkSelect.options.length; i++) {
        if (networkSelect.options[i].value === ssid) {
            networkSelect.selectedIndex = i;
            break;
        }
    }
    
    // Trigger the change event
    onNetworkSelect();
}

async function connectToNetwork(event) {
    event.preventDefault();
    
    const ssid = document.getElementById('ssid').value;
    const password = document.getElementById('password').value;
    const interface_name = document.getElementById('interface').value;
    
    const resultDiv = document.getElementById('connection-result');
    resultDiv.innerHTML = '<p class="loading"><i data-lucide="loader-2"></i> Connecting to network...</p>';
    lucide.createIcons();
    
    const data = await apiCall('/network/connect', 'POST', {
        ssid,
        password,
        interface_name
    });
    
    if (data.connected) {
        resultDiv.innerHTML = `<div class="result-success"><i data-lucide="check-circle"></i> Successfully connected to ${ssid}</div>`;
        // Auto-refresh status after connection
        setTimeout(() => {
            refreshInterfaceAndNetwork();
        }, 2000);
    } else {
        resultDiv.innerHTML = `<div class="result-error"><i data-lucide="x-circle"></i> Failed to connect to ${ssid}</div>`;
    }
    lucide.createIcons();
}

async function getCurrentWifi() {
    const currentWifiDiv = document.getElementById('current-wifi');
    currentWifiDiv.innerHTML = `
        <div class="network-header">
            <h2>Network</h2>
            <div class="loading"><i data-lucide="loader-2"></i> Loading...</div>
        </div>
    `;
    lucide.createIcons();
    
    const data = await apiCall(`/network/current?interface_name=${selectedInterface}`);
    
    if (data.error) {
        currentWifiDiv.innerHTML = `
            <div class="network-header">
                <h2>Network</h2>
                <div class="result-error"><i data-lucide="x-circle"></i> Error: ${data.error}</div>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    if (!data.connected || !data.ssid) {
        currentWifiDiv.innerHTML = createCurrentWifiDisplay(null);
        lucide.createIcons();
        return;
    }
    
    // The new /network/current endpoint already includes all network details
    currentWifiDiv.innerHTML = createCurrentWifiDisplay(data);
    lucide.createIcons();
}

function createCurrentWifiDisplay(data) {
    console.log('Current WiFi data:', data); // Debug log
    
    // Handle disconnected state
    if (!data || !data.ssid) {
        // Hide disconnect button when disconnected
        const actionsDiv = document.getElementById('network-actions');
        if (actionsDiv) actionsDiv.style.display = 'none';
        
        return `
            <div class="network-header">
                <h2>Network</h2>
                <span class="status-badge disconnected">
                    <i data-lucide="x"></i>
                    Disconnected
                </span>
            </div>
            
            <div class="connection-network-name">
                <i data-lucide="wifi-off"></i>
                <span>No Network Connected</span>
            </div>
            
            <div class="connection-details">
                <div class="connection-info">
                    <i data-lucide="info"></i>
                    <span>Use the "Connect to Network" section to establish a connection.</span>
                </div>
            </div>
        `;
    }
    
    // Show disconnect button when connected
    const actionsDiv = document.getElementById('network-actions');
    if (actionsDiv) actionsDiv.style.display = 'block';
    
    const signal = data.signal || data.signal_level;
    const signalBars = signal ? createSignalBars(signal) : '';
    const cleanBssid = data.bssid ? data.bssid.replace(/\\:/g, ':').replace(/\\$/g, '') : null;
    const freqValue = data.frequency ? (data.frequency.toString().includes('MHz') ? data.frequency : `${data.frequency} MHz`) : null;
    
    return `
        <div class="network-header">
            <h2>Network</h2>
            <span class="status-badge connected">
                <i data-lucide="check"></i>
                Connected
            </span>
        </div>
        
        <div class="connection-network-name">
            ${signalBars}
            <span>${data.ssid}</span>
        </div>
        
        <div class="connection-details">
            <div class="connection-detail">
                <span class="detail-label">SSID:</span>
                <span class="detail-value">${data.ssid}</span>
            </div>
            ${cleanBssid ? `
                <div class="connection-detail">
                    <span class="detail-label">BSSID:</span>
                    <span class="detail-value">${cleanBssid}</span>
                </div>
            ` : ''}
            ${freqValue ? `
                <div class="connection-detail">
                    <span class="detail-label">Frequency:</span>
                    <span class="detail-value">${freqValue}</span>
                </div>
            ` : ''}
        </div>
    `;
}

// Merged refresh function for both interface and network
async function refreshInterfaceAndNetwork() {
    await getInterfaceStatus();
    await getCurrentWifi();
}

// Disconnect from current WiFi network
async function disconnectWifi() {
    if (!confirm('Are you sure you want to disconnect from the current WiFi network?')) {
        return;
    }
    
    const actionsDiv = document.getElementById('network-actions');
    const originalContent = actionsDiv.innerHTML;
    
    // Show loading state
    actionsDiv.innerHTML = `
        <div class="loading">
            <i data-lucide="loader-2"></i>
            Disconnecting...
        </div>
    `;
    lucide.createIcons();
    
    try {
        const result = await apiCall('/network/disconnect', 'POST', {interface_name: selectedInterface});
        
        if (result.disconnected) {
            // Success - refresh the interface and network status
            await refreshInterfaceAndNetwork();
        } else {
            // Failed - show error and restore original content
            actionsDiv.innerHTML = `
                <div class="result-error">
                    <i data-lucide="x-circle"></i>
                    Failed to disconnect
                </div>
            `;
            lucide.createIcons();
            
            // Restore original content after 3 seconds
            setTimeout(() => {
                actionsDiv.innerHTML = originalContent;
                lucide.createIcons();
            }, 3000);
        }
    } catch (error) {
        console.error('Disconnect error:', error);
        actionsDiv.innerHTML = `
            <div class="result-error">
                <i data-lucide="x-circle"></i>
                Error: ${error.message}
            </div>
        `;
        lucide.createIcons();
        
        // Restore original content after 3 seconds
        setTimeout(() => {
            actionsDiv.innerHTML = originalContent;
            lucide.createIcons();
        }, 3000);
    }
}

// Auto-load interface status on page load
window.onload = function() {
    loadInterfaces();
    refreshInterfaceAndNetwork();
};
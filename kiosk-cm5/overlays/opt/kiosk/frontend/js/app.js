/**
 * Kiosk Application JavaScript
 * Handles offline-first operation, NFC events, and network management
 */

class KioskApp {
    constructor() {
        this.currentScreen = 'loading';
        this.isOnline = navigator.onLine;
        this.nfcConnected = false;
        this.websocket = null;
        this.currentCard = null;
        this.networks = [];
        this.selectedNetwork = null;
        
        this.init();
    }

    async init() {
        console.log('Initializing Kiosk App...');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Register service worker for offline functionality
        await this.registerServiceWorker();
        
        // Check initial connectivity
        await this.checkConnectivity();
        
        // Start clock
        this.startClock();
        
        // Initialize based on network status
        if (this.isOnline) {
            await this.initializeOnlineMode();
        } else {
            this.showNetworkSetup();
        }
    }

    setupEventListeners() {
        // Network events
        window.addEventListener('online', () => this.handleOnlineStatus(true));
        window.addEventListener('offline', () => this.handleOnlineStatus(false));
        
        // Button events
        document.getElementById('scan-btn').addEventListener('click', () => this.scanNetworks());
        document.getElementById('connect-btn').addEventListener('click', () => this.connectToNetwork());
        document.getElementById('cancel-btn').addEventListener('click', () => this.cancelConnection());
        document.getElementById('settings-btn').addEventListener('click', () => this.showSettings());
        document.getElementById('close-settings-btn').addEventListener('click', () => this.showMainApp());
        document.getElementById('network-settings-btn').addEventListener('click', () => this.showNetworkSetup());
        document.getElementById('update-btn').addEventListener('click', () => this.checkForUpdates());
        
        // Keyboard events for kiosk mode
        document.addEventListener('keydown', (e) => {
            // Disable common keyboard shortcuts
            if (e.key === 'F11' || e.key === 'F12' || 
                (e.ctrlKey && (e.key === 'r' || e.key === 'R' || e.key === 'u' || e.key === 'U'))) {
                e.preventDefault();
            }
        });
    }

    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                await navigator.serviceWorker.register('/sw.js');
                console.log('Service Worker registered successfully');
            } catch (error) {
                console.error('Service Worker registration failed:', error);
            }
        }
    }

    async checkConnectivity() {
        try {
            const response = await fetch('/api/network/connectivity');
            const data = await response.json();
            this.isOnline = data.online;
        } catch (error) {
            this.isOnline = false;
        }
        
        this.updateNetworkStatus();
    }

    handleOnlineStatus(online) {
        this.isOnline = online;
        this.updateNetworkStatus();
        
        if (online && this.currentScreen === 'network-setup') {
            setTimeout(() => this.initializeOnlineMode(), 2000);
        }
    }

    updateNetworkStatus() {
        const statusElement = document.getElementById('network-status');
        const statusText = statusElement.querySelector('.status-text');
        
        if (this.isOnline) {
            statusText.textContent = 'Online';
            statusElement.style.color = '#28a745';
        } else {
            statusText.textContent = 'Offline';
            statusElement.style.color = '#dc3545';
        }
    }

    async initializeOnlineMode() {
        this.updateLoadingStatus('Connecting to services...');
        
        // Initialize NFC WebSocket connection
        await this.initializeNFC();
        
        // Show main application
        setTimeout(() => this.showMainApp(), 1000);
    }

    async initializeNFC() {
        try {
            this.websocket = new WebSocket('ws://localhost/ws');
            
            this.websocket.onopen = () => {
                console.log('NFC WebSocket connected');
                this.nfcConnected = true;
                this.updateNFCStatus('Ready');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleNFCEvent(data);
            };
            
            this.websocket.onclose = () => {
                console.log('NFC WebSocket disconnected');
                this.nfcConnected = false;
                this.updateNFCStatus('Disconnected');
                
                // Attempt to reconnect after 5 seconds
                setTimeout(() => this.initializeNFC(), 5000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('NFC WebSocket error:', error);
                this.updateNFCStatus('Error');
            };
            
        } catch (error) {
            console.error('Failed to initialize NFC:', error);
            this.updateNFCStatus('Not Available');
        }
    }

    handleNFCEvent(event) {
        console.log('NFC Event:', event);
        
        switch (event.event) {
            case 'nfc_detected':
                this.onNFCDetected(event.uid, event.data);
                break;
            case 'nfc_removed':
                this.onNFCRemoved();
                break;
        }
    }

    onNFCDetected(uid, data) {
        this.currentCard = { uid, data, detectedAt: new Date() };
        
        // Update UI
        const nfcReader = document.getElementById('nfc-reader');
        const nfcMessage = document.getElementById('nfc-message');
        const cardInfo = document.getElementById('card-info');
        
        nfcReader.className = 'nfc-reader detected';
        nfcMessage.textContent = 'Card detected!';
        
        // Show card information
        document.getElementById('card-uid').textContent = uid;
        document.getElementById('card-type').textContent = data?.type || 'Unknown';
        document.getElementById('card-time').textContent = this.currentCard.detectedAt.toLocaleTimeString();
        
        cardInfo.classList.remove('hidden');
        
        this.updateNFCStatus('Card Present');
    }

    onNFCRemoved() {
        this.currentCard = null;
        
        // Update UI
        const nfcReader = document.getElementById('nfc-reader');
        const nfcMessage = document.getElementById('nfc-message');
        const cardInfo = document.getElementById('card-info');
        
        nfcReader.className = 'nfc-reader';
        nfcMessage.textContent = 'Waiting for NFC card...';
        cardInfo.classList.add('hidden');
        
        this.updateNFCStatus('Ready');
    }

    updateNFCStatus(status) {
        const statusElement = document.getElementById('nfc-status');
        const statusText = statusElement.querySelector('.status-text');
        statusText.textContent = status;
        
        // Color coding
        if (status === 'Ready') {
            statusElement.style.color = '#28a745';
        } else if (status === 'Card Present') {
            statusElement.style.color = '#ffa500';
        } else if (status.includes('Error') || status.includes('Disconnected')) {
            statusElement.style.color = '#dc3545';
        } else {
            statusElement.style.color = '#ccc';
        }
    }

    async scanNetworks() {
        const scanBtn = document.getElementById('scan-btn');
        const statusDiv = document.getElementById('scan-status');
        const networkList = document.getElementById('network-list');
        
        scanBtn.disabled = true;
        scanBtn.textContent = 'Scanning...';
        statusDiv.innerHTML = '<div class="status-message info">Scanning for networks...</div>';
        
        try {
            const response = await fetch('/api/network/scan');
            const networks = await response.json();
            
            this.networks = networks;
            this.renderNetworkList(networks);
            
            statusDiv.innerHTML = `<div class="status-message success">Found ${networks.length} networks</div>`;
            
        } catch (error) {
            console.error('Network scan failed:', error);
            statusDiv.innerHTML = '<div class="status-message error">Failed to scan networks</div>';
        }
        
        scanBtn.disabled = false;
        scanBtn.textContent = 'Scan Networks';
    }

    renderNetworkList(networks) {
        const networkList = document.getElementById('network-list');
        
        if (networks.length === 0) {
            networkList.innerHTML = '<p class="text-center">No networks found</p>';
            return;
        }
        
        networkList.innerHTML = networks.map(network => `
            <div class="network-item ${network.connected ? 'connected' : ''}" 
                 onclick="kioskApp.selectNetwork('${network.ssid}')">
                <div class="network-info">
                    <div class="network-ssid">${network.ssid}</div>
                    <div class="network-details">
                        ${network.security} • ${network.frequency}
                        ${network.connected ? ' • Connected' : ''}
                    </div>
                </div>
                <div class="signal-strength">
                    <div class="signal-bars">
                        ${this.generateSignalBars(network.signal_strength)}
                    </div>
                    <span>${network.signal_strength}%</span>
                </div>
            </div>
        `).join('');
    }

    generateSignalBars(strength) {
        const bars = [];
        for (let i = 1; i <= 4; i++) {
            const active = strength >= (i * 25) ? 'active' : '';
            bars.push(`<div class="signal-bar ${active}"></div>`);
        }
        return bars.join('');
    }

    selectNetwork(ssid) {
        const network = this.networks.find(n => n.ssid === ssid);
        if (!network) return;
        
        this.selectedNetwork = network;
        
        if (network.connected) {
            this.showMainApp();
            return;
        }
        
        // Show connection form
        const form = document.getElementById('connection-form');
        const ssidElement = document.getElementById('connect-ssid');
        const passwordInput = document.getElementById('password');
        
        ssidElement.textContent = `Connect to ${ssid}`;
        passwordInput.value = '';
        form.classList.remove('hidden');
        
        // Focus password input
        setTimeout(() => passwordInput.focus(), 100);
    }

    async connectToNetwork() {
        if (!this.selectedNetwork) return;
        
        const connectBtn = document.getElementById('connect-btn');
        const password = document.getElementById('password').value;
        
        connectBtn.disabled = true;
        connectBtn.textContent = 'Connecting...';
        
        try {
            const response = await fetch('/api/network/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ssid: this.selectedNetwork.ssid,
                    password: password
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Connected to network:', result);
                
                // Hide connection form
                this.cancelConnection();
                
                // Check connectivity and proceed
                await this.checkConnectivity();
                if (this.isOnline) {
                    await this.initializeOnlineMode();
                }
            } else {
                throw new Error('Connection failed');
            }
            
        } catch (error) {
            console.error('Connection error:', error);
            alert('Failed to connect to network. Please check the password and try again.');
        }
        
        connectBtn.disabled = false;
        connectBtn.textContent = 'Connect';
    }

    cancelConnection() {
        const form = document.getElementById('connection-form');
        form.classList.add('hidden');
        this.selectedNetwork = null;
    }

    // Screen Management
    showScreen(screenId) {
        // Hide all screens
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        
        // Show selected screen
        document.getElementById(screenId).classList.add('active');
        this.currentScreen = screenId;
    }

    showNetworkSetup() {
        this.showScreen('network-setup');
        // Auto-scan networks
        setTimeout(() => this.scanNetworks(), 500);
    }

    showMainApp() {
        this.showScreen('main-app');
    }

    showSettings() {
        this.showScreen('settings');
        this.updateSettingsInfo();
    }

    updateSettingsInfo() {
        const networkStatus = document.getElementById('settings-network-status');
        networkStatus.textContent = this.isOnline ? 'Connected' : 'Disconnected';
    }

    async checkForUpdates() {
        const updateBtn = document.getElementById('update-btn');
        updateBtn.disabled = true;
        updateBtn.textContent = 'Checking...';
        
        try {
            // Simulate update check
            await new Promise(resolve => setTimeout(resolve, 2000));
            alert('System is up to date');
        } catch (error) {
            alert('Failed to check for updates');
        }
        
        updateBtn.disabled = false;
        updateBtn.textContent = 'Check for Updates';
    }

    updateLoadingStatus(status) {
        const loadingStatus = document.getElementById('loading-status');
        if (loadingStatus) {
            loadingStatus.textContent = status;
        }
    }

    startClock() {
        const updateClock = () => {
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', { 
                hour12: false,
                hour: '2-digit',
                minute: '2-digit'
            });
            
            const timeElement = document.getElementById('system-time');
            if (timeElement) {
                timeElement.textContent = timeString;
            }
        };
        
        updateClock();
        setInterval(updateClock, 1000);
    }
}

// Service Worker for offline functionality
if ('serviceWorker' in navigator) {
    // Register service worker
    navigator.serviceWorker.register('/sw.js')
        .then(registration => console.log('SW registered'))
        .catch(error => console.log('SW registration failed'));
}

// Initialize app when DOM is loaded
let kioskApp;
document.addEventListener('DOMContentLoaded', () => {
    kioskApp = new KioskApp();
});
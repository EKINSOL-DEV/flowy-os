#!/usr/bin/env python3
"""
Network Management API for WiFi scanning and connection
"""

import subprocess
import json
import re
import logging
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kiosk Network API", version="1.0.0")

class NetworkConnection(BaseModel):
    ssid: str
    password: str

class NetworkInfo(BaseModel):
    ssid: str
    signal_strength: int
    security: str
    frequency: str
    connected: bool = False

class NetworkManager:
    """Network management using NetworkManager (nmcli)"""
    
    @staticmethod
    def run_command(cmd: List[str]) -> subprocess.CompletedProcess:
        """Run shell command and return result"""
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return result
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=408, detail="Command timeout")
        except Exception as e:
            logger.error(f"Command failed: {' '.join(cmd)} - {e}")
            raise HTTPException(status_code=500, detail=f"Command failed: {e}")

    def scan_networks(self) -> List[NetworkInfo]:
        """Scan for available WiFi networks"""
        try:
            # Rescan networks
            self.run_command(['nmcli', 'device', 'wifi', 'rescan'])
            
            # Get network list
            result = self.run_command([
                'nmcli', '-t', '-f', 
                'SSID,SIGNAL,SECURITY,FREQ,ACTIVE', 
                'device', 'wifi', 'list'
            ])
            
            if result.returncode != 0:
                logger.error(f"WiFi scan failed: {result.stderr}")
                return []
            
            networks = []
            seen_ssids = set()
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split(':')
                if len(parts) >= 5:
                    ssid = parts[0].strip()
                    if not ssid or ssid in seen_ssids:
                        continue
                        
                    seen_ssids.add(ssid)
                    
                    try:
                        signal = int(parts[1]) if parts[1] else 0
                    except ValueError:
                        signal = 0
                    
                    security = parts[2] if parts[2] else "Open"
                    frequency = parts[3] if parts[3] else ""
                    active = parts[4] == 'yes' if len(parts) > 4 else False
                    
                    networks.append(NetworkInfo(
                        ssid=ssid,
                        signal_strength=signal,
                        security=security,
                        frequency=frequency,
                        connected=active
                    ))
            
            # Sort by signal strength
            networks.sort(key=lambda x: x.signal_strength, reverse=True)
            return networks
            
        except Exception as e:
            logger.error(f"Network scan error: {e}")
            return []

    def get_connection_status(self) -> Dict:
        """Get current network connection status"""
        try:
            # Get active connection
            result = self.run_command([
                'nmcli', '-t', '-f', 
                'NAME,TYPE,DEVICE,STATE', 
                'connection', 'show', '--active'
            ])
            
            connections = []
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split(':')
                    if len(parts) >= 4:
                        connections.append({
                            'name': parts[0],
                            'type': parts[1],
                            'device': parts[2],
                            'state': parts[3]
                        })
            
            # Get device status
            device_result = self.run_command([
                'nmcli', '-t', '-f', 
                'DEVICE,TYPE,STATE,CONNECTION', 
                'device', 'status'
            ])
            
            devices = []
            if device_result.returncode == 0:
                for line in device_result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split(':')
                    if len(parts) >= 4:
                        devices.append({
                            'device': parts[0],
                            'type': parts[1],
                            'state': parts[2],
                            'connection': parts[3] if parts[3] != '--' else None
                        })
            
            return {
                'connections': connections,
                'devices': devices,
                'online': self.check_internet_connectivity()
            }
            
        except Exception as e:
            logger.error(f"Status check error: {e}")
            return {'connections': [], 'devices': [], 'online': False}

    def connect_network(self, ssid: str, password: str) -> bool:
        """Connect to WiFi network"""
        try:
            # First try to connect to existing connection
            result = self.run_command([
                'nmcli', 'connection', 'up', ssid
            ])
            
            if result.returncode == 0:
                logger.info(f"Connected to existing network: {ssid}")
                return True
            
            # Create new connection
            cmd = [
                'nmcli', 'device', 'wifi', 'connect', ssid
            ]
            
            if password:
                cmd.extend(['password', password])
            
            result = self.run_command(cmd)
            
            if result.returncode == 0:
                logger.info(f"Successfully connected to: {ssid}")
                return True
            else:
                logger.error(f"Connection failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def disconnect_network(self, ssid: str) -> bool:
        """Disconnect from network"""
        try:
            result = self.run_command([
                'nmcli', 'connection', 'down', ssid
            ])
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False

    def forget_network(self, ssid: str) -> bool:
        """Remove saved network"""
        try:
            result = self.run_command([
                'nmcli', 'connection', 'delete', ssid
            ])
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Forget network error: {e}")
            return False

    def check_internet_connectivity(self) -> bool:
        """Check if internet is accessible"""
        try:
            result = self.run_command([
                'ping', '-c', '1', '-W', '5', '8.8.8.8'
            ])
            return result.returncode == 0
        except Exception:
            return False

# Initialize network manager
network_manager = NetworkManager()

@app.get("/api/network/scan", response_model=List[NetworkInfo])
async def scan_networks():
    """Scan for available WiFi networks"""
    networks = network_manager.scan_networks()
    return networks

@app.get("/api/network/status")
async def get_status():
    """Get current network connection status"""
    status = network_manager.get_connection_status()
    return status

@app.post("/api/network/connect")
async def connect_network(connection: NetworkConnection):
    """Connect to WiFi network"""
    success = network_manager.connect_network(connection.ssid, connection.password)
    if not success:
        raise HTTPException(status_code=400, detail="Connection failed")
    
    # Wait a moment for connection to establish
    await asyncio.sleep(2)
    
    return {"status": "connected", "ssid": connection.ssid}

@app.post("/api/network/disconnect/{ssid}")
async def disconnect_network(ssid: str):
    """Disconnect from network"""
    success = network_manager.disconnect_network(ssid)
    if not success:
        raise HTTPException(status_code=400, detail="Disconnect failed")
    
    return {"status": "disconnected", "ssid": ssid}

@app.delete("/api/network/forget/{ssid}")
async def forget_network(ssid: str):
    """Remove saved network"""
    success = network_manager.forget_network(ssid)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to forget network")
    
    return {"status": "forgotten", "ssid": ssid}

@app.get("/api/network/connectivity")
async def check_connectivity():
    """Check internet connectivity"""
    online = network_manager.check_internet_connectivity()
    return {"online": online}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "network-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3003)
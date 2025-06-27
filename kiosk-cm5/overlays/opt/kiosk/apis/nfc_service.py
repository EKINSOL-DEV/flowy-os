#!/usr/bin/env python3
"""
NFC Service with WebSocket support for real-time communication
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Set
import signal
import sys

try:
    import nfc
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False
    print("Warning: nfcpy not available, using mock NFC")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NFCService:
    def __init__(self):
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.running = True
        self.current_tag = None
        
        if NFC_AVAILABLE:
            try:
                self.clf = nfc.ContactlessFrontend('usb')
                logger.info("NFC reader initialized")
            except Exception as e:
                logger.error(f"Failed to initialize NFC reader: {e}")
                self.clf = None
        else:
            self.clf = None
            logger.warning("NFC not available, running in mock mode")

    async def register_client(self, websocket, path):
        """Register new WebSocket client"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast_event(self, event_type: str, uid: str = None, data: dict = None):
        """Broadcast NFC event to all connected clients"""
        if not self.clients:
            return

        message = {
            'event': event_type,
            'uid': uid,
            'timestamp': datetime.now().isoformat(),
            'data': data or {}
        }
        
        message_json = json.dumps(message)
        logger.info(f"Broadcasting: {message_json}")

        # Send to all clients
        disconnected = set()
        for client in self.clients.copy():
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)

        # Remove disconnected clients
        for client in disconnected:
            self.clients.discard(client)

    def on_tag_connect(self, tag):
        """Callback when NFC tag is detected"""
        try:
            uid = tag.identifier.hex().upper()
            logger.info(f"NFC tag detected: {uid}")
            
            # Store current tag
            self.current_tag = {
                'uid': uid,
                'type': str(tag.type),
                'detected_at': datetime.now().isoformat()
            }
            
            # Schedule broadcast
            asyncio.create_task(
                self.broadcast_event('nfc_detected', uid, self.current_tag)
            )
            
            return True
        except Exception as e:
            logger.error(f"Error handling tag connect: {e}")
            return False

    def on_tag_release(self):
        """Callback when NFC tag is removed"""
        if self.current_tag:
            logger.info(f"NFC tag removed: {self.current_tag['uid']}")
            
            # Schedule broadcast
            asyncio.create_task(
                self.broadcast_event('nfc_removed', self.current_tag['uid'])
            )
            
            self.current_tag = None

    async def nfc_monitor(self):
        """Monitor NFC reader for tag events"""
        logger.info("Starting NFC monitoring...")
        
        while self.running:
            try:
                if self.clf:
                    # Real NFC monitoring
                    tag = self.clf.connect(
                        rdwr={
                            'on-connect': self.on_tag_connect,
                            'on-release': self.on_tag_release
                        },
                        terminate=lambda: not self.running
                    )
                else:
                    # Mock NFC for testing
                    await asyncio.sleep(5)
                    if self.current_tag is None:
                        # Simulate tag detection
                        mock_uid = "04:52:3A:B1:2C:80:00"
                        self.current_tag = {
                            'uid': mock_uid,
                            'type': 'Mock',
                            'detected_at': datetime.now().isoformat()
                        }
                        await self.broadcast_event('nfc_detected', mock_uid, self.current_tag)
                    else:
                        # Simulate tag removal
                        await self.broadcast_event('nfc_removed', self.current_tag['uid'])
                        self.current_tag = None
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"NFC monitoring error: {e}")
                await asyncio.sleep(1)

    def stop(self):
        """Stop the NFC service"""
        logger.info("Stopping NFC service...")
        self.running = False
        if self.clf:
            self.clf.close()

async def main():
    # Create NFC service
    nfc_service = NFCService()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        nfc_service.stop()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start WebSocket server
        logger.info("Starting WebSocket server on port 3001...")
        server = await websockets.serve(
            nfc_service.register_client,
            "0.0.0.0",
            3001
        )
        
        # Start NFC monitoring
        nfc_task = asyncio.create_task(nfc_service.nfc_monitor())
        
        logger.info("NFC Service started successfully")
        
        # Wait for tasks
        await asyncio.gather(
            server.wait_closed(),
            nfc_task
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        nfc_service.stop()
        logger.info("NFC Service stopped")

if __name__ == "__main__":
    asyncio.run(main())
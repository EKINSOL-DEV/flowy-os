#!/usr/bin/env python3
"""
FastAPI NFC API Server

Provides HTTP endpoints for NFC tag reading and writing operations using the nfc_reader module.
"""

import sys
import os
import asyncio
import time
import json
from typing import Optional, Dict, Any, List, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import NFC modules - either hardware I2C/SPI driver or USB Pico bridge
use_pico_bridge = "--usb" in sys.argv or "--usb-device" in sys.argv

if use_pico_bridge:
    try:
        from pico_nfc_bridge import NFCReader, NFCError, NFCInitializationError
        print("Using Pi Pico NFC Bridge (USB/Serial)")
    except ImportError as e:
        print(f"Error importing pico_nfc_bridge: {e}")
        sys.exit(1)
else:
    try:
        import nfc_reader
        from nfc_reader import NFCReader, NFCError, NFCInitializationError
        print("Using hardware NFC driver (I2C/SPI)")
    except ImportError as e:
        print(f"Error importing nfc_reader: {e}")
        print("Make sure nfc_reader.py and nfc_native.so are available in /home/builder/flowy-os/output/")
        sys.exit(1)

# Global NFC reader instance
nfc_reader_instance: Optional[NFCReader] = None

# WebSocket connection manager
class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
            
        # Create list of connections to remove if they fail
        failed_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                failed_connections.append(connection)
        
        # Remove failed connections
        for connection in failed_connections:
            self.active_connections.discard(connection)

websocket_manager = WebSocketManager()

# Polling state management
polling_active = False
polling_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for NFC initialization and cleanup"""
    global nfc_reader_instance
    
    # Startup
    try:
        if use_pico_bridge:
            # For Pico bridge, pass USB device path if specified
            usb_device = None
            for i, arg in enumerate(sys.argv):
                if arg == "--usb-device" and i + 1 < len(sys.argv):
                    usb_device = sys.argv[i + 1]
                    break
            nfc_reader_instance = NFCReader(device_path=usb_device, auto_cleanup=False)
        else:
            nfc_reader_instance = NFCReader(auto_cleanup=False)
        
        nfc_reader_instance.initialize()
        print("NFC reader initialized successfully")
    except NFCInitializationError as e:
        print(f"Warning: NFC initialization failed: {e}")
        print("API will still start but NFC operations will fail")
        nfc_reader_instance = None
    
    yield
    
    # Shutdown
    if nfc_reader_instance:
        nfc_reader_instance.cleanup()
        print("NFC reader cleaned up")

app = FastAPI(
    title="NFC API Server",
    description="HTTP API for NFC tag reading and writing operations",
    version="1.0.0",
    lifespan=lifespan
)

# Pydantic models for simplified API
class NFCWriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Text to write to NFC tag")

class NFCWriteResponse(BaseModel):
    success: bool
    message: str

class NFCEnableDisableResponse(BaseModel):
    success: bool
    message: str

class NFCPingResponse(BaseModel):
    success: bool
    message: str
    initialized: bool

# Utility function to check NFC availability
def check_nfc_available():
    if nfc_reader_instance is None:
        raise HTTPException(status_code=503, detail="NFC reader not initialized")

# Polling functionality for streaming NFC events
async def start_nfc_polling():
    """Start continuous NFC polling and stream events to WebSocket clients"""
    global polling_active
    
    if not nfc_reader_instance:
        return
    
    polling_active = True
    
    try:
        # For Pico bridge, we can start the POLL command and parse the serial output
        if use_pico_bridge:
            await poll_pico_bridge()
        else:
            # For hardware driver, implement basic polling
            await poll_hardware_driver()
    except Exception as e:
        print(f"Error in NFC polling: {e}")
        await websocket_manager.broadcast({
            "type": "error",
            "message": f"Polling error: {str(e)}"
        })
    finally:
        polling_active = False

async def poll_pico_bridge():
    """Poll using Pico bridge serial commands"""
    global polling_active
    
    try:
        # Send POLL command to start continuous polling
        if hasattr(nfc_reader_instance, 'serial_port') and nfc_reader_instance.serial_port:
            nfc_reader_instance.serial_port.write("POLL\n".encode())
            
            while polling_active:
                # Read lines from serial and parse NFC events
                if nfc_reader_instance.serial_port.in_waiting > 0:
                    try:
                        line = nfc_reader_instance.serial_port.readline().decode().strip()
                        if line:
                            await parse_nfc_event(line)
                    except Exception as e:
                        print(f"Error reading serial line: {e}")
                
                await asyncio.sleep(0.1)
                
    except Exception as e:
        print(f"Error in Pico bridge polling: {e}")
    finally:
        # Send ENDPOLL to stop polling
        try:
            if hasattr(nfc_reader_instance, 'serial_port') and nfc_reader_instance.serial_port:
                nfc_reader_instance.serial_port.write("ENDPOLL\n".encode())
        except:
            pass

async def poll_hardware_driver():
    """Poll using hardware driver (basic implementation)"""
    global polling_active
    
    while polling_active:
        try:
            # Basic tag detection using hardware driver
            if nfc_reader_instance.is_tag_present():
                tag_info = nfc_reader_instance.get_tag_info()
                if tag_info:
                    await websocket_manager.broadcast({
                        "type": "enter",
                        "data": {
                            "uid": tag_info.get("uid"),
                            "technology": tag_info.get("technology_name"),
                            "text": tag_info.get("text", "")
                        }
                    })
                    
                    # Wait for tag removal
                    while nfc_reader_instance.is_tag_present() and polling_active:
                        await asyncio.sleep(0.5)
                    
                    await websocket_manager.broadcast({
                        "type": "leave",
                        "data": {
                            "uid": tag_info.get("uid")
                        }
                    })
            
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Error in hardware driver polling: {e}")
            await asyncio.sleep(1)

async def parse_nfc_event(line: str):
    """Parse NFC events from Pico bridge serial output"""
    try:
        if line.startswith("OK:ENTER:"):
            # Parse: OK:ENTER:PROTOCOL:TECH:ID:"MESSAGE"
            parts = line.split(":", 5)
            if len(parts) >= 6:
                protocol = parts[2]
                tech = parts[3]
                tag_id = parts[4]
                message = parts[5].strip('"')
                
                await websocket_manager.broadcast({
                    "type": "enter",
                    "data": {
                        "uid": tag_id,
                        "protocol": protocol,
                        "technology": tech,
                        "text": message
                    }
                })
        
        elif line.startswith("OK:LEAVE:"):
            # Parse: OK:LEAVE:ID
            parts = line.split(":", 2)
            if len(parts) >= 3:
                tag_id = parts[2]
                
                await websocket_manager.broadcast({
                    "type": "leave",
                    "data": {
                        "uid": tag_id
                    }
                })
        
        elif line.startswith("POLLEND"):
            await websocket_manager.broadcast({
                "type": "poll_ended",
                "message": "Polling session ended"
            })
            
    except Exception as e:
        print(f"Error parsing NFC event '{line}': {e}")

async def stop_nfc_polling():
    """Stop NFC polling"""
    global polling_active, polling_task
    
    polling_active = False
    
    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    polling_task = None

# WebSocket endpoint for real-time NFC events
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming real-time NFC events"""
    await websocket_manager.connect(websocket)
    
    # Send initial status
    await websocket.send_json({
        "type": "status",
        "data": {
            "connected": True,
            "nfc_available": nfc_reader_instance is not None,
            "polling_active": polling_active
        }
    })
    
    try:
        while True:
            # Keep the connection alive and handle any client messages
            try:
                message = await websocket.receive_text()
                # Echo back any messages (could be used for client-side ping/pong)
                await websocket.send_json({"type": "echo", "message": message})
            except WebSocketDisconnect:
                break
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)

# Simplified REST API endpoints
@app.get("/ping", response_model=NFCPingResponse)
async def ping():
    """Ping endpoint to check if NFC system is available"""
    return NFCPingResponse(
        success=True,
        message="NFC API is running",
        initialized=nfc_reader_instance is not None
    )

@app.post("/enable", response_model=NFCEnableDisableResponse)
async def enable_polling():
    """Enable continuous NFC polling and stream events via WebSocket"""
    global polling_task
    
    check_nfc_available()
    
    try:
        if polling_active:
            return NFCEnableDisableResponse(
                success=True,
                message="NFC polling is already active"
            )
        
        # Start polling in background task
        polling_task = asyncio.create_task(start_nfc_polling())
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        return NFCEnableDisableResponse(
            success=True,
            message="NFC polling enabled successfully"
        )
        
    except Exception as e:
        return NFCEnableDisableResponse(
            success=False,
            message=f"Error enabling NFC polling: {str(e)}"
        )

@app.post("/disable", response_model=NFCEnableDisableResponse)
async def disable_polling():
    """Disable continuous NFC polling"""
    try:
        if not polling_active:
            return NFCEnableDisableResponse(
                success=True,
                message="NFC polling is already inactive"
            )
        
        await stop_nfc_polling()
        
        return NFCEnableDisableResponse(
            success=True,
            message="NFC polling disabled successfully"
        )
        
    except Exception as e:
        return NFCEnableDisableResponse(
            success=False,
            message=f"Error disabling NFC polling: {str(e)}"
        )

@app.post("/write", response_model=NFCWriteResponse)
async def write_tag(request: NFCWriteRequest):
    """Write text to an NFC tag"""
    check_nfc_available()
    
    try:
        if use_pico_bridge:
            # Use Pico bridge WRITE command
            if hasattr(nfc_reader_instance, 'serial_port') and nfc_reader_instance.serial_port:
                command = f"WRITE:{request.text}\n"
                nfc_reader_instance.serial_port.write(command.encode())
                
                # Wait for response
                start_time = time.time()
                while time.time() - start_time < 10:  # 10 second timeout
                    if nfc_reader_instance.serial_port.in_waiting > 0:
                        try:
                            line = nfc_reader_instance.serial_port.readline().decode().strip()
                            if line == "OK:WRITE_SUCCESS":
                                return NFCWriteResponse(
                                    success=True,
                                    message=f"Successfully wrote '{request.text}' to NFC tag"
                                )
                            elif line.startswith("ERROR:"):
                                return NFCWriteResponse(
                                    success=False,
                                    message=f"Write failed: {line}"
                                )
                        except Exception as e:
                            print(f"Error reading write response: {e}")
                    
                    await asyncio.sleep(0.1)
                
                return NFCWriteResponse(
                    success=False,
                    message="Write operation timed out"
                )
            else:
                return NFCWriteResponse(
                    success=False,
                    message="Pico bridge device not available"
                )
        else:
            # Use hardware driver
            success = nfc_reader_instance.write_text(request.text)
            if success:
                return NFCWriteResponse(
                    success=True,
                    message=f"Successfully wrote '{request.text}' to NFC tag"
                )
            else:
                return NFCWriteResponse(
                    success=False,
                    message="Failed to write to NFC tag"
                )
                
    except Exception as e:
        return NFCWriteResponse(
            success=False,
            message=f"Error writing to NFC tag: {str(e)}"
        )

if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="NFC API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=10001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    # Hardware NFC driver options (I2C/SPI)
    parser.add_argument("--i2c-bus", default="/dev/i2c-1", help="I2C bus device (default: /dev/i2c-1)")
    parser.add_argument("--gpio-int", type=int, default=23, help="GPIO pin for NFC interrupt (default: 23)")
    parser.add_argument("--gpio-enable", type=int, default=24, help="GPIO pin for NFC enable (default: 24)")
    parser.add_argument("--gpio-fwdnld", type=int, default=25, help="GPIO pin for NFC firmware download (default: 25)")
    
    # USB Pico bridge options
    parser.add_argument("--usb", action="store_true", help="Use Pi Pico NFC bridge over USB/Serial")
    parser.add_argument("--usb-device", help="USB serial device path (e.g., /dev/ttyACM0)")
    
    args = parser.parse_args()
    
    print(f"Starting NFC API Server on {args.host}:{args.port}")
    
    if args.usb or args.usb_device:
        device_path = args.usb_device or "auto-detect"
        print(f"Using Pi Pico NFC Bridge (USB/Serial) - Device: {device_path}")
    else:
        # Set NFC configuration environment variables for hardware driver
        os.environ['NFC_I2C_BUS'] = args.i2c_bus
        os.environ['NFC_PIN_INT'] = str(args.gpio_int)
        os.environ['NFC_PIN_ENABLE'] = str(args.gpio_enable)
        os.environ['NFC_PIN_FWDNLD'] = str(args.gpio_fwdnld)
        
        print(f"Using hardware NFC driver (I2C/SPI)")
        print(f"I2C bus: {args.i2c_bus}")
        print(f"GPIO pins - INT: {args.gpio_int}, ENABLE: {args.gpio_enable}, FWDNLD: {args.gpio_fwdnld}")
    
    uvicorn.run(
        "nfc_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
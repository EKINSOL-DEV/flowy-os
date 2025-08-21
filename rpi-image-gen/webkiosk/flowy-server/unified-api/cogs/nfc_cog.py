"""
NFC Cog for Flowy Unified API

Provides endpoints for NFC tag reading and writing operations with WebSocket support 
for real-time events. Converted from the original NFC API to use the cogs architecture.
"""

import sys
import os
import asyncio
import time
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# Add the modules path for imports
modules_path = os.path.join(os.path.dirname(__file__), "../modules") 
sys.path.insert(0, modules_path)

# Try to load configuration for NFC mode selection
try:
    from config_loader import get_config
    config = get_config()
    use_pico_bridge = config.cogs.nfc.use_pico_bridge or "--usb" in sys.argv or "--usb-device" in sys.argv
    print(f"NFC: Configuration loaded, use_pico_bridge = {use_pico_bridge}")
except ImportError:
    # Fallback to command line arguments only
    use_pico_bridge = "--usb" in sys.argv or "--usb-device" in sys.argv
    print(f"NFC: Using command line args only, use_pico_bridge = {use_pico_bridge}")

# Import NFC modules with proper fallback logic
NFC_HARDWARE_AVAILABLE = False
NFC_TYPE = "mock"

# Try to use USB bridge if explicitly requested
if use_pico_bridge:
    try:
        from pico_nfc_bridge import NFCReader, NFCError, NFCInitializationError
        NFC_HARDWARE_AVAILABLE = True
        NFC_TYPE = "pico_bridge"
        print("NFC: Using USB Pico bridge")
    except ImportError as e:
        print(f"NFC USB bridge not available: {e}")

# If USB bridge not requested or failed, try native library
if not NFC_HARDWARE_AVAILABLE:
    try:
        import nfc_reader
        from nfc_reader import NFCReader, NFCError, NFCInitializationError
        NFC_HARDWARE_AVAILABLE = True
        NFC_TYPE = "hardware"
        print("NFC: Using native library")
    except ImportError as e:
        print(f"NFC native library not available: {e}")

# If native library failed, try USB bridge as fallback
if not NFC_HARDWARE_AVAILABLE:
    try:
        from pico_nfc_bridge import NFCReader, NFCError, NFCInitializationError
        NFC_HARDWARE_AVAILABLE = True
        NFC_TYPE = "pico_bridge"
        print("NFC: Falling back to USB Pico bridge")
    except ImportError as e:
        print(f"NFC USB bridge fallback failed: {e}")

# If everything failed, use mock mode
if not NFC_HARDWARE_AVAILABLE:
    print("NFC hardware not available, using mock mode")

from .base_cog import BaseCog

# Pydantic models for API
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

class NFCCog(BaseCog):
    """NFC control cog with WebSocket support for real-time events"""
    
    def __init__(self, name: str = "nfc"):
        super().__init__(name)
        self.supports_websocket = True  # Enable WebSocket support
        self.nfc_reader_instance: Optional[NFCReader] = None
        
        # Polling state management
        self.polling_active = False
        self.polling_task = None
        
        # Register NFC endpoints
        self._register_nfc_endpoints()
    
    async def initialize(self) -> bool:
        """Initialize the NFC hardware"""
        try:
            if NFC_HARDWARE_AVAILABLE:
                if use_pico_bridge:
                    # For Pico bridge, pass USB device path if specified
                    usb_device = None
                    for i, arg in enumerate(sys.argv):
                        if arg == "--usb-device" and i + 1 < len(sys.argv):
                            usb_device = sys.argv[i + 1]
                            break
                    self.nfc_reader_instance = NFCReader(device_path=usb_device, auto_cleanup=False)
                else:
                    self.nfc_reader_instance = NFCReader(auto_cleanup=False)
                
                self.nfc_reader_instance.initialize()
                self.logger.info(f"NFC reader initialized successfully (type: {NFC_TYPE})")
                self.status = "running"
                return True
            else:
                self.logger.warning("NFC hardware not available, running in mock mode")
                self.status = "running"
                return True
        except NFCInitializationError as e:
            self.logger.warning(f"NFC initialization failed: {e}")
            self.logger.warning("API will still start but NFC operations will fail")
            self.nfc_reader_instance = None
            self.status = "degraded"
            return True
        except Exception as e:
            self.log_error(e, "NFC initialization error")
            self.status = "failed"
            return False
    
    async def shutdown(self):
        """Clean shutdown of NFC hardware"""
        try:
            # Stop polling if active
            await self.stop_nfc_polling()
            
            # Cleanup NFC reader
            if self.nfc_reader_instance:
                self.nfc_reader_instance.cleanup()
                self.logger.info("NFC reader cleaned up")
        except Exception as e:
            self.log_error(e, "NFC shutdown error")
    
    def get_capabilities(self) -> List[str]:
        """Return NFC capabilities"""
        capabilities = [
            "nfc_control",
            "tag_reading",
            "tag_writing",
            "real_time_events",
            "websocket_support"
        ]
        
        if NFC_HARDWARE_AVAILABLE and self.nfc_reader_instance:
            capabilities.extend([
                f"hardware_type_{NFC_TYPE}",
                "continuous_polling",
                "tag_detection"
            ])
        else:
            capabilities.extend([
                "mock_control",
                "simulated_events"
            ])
        
        return capabilities
    
    def _check_nfc_available(self):
        """Check if NFC reader is available"""
        if not NFC_HARDWARE_AVAILABLE or self.nfc_reader_instance is None:
            raise HTTPException(status_code=503, detail="NFC reader not initialized")
    
    async def start_nfc_polling(self):
        """Start continuous NFC polling and stream events to WebSocket clients"""
        if not NFC_HARDWARE_AVAILABLE or not self.nfc_reader_instance:
            # Mock polling for testing
            await self._mock_polling()
            return
        
        self.polling_active = True
        
        try:
            if NFC_TYPE == "pico_bridge":
                await self._poll_pico_bridge()
            else:
                await self._poll_hardware_driver()
        except Exception as e:
            self.log_error(e, "Error in NFC polling")
            await self.broadcast_websocket_event("error", {
                "message": f"Polling error: {str(e)}"
            })
        finally:
            self.polling_active = False
    
    async def _mock_polling(self):
        """Mock polling for testing without hardware"""
        self.polling_active = True
        mock_tags = [
            {"uid": "04:52:3A:B1:2C:80:00", "text": "Hello World"},
            {"uid": "04:A1:B2:C3:D4:E5:F6", "text": "Test Tag"},
        ]
        current_tag = None
        
        while self.polling_active:
            try:
                if current_tag is None:
                    # Simulate tag detection
                    import random
                    tag = random.choice(mock_tags)
                    current_tag = tag
                    await self.broadcast_websocket_event("nfc_detected", {
                        "uid": tag["uid"],
                        "technology": "Mock",
                        "text": tag["text"]
                    })
                    self.logger.info(f"Mock NFC tag detected: {tag['uid']}")
                else:
                    # Simulate tag removal after 5 seconds
                    await asyncio.sleep(5)
                    if current_tag:
                        await self.broadcast_websocket_event("nfc_removed", {
                            "uid": current_tag["uid"]
                        })
                        self.logger.info(f"Mock NFC tag removed: {current_tag['uid']}")
                        current_tag = None
                
                await asyncio.sleep(3)  # Wait before next detection
            except Exception as e:
                self.log_error(e, "Mock polling error")
                await asyncio.sleep(1)
    
    async def _poll_pico_bridge(self):
        """Poll using Pico bridge serial commands"""
        try:
            # Send POLL command to start continuous polling
            if hasattr(self.nfc_reader_instance, 'serial_port') and self.nfc_reader_instance.serial_port:
                self.nfc_reader_instance.serial_port.write("POLL\n".encode())
                
                while self.polling_active:
                    # Read lines from serial and parse NFC events
                    if self.nfc_reader_instance.serial_port.in_waiting > 0:
                        try:
                            line = self.nfc_reader_instance.serial_port.readline().decode().strip()
                            if line:
                                await self._parse_nfc_event(line)
                        except Exception as e:
                            self.log_error(e, "Error reading serial line")
                    
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            self.log_error(e, "Error in Pico bridge polling")
        finally:
            # Send ENDPOLL to stop polling
            try:
                if hasattr(self.nfc_reader_instance, 'serial_port') and self.nfc_reader_instance.serial_port:
                    self.nfc_reader_instance.serial_port.write("ENDPOLL\n".encode())
            except:
                pass
    
    async def _poll_hardware_driver(self):
        """Poll using hardware driver (basic implementation)"""
        while self.polling_active:
            try:
                # Basic tag detection using hardware driver
                if self.nfc_reader_instance.is_tag_present():
                    tag_info = self.nfc_reader_instance.get_tag_info()
                    if tag_info:
                        await self.broadcast_websocket_event("nfc_detected", {
                            "uid": tag_info.get("uid"),
                            "technology": tag_info.get("technology_name"),
                            "text": tag_info.get("text", "")
                        })
                        
                        # Wait for tag removal
                        while self.nfc_reader_instance.is_tag_present() and self.polling_active:
                            await asyncio.sleep(0.5)
                        
                        await self.broadcast_websocket_event("nfc_removed", {
                            "uid": tag_info.get("uid")
                        })
                
                await asyncio.sleep(0.5)
            except Exception as e:
                self.log_error(e, "Error in hardware driver polling")
                await asyncio.sleep(1)
    
    async def _parse_nfc_event(self, line: str):
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
                    
                    await self.broadcast_websocket_event("nfc_detected", {
                        "uid": tag_id,
                        "protocol": protocol,
                        "technology": tech,
                        "text": message
                    })
            
            elif line.startswith("OK:LEAVE:"):
                # Parse: OK:LEAVE:ID
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    tag_id = parts[2]
                    
                    await self.broadcast_websocket_event("nfc_removed", {
                        "uid": tag_id
                    })
            
            elif line.startswith("POLLEND"):
                await self.broadcast_websocket_event("poll_ended", {
                    "message": "Polling session ended"
                })
                
        except Exception as e:
            self.log_error(e, f"Error parsing NFC event '{line}'")
    
    async def stop_nfc_polling(self):
        """Stop NFC polling"""
        self.polling_active = False
        
        if self.polling_task and not self.polling_task.done():
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        
        self.polling_task = None
    
    def _register_nfc_endpoints(self):
        """Register all NFC-specific endpoints"""
        
        @self.router.get("/ping", response_model=NFCPingResponse)
        async def ping():
            """Ping endpoint to check if NFC system is available"""
            return NFCPingResponse(
                success=True,
                message="NFC API is running",
                initialized=self.nfc_reader_instance is not None
            )
        
        @self.router.post("/enable", response_model=NFCEnableDisableResponse)
        async def enable_polling():
            """Enable continuous NFC polling and stream events via WebSocket"""
            try:
                if not NFC_HARDWARE_AVAILABLE:
                    self.logger.info("Starting mock NFC polling for testing")
                else:
                    self._check_nfc_available()
                
                if self.polling_active:
                    return NFCEnableDisableResponse(
                        success=True,
                        message="NFC polling is already active"
                    )
                
                # Start polling in background task
                self.polling_task = asyncio.create_task(self.start_nfc_polling())
                
                # Give it a moment to start
                await asyncio.sleep(0.1)
                
                return NFCEnableDisableResponse(
                    success=True,
                    message="NFC polling enabled successfully"
                )
                
            except Exception as e:
                self.log_error(e, "Error enabling NFC polling")
                return NFCEnableDisableResponse(
                    success=False,
                    message=f"Error enabling NFC polling: {str(e)}"
                )
        
        @self.router.post("/disable", response_model=NFCEnableDisableResponse)
        async def disable_polling():
            """Disable continuous NFC polling"""
            try:
                if not self.polling_active:
                    return NFCEnableDisableResponse(
                        success=True,
                        message="NFC polling is already inactive"
                    )
                
                await self.stop_nfc_polling()
                
                return NFCEnableDisableResponse(
                    success=True,
                    message="NFC polling disabled successfully"
                )
                
            except Exception as e:
                self.log_error(e, "Error disabling NFC polling")
                return NFCEnableDisableResponse(
                    success=False,
                    message=f"Error disabling NFC polling: {str(e)}"
                )
        
        @self.router.post("/write", response_model=NFCWriteResponse)
        async def write_tag(request: NFCWriteRequest):
            """Write text to an NFC tag"""
            if not NFC_HARDWARE_AVAILABLE:
                # Mock write operation
                self.logger.info(f"Mock NFC write: '{request.text}'")
                return NFCWriteResponse(
                    success=True,
                    message=f"Mock write: '{request.text}' to NFC tag"
                )
            
            self._check_nfc_available()
            
            try:
                if NFC_TYPE == "pico_bridge":
                    # Use Pico bridge WRITE command
                    if hasattr(self.nfc_reader_instance, 'serial_port') and self.nfc_reader_instance.serial_port:
                        command = f"WRITE:{request.text}\n"
                        self.nfc_reader_instance.serial_port.write(command.encode())
                        
                        # Wait for response
                        start_time = time.time()
                        while time.time() - start_time < 10:  # 10 second timeout
                            if self.nfc_reader_instance.serial_port.in_waiting > 0:
                                try:
                                    line = self.nfc_reader_instance.serial_port.readline().decode().strip()
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
                                    self.log_error(e, "Error reading write response")
                            
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
                    success = self.nfc_reader_instance.write_text(request.text)
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
                self.log_error(e, "Error writing to NFC tag")
                return NFCWriteResponse(
                    success=False,
                    message=f"Error writing to NFC tag: {str(e)}"
                )
    
    async def websocket_handler(self, websocket: WebSocket):
        """Custom WebSocket handler for NFC real-time events"""
        await self.websocket_manager.connect(websocket)
        
        try:
            # Send initial status
            await websocket.send_json({
                "type": "nfc_status",
                "cog": self.name,
                "status": self.status,
                "polling_active": self.polling_active,
                "hardware_available": NFC_HARDWARE_AVAILABLE,
                "hardware_type": NFC_TYPE
            })
            
            # Keep connection alive and handle client messages
            while True:
                try:
                    data = await websocket.receive_text()
                    await self.handle_websocket_message(websocket, data)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    self.logger.warning(f"NFC WebSocket message error: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"NFC WebSocket handler error: {e}")
        finally:
            self.websocket_manager.disconnect(websocket)
    
    async def handle_websocket_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket messages for NFC commands"""
        try:
            import json
            data = json.loads(message)
            command = data.get("command")
            
            if command == "start_polling":
                if not self.polling_active:
                    self.polling_task = asyncio.create_task(self.start_nfc_polling())
                    await websocket.send_json({
                        "type": "command_response",
                        "command": "start_polling",
                        "success": True,
                        "message": "NFC polling started"
                    })
                else:
                    await websocket.send_json({
                        "type": "command_response",
                        "command": "start_polling",
                        "success": False,
                        "message": "Polling already active"
                    })
            
            elif command == "stop_polling":
                if self.polling_active:
                    await self.stop_nfc_polling()
                    await websocket.send_json({
                        "type": "command_response",
                        "command": "stop_polling",
                        "success": True,
                        "message": "NFC polling stopped"
                    })
                else:
                    await websocket.send_json({
                        "type": "command_response",
                        "command": "stop_polling",
                        "success": False,
                        "message": "Polling already inactive"
                    })
            
            elif command == "status":
                await websocket.send_json({
                    "type": "status_response",
                    "status": self.status,
                    "polling_active": self.polling_active,
                    "hardware_available": NFC_HARDWARE_AVAILABLE,
                    "error_count": self.error_count
                })
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown command: {command}"
                })
                
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON message"
            })
        except Exception as e:
            self.log_error(e, "Error handling WebSocket message")
            await websocket.send_json({
                "type": "error",
                "message": f"Error processing command: {str(e)}"
            })
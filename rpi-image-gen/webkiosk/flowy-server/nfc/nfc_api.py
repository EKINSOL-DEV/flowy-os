#!/usr/bin/env python3
"""
NFC API Server
FastAPI server providing NFC read/write operations via ST25R3916
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager

from st25r3916 import ST25R3916, ST25R3916Error
from nfc_reader import NFCReader


# Global NFC reader instance
nfc_reader: Optional[NFCReader] = None
st25r3916: Optional[ST25R3916] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global nfc_reader, st25r3916
    
    # Startup
    logger.info("Initializing NFC reader...")
    try:
        st25r3916 = ST25R3916(
            spi_bus=0,   # ST25R3916 is on SPI bus 0
            spi_device=0,
            rst_pin=22,  # GPIO 22 for reset
            irq_pin=17   # GPIO 17 for interrupt
        )
        st25r3916.initialize()
        
        nfc_reader = NFCReader(st25r3916)
        nfc_reader.initialize()
        
        logger.info("NFC reader initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize NFC reader: {e}")
        nfc_reader = None
        st25r3916 = None
    
    yield
    
    # Shutdown
    if nfc_reader:
        nfc_reader.stop_reading()
    if st25r3916:
        st25r3916.cleanup()
    logger.info("NFC reader shut down")


PORT = 10001

# Create logs directory if it doesn't exist
log_dir = '/flowy/logs/nfc'
os.makedirs(log_dir, exist_ok=True)

# Set up logging
log_file = os.path.join(log_dir, 'nfc_api.log')
handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger("nfc_api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Flowy NFC API",
    description="API for NFC tag reading and writing using ST25R3916",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_nfc_available():
    """Check if NFC reader is available"""
    if not nfc_reader or not st25r3916:
        raise HTTPException(status_code=503, detail="NFC reader not available")


@app.get("/status", summary="Get NFC Reader Status",
         description="Check if the NFC reader is initialized and ready")
def get_nfc_status():
    """Get NFC reader status"""
    logger.info("Getting NFC reader status")
    
    try:
        if not nfc_reader or not st25r3916:
            return {
                "status": "unavailable",
                "initialized": False,
                "error": "NFC reader not initialized"
            }
        
        # Try to read a register to test communication
        chip_id = st25r3916.read_register(0x00)  # Read IO_CONF1 register
        
        return {
            "status": "ready",
            "initialized": True,
            "chip_communication": "ok",
            "chip_id_register": f"0x{chip_id:02X}"
        }
        
    except Exception as e:
        logger.error(f"Error getting NFC status: {e}")
        return {
            "status": "error",
            "initialized": False,
            "error": str(e)
        }


@app.get("/detect", summary="Detect NFC Tag",
         description="Detect and identify an NFC tag in the field")
def detect_nfc_tag(timeout: float = 2.0):
    """Detect NFC tag"""
    check_nfc_available()
    logger.info("Detecting NFC tag")
    
    try:
        tag = nfc_reader.detect_tag(timeout=timeout)
        
        if tag:
            tag_info = {
                "detected": True,
                "uid": tag.uid_str,
                "type": tag.tag_type,
                "uid_bytes": tag.uid,
                "size": tag.size
            }
            logger.info(f"NFC tag detected: UID={tag.uid_str}, Type={tag.tag_type}")
            return tag_info
        else:
            logger.info("No NFC tag detected")
            return {
                "detected": False,
                "message": "No NFC tag found in field"
            }
            
    except Exception as e:
        logger.error(f"Error detecting NFC tag: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@app.get("/tag/info", summary="Get Current Tag Info",
         description="Get information about the currently detected tag")
def get_current_tag_info():
    """Get current tag information"""
    check_nfc_available()
    logger.info("Getting current tag info")
    
    try:
        tag_info = nfc_reader.get_tag_info()
        
        if tag_info:
            logger.info(f"Current tag info: UID={tag_info['uid']}")
            return tag_info
        else:
            return {
                "present": False,
                "message": "No tag currently selected"
            }
            
    except Exception as e:
        logger.error(f"Error getting tag info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tag info: {str(e)}")


@app.post("/tag/read", summary="Read NFC Tag Block",
          description="Read a specific block from the current NFC tag")
def read_tag_block(
    block_number: int = Body(..., description="Block number to read (0-based)"),
):
    """Read block from NFC tag"""
    check_nfc_available()
    logger.info(f"Reading block {block_number} from NFC tag")
    
    try:
        if not nfc_reader.current_tag:
            raise HTTPException(status_code=400, detail="No tag detected. Call /detect first.")
        
        block_data = nfc_reader.read_block(block_number)
        
        if block_data is not None:
            return {
                "success": True,
                "block_number": block_number,
                "data": block_data,
                "data_hex": ''.join(f'{b:02X}' for b in block_data),
                "data_ascii": ''.join(chr(b) if 32 <= b <= 126 else '.' for b in block_data)
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to read block")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading block {block_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Read failed: {str(e)}")


@app.post("/tag/write", summary="Write NFC Tag Block",
          description="Write data to a specific block of the current NFC tag")
def write_tag_block(
    block_number: int = Body(..., description="Block number to write (0-based)"),
    data: List[int] = Body(..., description="Data bytes to write (max 16 bytes)"),
):
    """Write block to NFC tag"""
    check_nfc_available()
    logger.info(f"Writing block {block_number} to NFC tag")
    
    try:
        if not nfc_reader.current_tag:
            raise HTTPException(status_code=400, detail="No tag detected. Call /detect first.")
        
        # Check data length based on tag type
        max_bytes = 4 if nfc_reader.current_tag.tag_type in ["MIFARE Ultralight", "NTAG"] else 16
        
        if len(data) > max_bytes:
            raise HTTPException(status_code=400, detail=f"Data too long. Maximum {max_bytes} bytes for {nfc_reader.current_tag.tag_type}.")
        
        # Don't pad for Ultralight/NTAG - they use exactly 4 bytes
        # Padding is handled in the tag-specific implementation
        
        success = nfc_reader.write_block(block_number, data)
        
        if success:
            logger.info(f"Successfully wrote block {block_number}")
            return {
                "success": True,
                "block_number": block_number,
                "bytes_written": len(data),
                "message": "Block written successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to write block")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error writing block {block_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Write failed: {str(e)}")


@app.post("/tag/halt", summary="Halt Current Tag",
          description="Send halt command to the current tag")
def halt_current_tag():
    """Halt current NFC tag"""
    check_nfc_available()
    logger.info("Halting current NFC tag")
    
    try:
        nfc_reader.halt_tag()
        return {
            "success": True,
            "message": "Tag halted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error halting tag: {e}")
        raise HTTPException(status_code=500, detail=f"Halt failed: {str(e)}")


@app.post("/field/on", summary="Turn RF Field On",
          description="Turn on the NFC RF field")
def turn_field_on():
    """Turn NFC field on"""
    check_nfc_available()
    logger.info("Turning NFC field on")
    
    try:
        st25r3916.field_on()
        return {
            "success": True,
            "message": "NFC field turned on"
        }
        
    except Exception as e:
        logger.error(f"Error turning field on: {e}")
        raise HTTPException(status_code=500, detail=f"Field on failed: {str(e)}")


@app.post("/field/off", summary="Turn RF Field Off",
          description="Turn off the NFC RF field")
def turn_field_off():
    """Turn NFC field off"""
    check_nfc_available()
    logger.info("Turning NFC field off")
    
    try:
        st25r3916.field_off()
        return {
            "success": True,
            "message": "NFC field turned off"
        }
        
    except Exception as e:
        logger.error(f"Error turning field off: {e}")
        raise HTTPException(status_code=500, detail=f"Field off failed: {str(e)}")


@app.get("/registers/{register}", summary="Read Register",
         description="Read a specific ST25R3916 register (for debugging)")
def read_register(register: int):
    """Read ST25R3916 register"""
    check_nfc_available()
    
    if register < 0 or register > 0xFF:
        raise HTTPException(status_code=400, detail="Register address must be 0x00-0xFF")
    
    try:
        value = st25r3916.read_register(register)
        logger.debug(f"Read register 0x{register:02X} = 0x{value:02X}")
        
        return {
            "register": f"0x{register:02X}",
            "value": f"0x{value:02X}",
            "decimal": value,
            "binary": f"0b{value:08b}"
        }
        
    except Exception as e:
        logger.error(f"Error reading register 0x{register:02X}: {e}")
        raise HTTPException(status_code=500, detail=f"Register read failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import os

    is_development = os.getenv("ENVIRONMENT", "production") == "development"
    logger.info(f"NFC API Server is listening on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=is_development)
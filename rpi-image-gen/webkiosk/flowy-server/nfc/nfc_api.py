#!/usr/bin/env python3
"""
FastAPI NFC API Server

Provides HTTP endpoints for NFC tag reading and writing operations using the nfc_reader module.
"""

import sys
import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# nfc_reader should be installed system-wide by nfc.sh
# No need to modify sys.path

try:
    import nfc_reader
    from nfc_reader import NFCReader, NFCError, NFCInitializationError
except ImportError as e:
    print(f"Error importing nfc_reader: {e}")
    print("Make sure nfc_reader.py and nfc_native.so are available in /home/builder/flowy-os/output/")
    sys.exit(1)

# Global NFC reader instance
nfc_reader_instance: Optional[NFCReader] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for NFC initialization and cleanup"""
    global nfc_reader_instance
    
    # Startup
    try:
        nfc_reader_instance = NFCReader(auto_cleanup=True)
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

# Pydantic models for request/response
class NFCReadRequest(BaseModel):
    timeout: float = Field(default=10.0, ge=0.1, le=300.0, description="Timeout in seconds")

class NFCWriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Text to write to NFC tag")
    language_code: str = Field(default="en", description="Language code")
    timeout: float = Field(default=10.0, ge=0.1, le=300.0, description="Timeout in seconds")

class NFCMultiReadRequest(BaseModel):
    min_tags: int = Field(default=2, ge=1, le=10, description="Minimum number of tags to read")
    timeout: float = Field(default=30.0, ge=0.1, le=300.0, description="Timeout in seconds")

class NFCTagResponse(BaseModel):
    text: Optional[str] = None
    language: Optional[str] = None
    uid: Optional[str] = None
    technology_name: Optional[str] = None

class NFCReadResponse(BaseModel):
    success: bool
    data: Optional[NFCTagResponse] = None
    message: str

class NFCMultiReadResponse(BaseModel):
    success: bool
    data: Optional[List[NFCTagResponse]] = None
    count: int = 0
    message: str

class NFCWriteResponse(BaseModel):
    success: bool
    message: str

class NFCStatusResponse(BaseModel):
    initialized: bool
    discovery_active: bool
    tag_present: bool
    num_tags: int

# Utility function to check NFC availability
def check_nfc_available():
    if nfc_reader_instance is None:
        raise HTTPException(status_code=503, detail="NFC reader not initialized")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "nfc_available": nfc_reader_instance is not None}

@app.get("/status", response_model=NFCStatusResponse)
async def get_status():
    """Get current NFC reader status"""
    check_nfc_available()
    
    return NFCStatusResponse(
        initialized=nfc_reader_instance._initialized,
        discovery_active=nfc_reader_instance.discovery_active,
        tag_present=nfc_reader_instance.is_tag_present(),
        num_tags=nfc_reader_instance.get_num_tags()
    )

@app.post("/read", response_model=NFCReadResponse)
async def read_tag(request: NFCReadRequest):
    """Read text from a single NFC tag"""
    check_nfc_available()
    
    try:
        # Start discovery if not already active
        if not nfc_reader_instance.discovery_active:
            nfc_reader_instance.start_discovery()
        
        # Wait for tag with text
        result = nfc_reader_instance.wait_for_tag(timeout=request.timeout)
        
        if result:
            # Get additional tag info
            tag_info = nfc_reader_instance.get_tag_info() or {}
            
            tag_data = NFCTagResponse(
                text=result.get('text'),
                language=result.get('language'),
                uid=tag_info.get('uid'),
                technology_name=tag_info.get('technology_name')
            )
            
            return NFCReadResponse(
                success=True,
                data=tag_data,
                message="Successfully read NFC tag"
            )
        else:
            return NFCReadResponse(
                success=False,
                message=f"No NFC tag with text found within {request.timeout} seconds"
            )
            
    except Exception as e:
        return NFCReadResponse(
            success=False,
            message=f"Error reading NFC tag: {str(e)}"
        )

@app.post("/read/multiple", response_model=NFCMultiReadResponse)
async def read_multiple_tags(request: NFCMultiReadRequest):
    """Read text from multiple NFC tags"""
    check_nfc_available()
    
    try:
        # Start discovery if not already active
        if not nfc_reader_instance.discovery_active:
            nfc_reader_instance.start_discovery()
        
        # Wait for multiple tags
        results = nfc_reader_instance.wait_for_multiple_tags(
            min_tags=request.min_tags,
            timeout=request.timeout
        )
        
        if results:
            tag_responses = []
            for result in results:
                tag_data = NFCTagResponse(
                    text=result.get('text'),
                    language=result.get('language'),
                    uid=result.get('uid'),
                    technology_name=result.get('technology_name')
                )
                tag_responses.append(tag_data)
            
            return NFCMultiReadResponse(
                success=True,
                data=tag_responses,
                count=len(tag_responses),
                message=f"Successfully read {len(tag_responses)} NFC tags"
            )
        else:
            return NFCMultiReadResponse(
                success=False,
                count=0,
                message=f"Found fewer than {request.min_tags} NFC tags within {request.timeout} seconds"
            )
            
    except Exception as e:
        return NFCMultiReadResponse(
            success=False,
            count=0,
            message=f"Error reading multiple NFC tags: {str(e)}"
        )

@app.post("/write", response_model=NFCWriteResponse)
async def write_tag(request: NFCWriteRequest):
    """Write text to an NFC tag"""
    check_nfc_available()
    
    try:
        # Start discovery if not already active
        if not nfc_reader_instance.discovery_active:
            nfc_reader_instance.start_discovery()
        
        # Wait for tag and write text
        start_time = time.time()
        while time.time() - start_time < request.timeout:
            if nfc_reader_instance.is_tag_present():
                success = nfc_reader_instance.write_text(request.text, request.language_code)
                if success:
                    return NFCWriteResponse(
                        success=True,
                        message=f"Successfully wrote text '{request.text}' to NFC tag"
                    )
                else:
                    return NFCWriteResponse(
                        success=False,
                        message="Failed to write text to NFC tag"
                    )
            await asyncio.sleep(0.1)
        
        return NFCWriteResponse(
            success=False,
            message=f"No NFC tag found within {request.timeout} seconds"
        )
        
    except Exception as e:
        return NFCWriteResponse(
            success=False,
            message=f"Error writing to NFC tag: {str(e)}"
        )

@app.get("/info")
async def get_tag_info():
    """Get detailed information about currently detected NFC tags"""
    check_nfc_available()
    
    try:
        # Start discovery if not already active
        if not nfc_reader_instance.discovery_active:
            nfc_reader_instance.start_discovery()
        
        num_tags = nfc_reader_instance.get_num_tags()
        
        if num_tags == 0:
            return {
                "success": False,
                "message": "No NFC tags detected",
                "count": 0,
                "tags": []
            }
        
        # Get info for all tags
        all_tags_info = nfc_reader_instance.get_all_tags_info() or []
        
        return {
            "success": True,
            "message": f"Found {num_tags} NFC tag(s)",
            "count": num_tags,
            "tags": all_tags_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting tag info: {str(e)}",
            "count": 0,
            "tags": []
        }

@app.post("/discovery/start")
async def start_discovery():
    """Manually start NFC tag discovery"""
    check_nfc_available()
    
    try:
        if not nfc_reader_instance.discovery_active:
            nfc_reader_instance.start_discovery()
            return {"success": True, "message": "NFC discovery started"}
        else:
            return {"success": True, "message": "NFC discovery already active"}
    except Exception as e:
        return {"success": False, "message": f"Error starting discovery: {str(e)}"}

@app.post("/discovery/stop")
async def stop_discovery():
    """Manually stop NFC tag discovery"""
    check_nfc_available()
    
    try:
        if nfc_reader_instance.discovery_active:
            nfc_reader_instance.stop_discovery()
            return {"success": True, "message": "NFC discovery stopped"}
        else:
            return {"success": True, "message": "NFC discovery already inactive"}
    except Exception as e:
        return {"success": False, "message": f"Error stopping discovery: {str(e)}"}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NFC API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=10001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    print(f"Starting NFC API Server on {args.host}:{args.port}")
    
    uvicorn.run(
        "nfc_api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
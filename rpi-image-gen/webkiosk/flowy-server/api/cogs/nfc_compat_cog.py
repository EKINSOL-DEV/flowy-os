"""
NFC Compat Cog
- Mirrors the old API's WebSocket message types and control flow.
- Uses prefix /nfc2 to avoid conflict with existing /nfc cog; change to "/nfc" if replacing.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, Set, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

class NFCWriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Text to write to NFC tag")

class NFCWriteResponse(BaseModel):
    success: bool

class NFCEnableDisableResponse(BaseModel):
    success: bool
    polling_active: bool

class NFCPingResponse(BaseModel):
    success: bool
    initialized: bool
    polling_active: bool
    clients: int

router = APIRouter(prefix="/nfc", tags=["nfc"])

# ----- Reader management -----

_reader = None  # singleton reader
_polling_task: Optional[asyncio.Task] = None
_polling_active: bool = False
_use_pico_bridge: bool = False

# Tag presence tracking: uid -> last_seen_timestamp
_seen: Dict[str, float] = {}
_SEEN_TTL = 1.0  # seconds before we emit "leave" after last seen

# Connections
_clients: Set[WebSocket] = set()
_clients_lock: Optional[asyncio.Lock] = None

def _lock() -> asyncio.Lock:
    global _clients_lock
    if _clients_lock is None:
        _clients_lock = asyncio.Lock()
    return _clients_lock

def _import_reader_class():
    try:
        import pico_nfc_bridge as nfc
        _use_pico_bridge = True
    except Exception:
        try:
            import nfc_reader as nfc
            _use_pico_bridge = False
        except Exception as e:
            raise RuntimeError(f"Import error for both pico_nfc_bridge and nfc_reader: {e}")
    
    Reader = getattr(nfc, "PicoNFCReader", None) or getattr(nfc, "NFCReader", None)
    if Reader is None:
        raise RuntimeError("Reader class not found")
    return Reader, _use_pico_bridge

async def _ensure_reader():
    global _reader, _use_pico_bridge
    if _reader is not None:
        return _reader
    Reader, _use_pico_bridge = _import_reader_class()
    r = Reader()
    await run_in_threadpool(r.initialize)
    if hasattr(r, "start_discovery"):
        await run_in_threadpool(r.start_discovery)
    _reader = r
    return _reader

async def _stop_reader():
    global _reader
    r = _reader
    _reader = None
    if r is None:
        return
    try:
        if hasattr(r, "stop_discovery"):
            await run_in_threadpool(r.stop_discovery)
    except Exception:
        pass
    try:
        await run_in_threadpool(r.cleanup)
    except Exception:
        pass

# ----- Broadcasting -----

async def _broadcast(message: Dict[str, Any]):
    # Copy to avoid iteration issues if set mutates
    targets = list(_clients)
    for ws in targets:
        try:
            await ws.send_json(message)
        except Exception:
            # Drop dead connection
            async with _lock():
                _clients.discard(ws)

def _uid_from_tag(tag: Any) -> str:
    # Try common keys; else use json of object
    if isinstance(tag, dict):
        for k in ("uid", "id", "tag_id"):
            v = tag.get(k)
            if v is not None:
                return str(v)
        return json.dumps(tag, sort_keys=True)
    return str(tag)

# ----- Polling loop -----

async def _poll_pico_bridge(reader):
    """Poll using Pico bridge serial commands"""
    global _polling_active
    
    try:
        # Send POLL command to start continuous polling
        if hasattr(reader, 'serial_port') and reader.serial_port:
            reader.serial_port.write("POLL\n".encode())
            
            while _polling_active:
                # Read lines from serial and parse NFC events
                if reader.serial_port.in_waiting > 0:
                    try:
                        line = reader.serial_port.readline().decode().strip()
                        if line:
                            await _parse_nfc_event(line)
                    except Exception as e:
                        await _broadcast({"type": "error", "detail": f"Error reading serial: {e}"})
                
                await asyncio.sleep(0.1)
                
    except Exception as e:
        await _broadcast({"type": "error", "detail": f"Pico bridge polling error: {e}"})
    finally:
        # Send ENDPOLL to stop polling
        try:
            if hasattr(reader, 'serial_port') and reader.serial_port:
                reader.serial_port.write("ENDPOLL\n".encode())
        except:
            pass

async def _parse_nfc_event(line: str):
    """Parse NFC events from Pico bridge serial output"""
    global _seen
    try:
        if line.startswith("OK:ENTER:"):
            # Parse: OK:ENTER:PROTOCOL:TECH:ID:"MESSAGE"
            parts = line.split(":", 5)
            if len(parts) >= 6:
                protocol = parts[2]
                tech = parts[3]
                tag_id = parts[4]
                message = parts[5].strip('"')
                
                # Track for old API compatibility
                now = time.time()
                _seen[tag_id] = now
                
                await _broadcast({
                    "type": "tag",
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
                
                _seen.pop(tag_id, None)
                
                await _broadcast({
                    "type": "leave",
                    "data": {
                        "uid": tag_id
                    }
                })
        
        elif line.startswith("POLLEND"):
            await _broadcast({
                "type": "poll_ended",
                "message": "Polling session ended"
            })
            
    except Exception as e:
        await _broadcast({"type": "error", "detail": f"Error parsing NFC event '{line}': {e}"})

async def _poll_hardware_driver(reader):
    """Poll using hardware driver methods"""
    global _polling_active, _seen
    
    while _polling_active:
        # process() to drain serial if available
        proc = getattr(reader, "process", None)
        if callable(proc):
            try:
                await run_in_threadpool(proc)
            except Exception:
                # don't crash polling
                pass

        # Gather tags
        tags = None
        try:
            if hasattr(reader, "get_all_tags_info"):
                tags = await run_in_threadpool(reader.get_all_tags_info)
            elif hasattr(reader, "is_tag_present") and hasattr(reader, "get_tag_info"):
                present = await run_in_threadpool(reader.is_tag_present)
                if present:
                    info = await run_in_threadpool(reader.get_tag_info)
                    tags = [info] if info else []
            else:
                # No way to poll; back off and notify once
                await _broadcast({"type": "error", "detail": "Reader has no polling method"})
                await asyncio.sleep(0.5)
                continue
        except Exception as e:
            await _broadcast({"type": "error", "detail": str(e)})
            tags = None

        now = time.time()
        current_uids: Set[str] = set()

        if tags:
            for t in tags:
                if not isinstance(t, dict):
                    continue
                uid = _uid_from_tag(t)
                current_uids.add(uid)
                if uid not in _seen:
                    _seen[uid] = now
                    await _broadcast({"type": "tag", "data": t})
                else:
                    # refresh last seen
                    _seen[uid] = now

        # Emit "leave" for stale tags
        stale = [uid for uid, ts in _seen.items() if now - ts > _SEEN_TTL and uid not in current_uids]
        for uid in stale:
            await _broadcast({"type": "leave", "data": {"uid": uid}})
            _seen.pop(uid, None)

        await asyncio.sleep(0.10)

async def _poll_loop():
    global _polling_active, _seen
    await _broadcast({"type": "poll_started", "message": "Polling session started"})
    try:
        while _polling_active:
            # Initialize/ensure reader
            try:
                reader = await _ensure_reader()
            except Exception as e:
                await _broadcast({"type": "error", "detail": f"NFC init failed: {e}"})
                await asyncio.sleep(0.5)
                continue

            # Choose polling method based on reader type
            if _use_pico_bridge:
                await _poll_pico_bridge(reader)
            else:
                await _poll_hardware_driver(reader)
            
            break  # Exit loop after polling completes

    finally:
        await _broadcast({"type": "poll_ended", "message": "Polling session ended"})

# ----- HTTP endpoints -----

@router.get("/ping", response_model=NFCPingResponse)
async def ping():
    return NFCPingResponse(
        success=True,
        initialized=bool(_reader),
        polling_active=bool(_polling_active),
        clients=len(_clients),
    )

@router.post("/enable", response_model=NFCEnableDisableResponse)
async def enable():
    global _polling_task, _polling_active
    await _ensure_reader()
    if not _polling_active:
        _polling_active = True
        _polling_task = asyncio.create_task(_poll_loop())
    return NFCEnableDisableResponse(success=True, polling_active=True)

@router.post("/disable", response_model=NFCEnableDisableResponse)
async def disable():
    global _polling_task, _polling_active
    _polling_active = False
    if _polling_task:
        try:
            await _polling_task
        except Exception:
            pass
        _polling_task = None
    await _stop_reader()
    return NFCEnableDisableResponse(success=True, polling_active=False)

@router.post("/write", response_model=NFCWriteResponse)
async def write(request: NFCWriteRequest):
    reader = await _ensure_reader()
    write_fn = getattr(reader, "write_text", None) or getattr(reader, "write", None)
    if write_fn is None:
        raise HTTPException(status_code=501, detail="Reader has no write_text/write method")
    ok = await run_in_threadpool(write_fn, request.text)
    return NFCWriteResponse(success=bool(ok))

# ----- WebSocket -----

@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    # Accept immediately
    await ws.accept()

    # Register client
    async with _lock():
        _clients.add(ws)

    try:
        # Old API style initial status
        await ws.send_json({
            "type": "status",
            "data": {
                "connected": True,
                "nfc_available": _reader is not None,
                "polling_active": _polling_active,
            }
        })

        # Keepalive / commands
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=0.05)
                if msg == "ping":
                    await ws.send_json({"type": "pong"})
                    continue
                try:
                    obj = json.loads(msg)
                    cmd = obj.get("cmd")
                    if cmd == "ping":
                        await ws.send_json({"type": "pong"})
                    elif cmd == "enable":
                        await enable()
                        await ws.send_json({"type": "status", "data": {
                            "connected": True,
                            "nfc_available": True,
                            "polling_active": _polling_active,
                        }})
                    elif cmd == "disable":
                        await disable()
                        await ws.send_json({"type": "status", "data": {
                            "connected": True,
                            "nfc_available": bool(_reader),
                            "polling_active": _polling_active,
                        }})
                except json.JSONDecodeError:
                    # ignore/echo if you want: await ws.send_text(msg)
                    pass
            except asyncio.TimeoutError:
                # no client message; the background poller will broadcast to all clients
                pass

    except WebSocketDisconnect:
        pass
    finally:
        async with _lock():
            _clients.discard(ws)

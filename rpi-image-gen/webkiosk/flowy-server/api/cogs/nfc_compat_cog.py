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

router = APIRouter(prefix="/nfc2", tags=["nfc"])

# ----- Reader management -----

_reader = None  # singleton reader
_polling_task: Optional[asyncio.Task] = None
_polling_active: bool = False

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
    except Exception as e:
        raise RuntimeError(f"Import error for pico_nfc_bridge: {e}")
    Reader = getattr(nfc, "PicoNFCReader", None) or getattr(nfc, "NFCReader", None)
    if Reader is None:
        raise RuntimeError("PicoNFCReader (or NFCReader) class not found in pico_nfc_bridge")
    return Reader

async def _ensure_reader():
    global _reader
    if _reader is not None:
        return _reader
    Reader = _import_reader_class()
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
                    await _broadcast({"type": "error", "detail": "Reader has no polling method (get_all_tags_info or is_tag_present/get_tag_info)"})
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

    finally:
        await _broadcast({"type": "poll_ended", "message": "Polling session ended"})

# ----- HTTP endpoints -----

@router.get("/ping")
async def ping():
    return {
        "success": True,
        "initialized": bool(_reader),
        "polling_active": bool(_polling_active),
        "clients": len(_clients),
    }

@router.post("/enable")
async def enable():
    global _polling_task, _polling_active
    await _ensure_reader()
    if not _polling_active:
        _polling_active = True
        _polling_task = asyncio.create_task(_poll_loop())
    return {"success": True, "polling_active": True}

@router.post("/disable")
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
    return {"success": True, "polling_active": False}

@router.post("/write")
async def write(body: Dict[str, Any] = Body(...)):
    text = body.get("text")
    if not isinstance(text, str) or not text:
        raise HTTPException(status_code=400, detail="Body must include non-empty 'text'")
    reader = await _ensure_reader()
    write_fn = getattr(reader, "write_text", None) or getattr(reader, "write", None)
    if write_fn is None:
        raise HTTPException(status_code=501, detail="Reader has no write_text/write method")
    ok = await run_in_threadpool(write_fn, text)
    return {"success": bool(ok)}

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

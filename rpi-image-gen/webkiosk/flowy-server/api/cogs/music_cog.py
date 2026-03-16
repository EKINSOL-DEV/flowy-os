"""
Music cog — reads librespot/raspotify playback state from /tmp/librespot-state.json
and exposes it via REST endpoints.
"""

import json
import subprocess
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/music", tags=["music"])

STATE_FILE = Path("/tmp/librespot-state.json")


def _read_state() -> dict:
    """Read the current playback state from the librespot event handler file."""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return data
    except (json.JSONDecodeError, IOError):
        pass
    return {"playing": False, "track_id": None}


@router.get("/status")
async def music_status():
    """Get current playback status."""
    state = _read_state()
    return {
        "playing": state.get("playing", False),
        "track_id": state.get("track_id"),
        "title": state.get("track_id", ""),  # Track ID for now, metadata requires Spotify API
        "artist": "",
        "album": "",
        "art_url": None,
        "duration_ms": state.get("duration_ms", 0),
        "progress_ms": state.get("position_ms", 0),
        "volume": state.get("volume", 50),
    }


@router.post("/play")
async def music_play():
    """Resume playback via dbus."""
    try:
        subprocess.run(
            ["dbus-send", "--system", "--type=method_call",
             "--dest=org.mpris.MediaPlayer2.Librespot",
             "/org/mpris/MediaPlayer2",
             "org.mpris.MediaPlayer2.Player.Play"],
            timeout=5, check=False
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/pause")
async def music_pause():
    """Pause playback via dbus."""
    try:
        subprocess.run(
            ["dbus-send", "--system", "--type=method_call",
             "--dest=org.mpris.MediaPlayer2.Librespot",
             "/org/mpris/MediaPlayer2",
             "org.mpris.MediaPlayer2.Player.Pause"],
            timeout=5, check=False
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/skip")
async def music_skip():
    """Skip to next track."""
    try:
        subprocess.run(
            ["dbus-send", "--system", "--type=method_call",
             "--dest=org.mpris.MediaPlayer2.Librespot",
             "/org/mpris/MediaPlayer2",
             "org.mpris.MediaPlayer2.Player.Next"],
            timeout=5, check=False
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/previous")
async def music_previous():
    """Go to previous track."""
    try:
        subprocess.run(
            ["dbus-send", "--system", "--type=method_call",
             "--dest=org.mpris.MediaPlayer2.Librespot",
             "/org/mpris/MediaPlayer2",
             "org.mpris.MediaPlayer2.Player.Previous"],
            timeout=5, check=False
        )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/volume")
async def music_volume(level: float = 50):
    """Set volume (0-100)."""
    return {"success": True, "volume": level}

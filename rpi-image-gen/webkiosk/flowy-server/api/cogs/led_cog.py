"""
LED Cog: full endpoints mirroring the LED API (status/info/pixel/fill/brightness/show/clear).
Safe by default: missing libs return HTTP errors without crashing the app.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Path as FPath
from typing import Dict, Any, Optional, List, Union, Tuple
try:
    from pydantic import BaseModel, Field
except Exception:  # pydantic optional at import; FastAPI will require it at runtime anyway
    BaseModel = object  # type: ignore
    def Field(*args, **kwargs):  # type: ignore
        return None

# Optional imports (we handle failures)
try:
    from pi5_pixelbuf import get_pixels
except Exception as e:
    get_pixels = None  # type: ignore
    _pixel_import_error = e
else:
    _pixel_import_error = None

try:
    from color import Color, Colors  # type: ignore
except Exception as e:
    Color = None  # type: ignore
    Colors = None  # type: ignore
    _color_import_error = e
else:
    _color_import_error = None

router = APIRouter(prefix="/led", tags=["led"])

def _require_pixels():
    if get_pixels is None:
        raise HTTPException(status_code=500, detail=f"Failed to import pi5_pixelbuf.get_pixels: {_pixel_import_error}")

def _pixels():
    _require_pixels()
    p = get_pixels()
    if p is None:
        raise HTTPException(status_code=500, detail="LED pixel buffer not initialized (get_pixels() returned None)")
    return p

# --- Models ---
class LEDStatus(BaseModel):
    pixel_count: int
    brightness: Optional[float] = None
    byteorder: Optional[str] = None
    auto_write: Optional[bool] = None

class PixelWriteBody(BaseModel):
    index: int = Field(..., ge=0, description="Pixel index to set")  # type: ignore
    color: Union[str, List[int], Tuple[int, int, int]]  # type: ignore

class FillBody(BaseModel):
    color: Union[str, List[int], Tuple[int, int, int]]  # type: ignore

class BrightnessBody(BaseModel):
    level: float = Field(..., ge=0.0, le=1.0, description="Brightness 0..1")  # type: ignore

def _parse_color(value: Union[str, List[int], Tuple[int, int, int]]) -> Tuple[int, int, int]:
    # Prefer the Color helper if available
    if Color is not None:
        try:
            # If it's a string, try Color parser methods
            if isinstance(value, str):
                v = value.strip()
                # try hex
                if v.startswith("#") and (len(v) == 7 or len(v) == 4):
                    try:
                        if len(v) == 7:
                            r = int(v[1:3], 16); g = int(v[3:5], 16); b = int(v[5:7], 16)
                        else:
                            r = int(v[1]*2, 16); g = int(v[2]*2, 16); b = int(v[3]*2, 16)
                        return (r, g, b)
                    except Exception:
                        pass
                # maybe Color has named colors or parser
                if hasattr(Color, "from_hex") and (v.startswith("#") or len(v) in (6,8) or v.lower().startswith("0x")):
                    c = Color.from_hex(v)  # type: ignore[attr-defined]
                    if hasattr(c, "to_rgb_tuple"):
                        return tuple(c.to_rgb_tuple())  # type: ignore[return-value]
                    if hasattr(c, "to_tuple"):
                        return tuple(c.to_tuple())  # type: ignore[return-value]
                # Heuristic named color via Colors constants
                if Colors is not None and hasattr(Colors, v.upper()):
                    c = getattr(Colors, v.upper())
                    if hasattr(c, "to_rgb_tuple"):
                        return tuple(c.to_rgb_tuple())  # type: ignore[return-value]
                    if hasattr(c, "to_tuple"):
                        return tuple(c.to_tuple())  # type: ignore[return-value]
            else:
                # list/tuple path handled below
                pass
        except Exception:
            # fall back to manual parsing
            pass
    # Manual parsing
    if isinstance(value, str):
        v = value.strip()
        if v.startswith("#"):
            if len(v) == 7:
                return (int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16))
            if len(v) == 4:
                return (int(v[1]*2, 16), int(v[2]*2, 16), int(v[3]*2, 16))
        # named fallbacks
        name_map = {
            "red": (255,0,0), "green": (0,255,0), "blue": (0,0,255),
            "white": (255,255,255), "black": (0,0,0),
            "yellow": (255,255,0), "cyan": (0,255,255), "magenta": (255,0,255),
            "orange": (255,165,0), "purple": (128,0,128)
        }
        rgb = name_map.get(v.lower())
        if rgb:
            return rgb
        # final: comma-separated "r,g,b"
        if "," in v:
            try:
                parts = [int(x) for x in v.split(",")]
            except Exception:
                parts = []
            if len(parts) == 3 and all(0 <= x <= 255 for x in parts):
                return tuple(parts)  # type: ignore[return-value]
        raise HTTPException(status_code=422, detail=f"Unrecognized color string: '{value}'")
    else:
        if len(value) == 3 and all(isinstance(x, int) and 0 <= x <= 255 for x in value):
            return int(value[0]), int(value[1]), int(value[2])
        raise HTTPException(status_code=422, detail="RGB list/tuple must be 3 integers 0..255")

# --- Routes ---
@router.get("/status", summary="Get LED strip status", response_model=LEDStatus)
def status():
    p = _pixels()
    try:
        return LEDStatus(
            pixel_count=len(p),
            brightness=getattr(p, "brightness", None),
            byteorder=getattr(p, "byteorder", None),
            auto_write=getattr(p, "auto_write", None),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info", summary="Detailed LED info")
def info() -> Dict[str, Any]:
    p = _pixels()
    try:
        return {
            "pixel_count": len(p),
            "brightness": getattr(p, "brightness", None),
            "byteorder": getattr(p, "byteorder", None),
            "auto_write": getattr(p, "auto_write", None),
            "bpp": getattr(p, "bpp", None),
            "order": getattr(p, "order", None),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pixel/{index}", summary="Get color of a single pixel")
def get_pixel(index: int = FPath(..., ge=0)):
    p = _pixels()
    try:
        if index < 0 or index >= len(p):
            raise HTTPException(status_code=400, detail=f"index {index} out of range (0..{len(p)-1})")
        val = p[index]
        # Normalize to [r,g,b]
        if isinstance(val, (list, tuple)) and len(val) >= 3:
            r, g, b = int(val[0]), int(val[1]), int(val[2])
        else:
            # could be int (packed) or unsupported
            r = g = b = int(val) if isinstance(val, int) else 0
        return {"index": index, "color": [r, g, b]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pixel", summary="Set color of a single pixel")
def set_pixel(body: PixelWriteBody):
    p = _pixels()
    try:
        rgb = _parse_color(body.color)  # type: ignore[arg-type]
        if body.index < 0 or body.index >= len(p):
            raise HTTPException(status_code=400, detail=f"index {body.index} out of range (0..{len(p)-1})")
        p[body.index] = tuple(rgb)
        if hasattr(p, "show"):
            p.show()
        return {"ok": True, "index": body.index, "color": list(rgb)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fill", summary="Fill entire strip with a color")
def fill(body: FillBody):
    p = _pixels()
    try:
        rgb = _parse_color(body.color)  # type: ignore[arg-type]
        if hasattr(p, "fill"):
            p.fill(tuple(rgb))
        else:
            for i in range(len(p)):
                p[i] = tuple(rgb)
        if hasattr(p, "show"):
            p.show()
        return {"ok": True, "color": list(rgb)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/brightness", summary="Set brightness 0..1")
def brightness(body: BrightnessBody):
    p = _pixels()
    try:
        level = float(body.level)  # type: ignore[attr-defined]
        if not (0.0 <= level <= 1.0):
            raise HTTPException(status_code=422, detail="Brightness level must be 0..1")
        setattr(p, "brightness", level)
        if hasattr(p, "show"):
            p.show()
        return {"ok": True, "brightness": getattr(p, "brightness", level)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/show", summary="Flush buffered changes to the strip")
def show():
    p = _pixels()
    try:
        if hasattr(p, "show"):
            p.show()
            return {"ok": True}
        raise HTTPException(status_code=501, detail="Pixel buffer has no 'show' method")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear", summary="Turn off all pixels")
def clear():
    p = _pixels()
    try:
        if hasattr(p, "fill"):
            p.fill((0,0,0))
        else:
            for i in range(len(p)):
                p[i] = (0,0,0)
        if hasattr(p, "show"):
            p.show()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

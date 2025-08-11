import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union, Tuple, Optional
from pi5_pixelbuf import get_pixels
from color import Color, Colors

PORT = 10_002

# Create logs directory if it doesn't exist
log_dir = '/flowy/logs/led'
os.makedirs(log_dir, exist_ok=True)

# Set up logging
log_file = os.path.join(log_dir, 'led_api.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Flowy LED API",
    description="API for controlling NeoPixel/WS2812B LED strips on Raspberry Pi 5",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class PixelColor(BaseModel):
    r: int
    g: int 
    b: int
    w: Optional[int] = 0

class SetPixelRequest(BaseModel):
    index: int
    color: PixelColor

class LEDStatus(BaseModel):
    pixel_count: int
    brightness: float
    byteorder: str
    auto_write: bool

class LEDInfo(BaseModel):
    pixel_count: int
    byteorder: str
    bpp: int
    pin: str

# Get global pixels instance
pixels = get_pixels()


@app.get("/led/status", response_model=LEDStatus)
async def get_led_status():
    """Get current LED strip status"""
    try:
        return LEDStatus(
            pixel_count=len(pixels),
            brightness=pixels.brightness,
            byteorder=pixels.byteorder,
            auto_write=pixels.auto_write
        )
    except Exception as e:
        logger.error(f"Error getting LED status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/led/info", response_model=LEDInfo)
async def get_led_info():
    """Get LED strip information"""
    try:
        return LEDInfo(
            pixel_count=len(pixels),
            byteorder=pixels.byteorder,
            bpp=pixels.bpp,
            pin="D7"  # Default pin
        )
    except Exception as e:
        logger.error(f"Error getting LED info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/led/pixel/{index}")
async def get_pixel(index: int):
    """Get color of a specific pixel"""
    try:
        if index < 0 or index >= len(pixels):
            raise HTTPException(status_code=400, detail=f"Pixel index {index} out of range (0-{len(pixels)-1})")
        
        color = pixels[index]
        if len(color) == 3:
            return {"r": color[0], "g": color[1], "b": color[2]}
        else:
            return {"r": color[0], "g": color[1], "b": color[2], "w": color[3]}
    except Exception as e:
        logger.error(f"Error getting pixel {index}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/led/pixel")
async def set_pixel(request: SetPixelRequest):
    """Set color of a specific pixel"""
    try:
        if request.index < 0 or request.index >= len(pixels):
            raise HTTPException(status_code=400, detail=f"Pixel index {request.index} out of range (0-{len(pixels)-1})")
        
        # Validate color values
        color = request.color
        if not all(0 <= val <= 255 for val in [color.r, color.g, color.b]):
            raise HTTPException(status_code=400, detail="Color values must be between 0-255")
        
        if pixels.bpp == 4:
            pixels[request.index] = (color.r, color.g, color.b, color.w or 0)
        else:
            pixels[request.index] = (color.r, color.g, color.b)
        
        logger.info(f"Set pixel {request.index} to RGB({color.r}, {color.g}, {color.b})")
        return {"success": True, "message": f"Pixel {request.index} set to RGB({color.r}, {color.g}, {color.b})"}
    except Exception as e:
        logger.error(f"Error setting pixel {request.index}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/led/fill")
async def fill_pixels(color: PixelColor):
    """Fill all pixels with the same color"""
    try:
        # Validate color values
        if not all(0 <= val <= 255 for val in [color.r, color.g, color.b]):
            raise HTTPException(status_code=400, detail="Color values must be between 0-255")
        
        if pixels.bpp == 4:
            pixels.fill((color.r, color.g, color.b, color.w or 0))
        else:
            pixels.fill((color.r, color.g, color.b))
        
        logger.info(f"Filled all pixels with RGB({color.r}, {color.g}, {color.b})")
        return {"success": True, "message": f"All pixels filled with RGB({color.r}, {color.g}, {color.b})"}
    except Exception as e:
        logger.error(f"Error filling pixels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/led/brightness")
# async def set_brightness(brightness: float = Body(..., embed=True)):
#     """Set overall brightness (0.0 to 1.0) - seems to do nothing, use color values instead"""
#     try:
#         if not 0.0 <= brightness <= 1.0:
#             raise HTTPException(status_code=400, detail="Brightness must be between 0.0 and 1.0")
#         
#         pixels.brightness = brightness
#         logger.info(f"Set brightness to {brightness}")
#         return {"success": True, "message": f"Brightness set to {brightness}"}
#     except Exception as e:
#         logger.error(f"Error setting brightness: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/led/show")
async def show_pixels():
    """Apply changes to physical LEDs (display current buffer)"""
    try:
        pixels.show()
        logger.info("LED display updated")
        return {"success": True, "message": "LED display updated"}
    except Exception as e:
        logger.error(f"Error updating LED display: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/led/clear")
async def clear_pixels():
    """Turn off all LEDs (set to black)"""
    try:
        pixels.fill((0, 0, 0))
        pixels.show()
        logger.info("All LEDs cleared")
        return {"success": True, "message": "All LEDs cleared"}
    except Exception as e:
        logger.error(f"Error clearing LEDs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    try:
        import uvicorn
        logger.info(f"Starting Flowy LED API server on port {PORT}")
        
        pixels.fill(Colors.PURPLE)
        pixels.show()
        
        uvicorn.run("led_api:app", host="0.0.0.0", port=PORT, log_level="info")
    finally:
        pixels.fill(0)
        pixels.show()
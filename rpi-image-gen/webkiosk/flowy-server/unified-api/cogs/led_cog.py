"""
LED Cog for Flowy Unified API

Provides endpoints for controlling NeoPixel/WS2812B LED strips on Raspberry Pi 5.
Converted from the original LED API to use the cogs architecture.
"""

import sys
import os
from typing import List, Optional
from fastapi import HTTPException, Body
from pydantic import BaseModel

# Add the modules path for imports
modules_path = os.path.join(os.path.dirname(__file__), "../modules")
sys.path.insert(0, modules_path)

try:
    from pi5_pixelbuf import get_pixels
    from color import Color, Colors
    LED_HARDWARE_AVAILABLE = True
except ImportError as e:
    print(f"LED hardware not available: {e}")
    LED_HARDWARE_AVAILABLE = False
    
    # Mock the LED modules for testing
    class MockColors:
        PURPLE = (128, 0, 128)
        BLACK = (0, 0, 0)
        RED = (255, 0, 0)
        GREEN = (0, 255, 0)
        BLUE = (0, 0, 255)
    
    Colors = MockColors()
    
    def get_pixels():
        return None

from .base_cog import BaseCog

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

class LEDCog(BaseCog):
    """LED control cog for NeoPixel strips"""
    
    def __init__(self, name: str = "led"):
        super().__init__(name)
        self.pixels = None
        self.mock_pixels = None  # For testing without hardware
        
        # Register LED endpoints
        self._register_led_endpoints()
    
    async def initialize(self) -> bool:
        """Initialize the LED hardware"""
        try:
            if LED_HARDWARE_AVAILABLE:
                self.pixels = get_pixels()
                self.logger.info("LED hardware initialized successfully")
                self.status = "running"
                return True
            else:
                # Mock pixels for testing
                self.logger.warning("LED hardware not available, using mock pixels")
                self.mock_pixels = {
                    "pixel_count": 8,
                    "brightness": 1.0,
                    "byteorder": "GRB",
                    "auto_write": True,
                    "bpp": 3,
                    "pixels": [(0, 0, 0)] * 8
                }
                self.status = "running"
                return True
        except Exception as e:
            self.log_error(e, "LED initialization failed")
            self.status = "failed"
            return False
    
    async def shutdown(self):
        """Clean shutdown of LED hardware"""
        try:
            if self.pixels:
                # Turn off all LEDs
                self.pixels.fill((0, 0, 0))
                self.pixels.show()
                self.logger.info("LED hardware shut down, all LEDs turned off")
            elif self.mock_pixels:
                self.mock_pixels["pixels"] = [(0, 0, 0)] * self.mock_pixels["pixel_count"]
                self.logger.info("Mock LED pixels cleared")
        except Exception as e:
            self.log_error(e, "LED shutdown error")
    
    def get_capabilities(self) -> List[str]:
        """Return LED capabilities"""
        capabilities = [
            "led_control",
            "pixel_addressing",
            "color_control",
            "fill_operations",
            "status_monitoring"
        ]
        
        if LED_HARDWARE_AVAILABLE and self.pixels:
            capabilities.extend([
                "hardware_control",
                f"pixel_count_{len(self.pixels)}",
                f"color_depth_{self.pixels.bpp * 8}bit"
            ])
        elif self.mock_pixels:
            capabilities.extend([
                "mock_control",
                f"pixel_count_{self.mock_pixels['pixel_count']}",
                f"color_depth_{self.mock_pixels['bpp'] * 8}bit"
            ])
        
        return capabilities
    
    def _get_pixel_count(self) -> int:
        """Get the number of pixels"""
        if self.pixels:
            return len(self.pixels)
        elif self.mock_pixels:
            return self.mock_pixels["pixel_count"]
        else:
            return 0
    
    def _get_pixel(self, index: int):
        """Get color of a specific pixel"""
        if self.pixels:
            return self.pixels[index]
        elif self.mock_pixels:
            return self.mock_pixels["pixels"][index]
        else:
            raise Exception("No LED hardware available")
    
    def _set_pixel(self, index: int, color: tuple):
        """Set color of a specific pixel"""
        if self.pixels:
            self.pixels[index] = color
        elif self.mock_pixels:
            self.mock_pixels["pixels"][index] = color
        else:
            raise Exception("No LED hardware available")
    
    def _fill_pixels(self, color: tuple):
        """Fill all pixels with the same color"""
        if self.pixels:
            self.pixels.fill(color)
        elif self.mock_pixels:
            self.mock_pixels["pixels"] = [color] * self.mock_pixels["pixel_count"]
        else:
            raise Exception("No LED hardware available")
    
    def _show_pixels(self):
        """Apply changes to physical LEDs"""
        if self.pixels:
            self.pixels.show()
        elif self.mock_pixels:
            # Mock show operation
            pass
        else:
            raise Exception("No LED hardware available")
    
    def _register_led_endpoints(self):
        """Register all LED-specific endpoints"""
        
        @self.router.get("/status", response_model=LEDStatus)
        async def get_led_status():
            """Get current LED strip status"""
            try:
                if self.pixels:
                    return LEDStatus(
                        pixel_count=len(self.pixels),
                        brightness=self.pixels.brightness,
                        byteorder=self.pixels.byteorder,
                        auto_write=self.pixels.auto_write
                    )
                elif self.mock_pixels:
                    return LEDStatus(
                        pixel_count=self.mock_pixels["pixel_count"],
                        brightness=self.mock_pixels["brightness"],
                        byteorder=self.mock_pixels["byteorder"],
                        auto_write=self.mock_pixels["auto_write"]
                    )
                else:
                    raise HTTPException(status_code=503, detail="LED hardware not available")
            except Exception as e:
                self.log_error(e, "Error getting LED status")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/info", response_model=LEDInfo)
        async def get_led_info():
            """Get LED strip information"""
            try:
                if self.pixels:
                    return LEDInfo(
                        pixel_count=len(self.pixels),
                        byteorder=self.pixels.byteorder,
                        bpp=self.pixels.bpp,
                        pin="D7"  # Default pin
                    )
                elif self.mock_pixels:
                    return LEDInfo(
                        pixel_count=self.mock_pixels["pixel_count"],
                        byteorder=self.mock_pixels["byteorder"],
                        bpp=self.mock_pixels["bpp"],
                        pin="Mock"
                    )
                else:
                    raise HTTPException(status_code=503, detail="LED hardware not available")
            except Exception as e:
                self.log_error(e, "Error getting LED info")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/pixel/{index}")
        async def get_pixel(index: int):
            """Get color of a specific pixel"""
            try:
                pixel_count = self._get_pixel_count()
                if index < 0 or index >= pixel_count:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Pixel index {index} out of range (0-{pixel_count-1})"
                    )
                
                color = self._get_pixel(index)
                if len(color) == 3:
                    return {"r": color[0], "g": color[1], "b": color[2]}
                else:
                    return {"r": color[0], "g": color[1], "b": color[2], "w": color[3]}
            except Exception as e:
                self.log_error(e, f"Error getting pixel {index}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/pixel")
        async def set_pixel(request: SetPixelRequest):
            """Set color of a specific pixel"""
            try:
                pixel_count = self._get_pixel_count()
                if request.index < 0 or request.index >= pixel_count:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Pixel index {request.index} out of range (0-{pixel_count-1})"
                    )
                
                # Validate color values
                color = request.color
                if not all(0 <= val <= 255 for val in [color.r, color.g, color.b]):
                    raise HTTPException(status_code=400, detail="Color values must be between 0-255")
                
                # Set pixel color based on BPP
                bpp = getattr(self.pixels, 'bpp', 3) if self.pixels else self.mock_pixels.get('bpp', 3)
                if bpp == 4:
                    pixel_color = (color.r, color.g, color.b, color.w or 0)
                else:
                    pixel_color = (color.r, color.g, color.b)
                
                self._set_pixel(request.index, pixel_color)
                
                self.logger.info(f"Set pixel {request.index} to RGB({color.r}, {color.g}, {color.b})")
                return {
                    "success": True, 
                    "message": f"Pixel {request.index} set to RGB({color.r}, {color.g}, {color.b})"
                }
            except Exception as e:
                self.log_error(e, f"Error setting pixel {request.index}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/fill")
        async def fill_pixels(color: PixelColor):
            """Fill all pixels with the same color"""
            try:
                # Validate color values
                if not all(0 <= val <= 255 for val in [color.r, color.g, color.b]):
                    raise HTTPException(status_code=400, detail="Color values must be between 0-255")
                
                # Fill pixels based on BPP
                bpp = getattr(self.pixels, 'bpp', 3) if self.pixels else self.mock_pixels.get('bpp', 3)
                if bpp == 4:
                    pixel_color = (color.r, color.g, color.b, color.w or 0)
                else:
                    pixel_color = (color.r, color.g, color.b)
                
                self._fill_pixels(pixel_color)
                
                self.logger.info(f"Filled all pixels with RGB({color.r}, {color.g}, {color.b})")
                return {
                    "success": True, 
                    "message": f"All pixels filled with RGB({color.r}, {color.g}, {color.b})"
                }
            except Exception as e:
                self.log_error(e, "Error filling pixels")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/show")
        async def show_pixels():
            """Apply changes to physical LEDs (display current buffer)"""
            try:
                self._show_pixels()
                self.logger.info("LED display updated")
                return {"success": True, "message": "LED display updated"}
            except Exception as e:
                self.log_error(e, "Error updating LED display")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/clear")
        async def clear_pixels():
            """Turn off all LEDs (set to black)"""
            try:
                self._fill_pixels((0, 0, 0))
                self._show_pixels()
                self.logger.info("All LEDs cleared")
                return {"success": True, "message": "All LEDs cleared"}
            except Exception as e:
                self.log_error(e, "Error clearing LEDs")
                raise HTTPException(status_code=500, detail=str(e))
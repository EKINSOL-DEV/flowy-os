"""
Pi5Pixelbuf - Hardware integration for Raspberry Pi 5 NeoPixel/WS2812B LEDs
Lazy initialization version to avoid GPIO issues at import time.
"""
import sys
from color import Color, Colors
from pixelbuf_lite import PixelBuf

# Default configuration
DEFAULT_NUM_PIXELS = 5
DEFAULT_BYTEORDER = "RGB"

class Pi5Pixelbuf(PixelBuf):
    """
    Raspberry Pi 5 implementation of PixelBuf using adafruit_raspberry_pi5_neopixel_write.
    Uses lazy initialization to avoid GPIO issues at import time.
    """
    
    def __init__(self, pin_number, size, **kwargs):
        """
        Initialize Pi5 NeoPixel strip.
        
        :param pin_number: GPIO pin number (e.g., 7 for D7)
        :param size: Number of pixels
        :param kwargs: Additional arguments passed to PixelBuf
        """
        self._pin_number = pin_number
        self._pin = None
        self._board = None
        self._neopixel_write = None
        self._initialized = False
        super().__init__(size=size, **kwargs)
        
    def _lazy_init(self):
        """Initialize GPIO libraries only when actually needed."""
        if self._initialized:
            return True
            
        try:
            # Import GPIO libraries only when needed
            import board
            from adafruit_raspberry_pi5_neopixel_write import neopixel_write
            
            # Get the pin object
            if self._pin_number == 7:
                self._pin = board.D7
            elif self._pin_number == 18:
                self._pin = board.D18
            elif self._pin_number == 12:
                self._pin = board.D12
            elif self._pin_number == 10:
                self._pin = board.D10
            else:
                # Fallback to D7 if unsupported pin
                print(f"Warning: Pin {self._pin_number} not directly supported, using D7")
                self._pin = board.D7
                
            self._neopixel_write = neopixel_write
            self._initialized = True
            print(f"GPIO initialized successfully for pin {self._pin_number}")
            return True
            
        except Exception as e:
            print(f"GPIO initialization failed: {e}")
            return False
        
    def _transmit(self, buf):
        """
        Transmit buffer data to NeoPixel hardware.
        
        :param buf: Byte buffer containing pixel data
        """
        if not self._lazy_init():
            print("Warning: GPIO not available, skipping LED update")
            return
            
        try:
            self._neopixel_write(self._pin, buf)
        except Exception as e:
            print(f"LED transmission error: {e}")

def create_default_pixels():
    """
    Create a default Pi5Pixelbuf instance for testing.
    
    :return: Pi5Pixelbuf instance with default settings
    """
    return Pi5Pixelbuf(
        7,  # GPIO 7 (D7)
        DEFAULT_NUM_PIXELS, 
        auto_write=False,  # Manual control for API
        byteorder=DEFAULT_BYTEORDER
    )

# Global instance for API use
pixels = None

def get_pixels():
    """
    Get or create the global pixels instance.
    
    :return: Global Pi5Pixelbuf instance
    """
    global pixels
    if pixels is None:
        pixels = create_default_pixels()
    return pixels
"""
Pi5Pixelbuf - Hardware integration for Raspberry Pi 5 NeoPixel/WS2812B LEDs
"""
import board
from color import Color, Colors
from pixelbuf_lite import PixelBuf
from adafruit_raspberry_pi5_neopixel_write import neopixel_write

# Default configuration
DEFAULT_PIN = board.USB_DM
DEFAULT_NUM_PIXELS = 5
DEFAULT_BYTEORDER = "RGB"

class Pi5Pixelbuf(PixelBuf):
    """
    Raspberry Pi 5 implementation of PixelBuf using adafruit_raspberry_pi5_neopixel_write.
    
    Usage:
        from pi5_pixelbuf import Pi5Pixelbuf
        
        # Create LED strip
        pixels = Pi5Pixelbuf(board.D7, 10, auto_write=True)
        
        # Set colors
        pixels[0] = (255, 0, 0)     # Red
        pixels[1] = Colors.BLUE     # Blue
        pixels.fill(Colors.GREEN)   # All green
        pixels.show()               # Update display
    """
    
    def __init__(self, pin, size, **kwargs):
        """
        Initialize Pi5 NeoPixel strip.
        
        :param pin: GPIO pin (use board.D7, board.D18, etc.)
        :param size: Number of pixels
        :param kwargs: Additional arguments passed to PixelBuf
        """
        self._pin = pin
        super().__init__(size=size, **kwargs)
        
    def _transmit(self, buf):
        """
        Transmit buffer data to NeoPixel hardware.
        
        :param buf: Byte buffer containing pixel data
        """
        try:
            neopixel_write(self._pin, buf)
        except Exception as e:
            # Log error but don't crash the server
            print(f"LED transmission error: {e}")

def create_default_pixels():
    """
    Create a default Pi5Pixelbuf instance for testing.
    
    :return: Pi5Pixelbuf instance with default settings
    """
    return Pi5Pixelbuf(
        DEFAULT_PIN, 
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
"""
Color class with support for RGB, HSV, and HEX color representations.
"""
import colorsys
from typing import Union, Tuple


class Color:
    """
    A color representation supporting RGB, HSV, and HEX formats.
    
    Usage:
        # From RGB values (0-255)
        red = Color.from_rgb(255, 0, 0)
        
        # From HSV values (hue: 0-360, sat/val: 0-100)
        blue = Color.from_hsv(240, 100, 100)
        
        # From hex string
        green = Color.from_hex("#00FF00")
        
        # Get RGB tuple for LED strips
        rgb_tuple = red.rgb
        rgb_values = red.r, red.g, red.b
    """
    
    def __init__(self, r: int = 0, g: int = 0, b: int = 0):
        """Initialize with RGB values (0-255)."""
        self._r = max(0, min(255, int(r)))
        self._g = max(0, min(255, int(g))) 
        self._b = max(0, min(255, int(b)))
    
    @classmethod
    def from_rgb(cls, r: int, g: int, b: int) -> 'Color':
        """Create Color from RGB values (0-255)."""
        return cls(r, g, b)
    
    @classmethod
    def from_hsv(cls, h: float, s: float, v: float) -> 'Color':
        """
        Create Color from HSV values.
        
        :param h: Hue (0-360 degrees)
        :param s: Saturation (0-100%)
        :param v: Value/Brightness (0-100%)
        """
        # Convert to 0-1 range for colorsys
        h_norm = (h % 360) / 360.0
        s_norm = max(0, min(100, s)) / 100.0
        v_norm = max(0, min(100, v)) / 100.0
        
        r, g, b = colorsys.hsv_to_rgb(h_norm, s_norm, v_norm)
        return cls(int(r * 255), int(g * 255), int(b * 255))
    
    @classmethod
    def from_hex(cls, hex_string: str) -> 'Color':
        """
        Create Color from hex string.
        
        :param hex_string: Hex color like "#FF0000", "FF0000", or "0xFF0000"
        """
        hex_string = hex_string.strip()
        
        # Remove common prefixes
        if hex_string.startswith('#'):
            hex_string = hex_string[1:]
        elif hex_string.startswith('0x') or hex_string.startswith('0X'):
            hex_string = hex_string[2:]
        
        # Ensure 6 characters
        if len(hex_string) == 3:
            # Expand short form: "F0A" -> "FF00AA"
            hex_string = ''.join(c*2 for c in hex_string)
        elif len(hex_string) != 6:
            raise ValueError(f"Invalid hex color format: {hex_string}")
        
        try:
            value = int(hex_string, 16)
            r = (value >> 16) & 0xFF
            g = (value >> 8) & 0xFF
            b = value & 0xFF
            return cls(r, g, b)
        except ValueError as e:
            raise ValueError(f"Invalid hex color: {hex_string}") from e
    
    @property
    def r(self) -> int:
        """Red component (0-255)."""
        return self._r
    
    @property  
    def g(self) -> int:
        """Green component (0-255)."""
        return self._g
    
    @property
    def b(self) -> int:
        """Blue component (0-255)."""
        return self._b
    
    @property
    def rgb(self) -> Tuple[int, int, int]:
        """RGB tuple (r, g, b) with values 0-255."""
        return (self._r, self._g, self._b)
    
    @property
    def hsv(self) -> Tuple[float, float, float]:
        """HSV tuple (h, s, v) with h: 0-360, s/v: 0-100."""
        r_norm = self._r / 255.0
        g_norm = self._g / 255.0
        b_norm = self._b / 255.0
        
        h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
        return (h * 360, s * 100, v * 100)
    
    @property
    def hex(self) -> str:
        """Hex string representation like '#FF0000'."""
        return f"#{self._r:02X}{self._g:02X}{self._b:02X}"
    
    def __str__(self) -> str:
        return f"Color(r={self._r}, g={self._g}, b={self._b})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Color):
            return self.rgb == other.rgb
        return False
    
    def __iter__(self):
        """Allow unpacking: r, g, b = color"""
        yield self._r
        yield self._g  
        yield self._b


# Common colors as constants
class Colors:
    """Common color constants."""
    RED = Color.from_rgb(255, 0, 0)
    GREEN = Color.from_rgb(0, 255, 0)
    BLUE = Color.from_rgb(0, 0, 255)
    WHITE = Color.from_rgb(255, 255, 255)
    BLACK = Color.from_rgb(0, 0, 0)
    YELLOW = Color.from_rgb(255, 255, 0)
    CYAN = Color.from_rgb(0, 255, 255)
    MAGENTA = Color.from_rgb(255, 0, 255)
    ORANGE = Color.from_rgb(255, 165, 0)
    PURPLE = Color.from_rgb(128, 0, 128)
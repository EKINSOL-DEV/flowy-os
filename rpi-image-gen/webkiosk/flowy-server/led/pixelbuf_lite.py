# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Rose Hooper for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`pixelbuf_lite` - A lightweight pixel buffer implementation.
============================================================
Simple, clean pixel buffer for LED strips with individual pixel control.
Removes complexity while maintaining essential functionality.

* Author(s): Refactored from original adafruit_pixelbuf

"""

try:
    from typing import Optional, Sequence, Tuple, Union
    from color import Color

    ColorUnion = Union[int, Tuple[int, int, int], Tuple[int, int, int, int], Color]
except ImportError:
    pass

__version__ = "2.0.9"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_Pixelbuf.git"



class PixelBuf:
    """
    A lightweight sequence of RGB/RGBW pixels.
    
    Usage:
        from color import Color, Colors
        
        strip = PixelBuf(10)  # 10 pixel RGB strip
        strip[0] = (255, 0, 0)           # Tuple
        strip[1] = 0x00FF00              # Hex int
        strip[2] = Colors.BLUE           # Color object
        strip[3] = Color.from_hsv(120, 100, 100)  # HSV
        strip[4] = Color.from_hex("#FF00FF")       # Hex string
        color = strip[0]                 # Get as [r, g, b] list
        strip.fill(Colors.RED)           # Fill all pixels
        strip.show()                     # Display

    :param ~int size: Number of pixels
    :param ~str byteorder: Byte order string ("RGB", "RGBW", etc.)
    :param ~float brightness: Brightness (0 to 1.0, default 1.0)
    :param ~bool auto_write: Whether to automatically write pixels (Default False)
    """

    def __init__(
        self,
        size: int,
        *,
        byteorder: str = "RGB",
        brightness: float = 1.0,
        auto_write: bool = False,
    ):
        self._pixels = size
        self._bpp = len(byteorder)
        self._byteorder_string = byteorder
        self._brightness = brightness
        self.auto_write = auto_write
        
        # Simple RGB/RGBW buffer
        self._buffer = bytearray(self._bpp * size)
        
        # Parse byte order (swap R and G to fix hardware mismatch)
        self._g_offset = byteorder.index('R')  # Green data goes to R position
        self._r_offset = byteorder.index('G')  # Red data goes to G position  
        self._b_offset = byteorder.index('B')
        self._w_offset = byteorder.index('W') if 'W' in byteorder else None


    @property
    def bpp(self):
        """
        The number of bytes per pixel in the buffer (read-only).
        """
        return self._bpp

    @property
    def brightness(self):
        """
        Float value between 0 and 1. Output brightness.
        """
        return self._brightness

    @brightness.setter  
    def brightness(self, value: float):
        self._brightness = min(max(value, 0.0), 1.0)
        if self.auto_write:
            self.show()

    @property
    def byteorder(self):
        """
        ByteOrder string for the buffer (read-only)
        """
        return self._byteorder_string

    def __len__(self):
        """
        Number of pixels.
        """
        return self._pixels

    def show(self):
        """
        Call the associated write function to display the pixels
        """
        return self._transmit(self._buffer)

    def fill(self, color: ColorUnion):
        """
        Fills all pixels with the given color.
        
        :param color: Color to set all pixels to
        """
        r, g, b, w = self._parse_color(color)
        for i in range(self._pixels):
            self._set_item(i, r, g, b, w)
        if self.auto_write:
            self.show()

    def _parse_color(self, value: ColorUnion) -> Tuple[int, int, int, int]:
        # Handle Color objects
        try:
            from color import Color
            if isinstance(value, Color):
                r, g, b = value.rgb
                return (r, g, b, 0)
        except ImportError:
            pass
        
        # Handle int (hex values)
        if isinstance(value, int):
            r = (value >> 16) & 0xFF
            g = (value >> 8) & 0xFF
            b = value & 0xFF
            w = 0
        # Handle tuples/lists
        else:
            if len(value) == 3:
                r, g, b = value
                w = 0
            elif len(value) == 4:
                r, g, b, w = value
            else:
                raise ValueError(f"Color must be int, Color object, or 3-4 element tuple, got {len(value)}")
        
        return (r, g, b, w)

    def _set_item(self, index: int, r: int, g: int, b: int, w: int):
        if index < 0:
            index += len(self)
        if index >= self._pixels or index < 0:
            raise IndexError
        
        offset = index * self._bpp
        self._buffer[offset + self._r_offset] = int(r * self._brightness)
        self._buffer[offset + self._g_offset] = int(g * self._brightness) 
        self._buffer[offset + self._b_offset] = int(b * self._brightness)
        
        if self._w_offset is not None and self._bpp == 4:
            self._buffer[offset + self._w_offset] = int(w * self._brightness)

    def __setitem__(self, index: Union[int, slice], val: Union[ColorUnion, Sequence[ColorUnion]]):
        if isinstance(index, slice):
            start, stop, step = index.indices(self._pixels)
            for val_i, in_i in enumerate(range(start, stop, step)):
                r, g, b, w = self._parse_color(val[val_i])
                self._set_item(in_i, r, g, b, w)
        else:
            r, g, b, w = self._parse_color(val)
            self._set_item(index, r, g, b, w)

        if self.auto_write:
            self.show()

    def _getitem(self, index: int):
        offset = index * self._bpp
        r = self._buffer[offset + self._r_offset]
        g = self._buffer[offset + self._g_offset] 
        b = self._buffer[offset + self._b_offset]
        
        if self._w_offset is not None and self._bpp == 4:
            w = self._buffer[offset + self._w_offset]
            return [r, g, b, w]
        else:
            return [r, g, b]

    def __getitem__(self, index: Union[int, slice]):
        if isinstance(index, slice):
            out = []
            for in_i in range(*index.indices(self._pixels)):
                out.append(self._getitem(in_i))
            return out
        if index < 0:
            index += len(self)
        if index >= self._pixels or index < 0:
            raise IndexError
        return self._getitem(index)

    def _transmit(self, buffer: bytearray):
        raise NotImplementedError("Must be subclassed")

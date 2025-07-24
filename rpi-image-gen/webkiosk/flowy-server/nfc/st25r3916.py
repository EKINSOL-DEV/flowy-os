#!/usr/bin/env python3
"""
ST25R3916 NFC Reader Library
Python implementation for SPI communication with ST25R3916 NFC reader module
Based on STMicroelectronics ST25R3916 specifications and Arduino library
"""

import spidev
import time
import logging
from typing import List, Optional, Tuple, Union

# Use lgpio for Pi 5 compatibility
import lgpio
USE_LGPIO = True


class ST25R3916Error(Exception):
    """Custom exception for ST25R3916 operations"""
    pass


class ST25R3916:
    """
    ST25R3916 NFC Reader SPI Communication Class
    
    Provides read/write functionality for NFC tags using ST25R3916 chip over SPI.
    Supports ISO14443A/B, ISO15693, FeliCa, and NFC Forum protocols.
    """
    
    # Communication Mode Constants
    WRITE_MODE = 0x00  # 0U << 6
    READ_MODE = 0x40   # 1U << 6  
    CMD_MODE = 0xC0    # 3U << 6
    
    # FIFO Commands
    FIFO_LOAD = 0x80
    FIFO_READ = 0x9F
    
    # Register addresses (common ones from ST25R3916 spec)
    REG_IO_CONF1 = 0x00
    REG_IO_CONF2 = 0x01
    REG_OP_CONTROL = 0x02
    REG_MODE = 0x03
    REG_BITRATE = 0x04
    REG_ISO14443A_NFC = 0x05
    REG_ISO14443B_1 = 0x06
    REG_ISO14443B_2 = 0x07
    REG_PASSIVE_TARGET = 0x08
    REG_STREAM_MODE = 0x09
    REG_AUX = 0x0A
    REG_RX_CONF1 = 0x0B
    REG_RX_CONF2 = 0x0C
    REG_RX_CONF3 = 0x0D
    REG_RX_CONF4 = 0x0E
    REG_P2P_RX_CONF = 0x0F
    REG_CORR_CONF1 = 0x10
    REG_CORR_CONF2 = 0x11
    
    # Direct Commands
    CMD_SET_DEFAULT = 0xC1
    CMD_CLEAR_FIFO = 0xC2
    CMD_TRANSMIT_WITH_CRC = 0xC4
    CMD_TRANSMIT_WITHOUT_CRC = 0xC5
    CMD_TRANSMIT_REQA = 0xC6
    CMD_TRANSMIT_WUPA = 0xC7
    CMD_NFC_INITIAL_FIELD_ON = 0xC8
    CMD_NFC_RESPONSE_FIELD_ON = 0xC9
    CMD_GOTO_SLEEP = 0xCA
    CMD_GOTO_IDLE = 0xCB
    
    def __init__(self, spi_bus=0, spi_device=0, rst_pin=22, irq_pin=17, max_speed_hz=1000000):
        """
        Initialize ST25R3916 NFC reader
        
        Args:
            spi_bus: SPI bus number (default: 0)
            spi_device: SPI device number (default: 0) 
            rst_pin: GPIO pin for reset (default: 22)
            irq_pin: GPIO pin for interrupt (default: 17)
            max_speed_hz: SPI clock speed (default: 1MHz)
        """
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.rst_pin = rst_pin
        self.irq_pin = irq_pin
        self.max_speed_hz = max_speed_hz
        
        # Initialize SPI and GPIO
        self.spi = None
        self._initialized = False
        
        # GPIO handling - use lgpio for Pi 5
        self.gpio_chip = None
        self.gpio_handles = {}
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """Initialize SPI communication and GPIO pins"""
        try:
            # Initialize GPIO using lgpio for Pi 5
            self.gpio_chip = lgpio.gpiochip_open(0)  # Use GPIO chip 0 on Pi 5
            
            # Set up GPIO pins
            self.gpio_handles[self.rst_pin] = lgpio.gpio_claim_output(self.gpio_chip, self.rst_pin)
            self.gpio_handles[self.irq_pin] = lgpio.gpio_claim_input(self.gpio_chip, self.irq_pin)
            
            # Initialize SPI
            self.spi = spidev.SpiDev()
            self.spi.open(self.spi_bus, self.spi_device)
            self.spi.max_speed_hz = self.max_speed_hz
            self.spi.mode = 0  # SPI mode 0 (CPOL=0, CPHA=0)
            
            # Reset the chip
            self._reset()
            
            # Clear any pending interrupts and initialize properly (using direct SPI)
            self.spi.xfer2([self.CMD_CLEAR_FIFO])  # Clear FIFO and IRQ state
            self.spi.xfer2([self.CMD_SET_DEFAULT])  # Set chip to default state
            self.spi.xfer2([self.WRITE_MODE | 0x02, 0x00])  # Clear OP_CONTROL register
            
            # Wait for initialization
            time.sleep(0.01)
            
            self._initialized = True
            self.logger.info("ST25R3916 initialized successfully using lgpio")
            
        except Exception as e:
            self._cleanup_gpio()
            raise ST25R3916Error(f"Failed to initialize ST25R3916: {e}")
    
    def cleanup(self):
        """Clean up SPI and GPIO resources"""
        if self.spi:
            self.spi.close()
        
        self._cleanup_gpio()
        self._initialized = False
    
    def _cleanup_gpio(self):
        """Clean up GPIO resources"""
        # Free GPIO handles
        for pin, handle in self.gpio_handles.items():
            try:
                lgpio.gpio_free(self.gpio_chip, pin)
            except:
                pass
        self.gpio_handles.clear()
        
        # Close GPIO chip
        if self.gpio_chip is not None:
            try:
                lgpio.gpiochip_close(self.gpio_chip)
            except:
                pass
            self.gpio_chip = None
        
    def _reset(self):
        """Hardware reset of ST25R3916"""
        lgpio.gpio_write(self.gpio_chip, self.rst_pin, 0)
        time.sleep(0.001)  # 1ms reset pulse
        lgpio.gpio_write(self.gpio_chip, self.rst_pin, 1)
        time.sleep(0.005)  # 5ms recovery time
        
    def _check_initialized(self):
        """Check if the device is initialized"""
        if not self._initialized:
            raise ST25R3916Error("ST25R3916 not initialized. Call initialize() first.")
    
    def write_register(self, register: int, value: int):
        """
        Write a single byte to a register
        
        Args:
            register: Register address (0x00-0xFF)
            value: Byte value to write (0x00-0xFF)
        """
        self._check_initialized()
        
        # SPI command: WRITE_MODE | register_address
        cmd = self.WRITE_MODE | (register & 0x3F)
        
        try:
            self.spi.xfer2([cmd, value])
            self.logger.debug(f"Write register 0x{register:02X} = 0x{value:02X}")
        except Exception as e:
            raise ST25R3916Error(f"Failed to write register 0x{register:02X}: {e}")
    
    def read_register(self, register: int) -> int:
        """
        Read a single byte from a register
        
        Args:
            register: Register address (0x00-0xFF)
            
        Returns:
            Register value (0x00-0xFF)
        """
        self._check_initialized()
        
        # SPI command: READ_MODE | register_address
        cmd = self.READ_MODE | (register & 0x3F)
        
        try:
            response = self.spi.xfer2([cmd, 0x00])
            value = response[1]
            self.logger.debug(f"Read register 0x{register:02X} = 0x{value:02X}")
            return value
        except Exception as e:
            raise ST25R3916Error(f"Failed to read register 0x{register:02X}: {e}")
    
    def send_direct_command(self, command: int):
        """
        Send a direct command to ST25R3916
        
        Args:
            command: Direct command byte (0xC0-0xFF)
        """
        self._check_initialized()
        
        try:
            self.spi.xfer2([command])
            self.logger.debug(f"Send direct command 0x{command:02X}")
        except Exception as e:
            raise ST25R3916Error(f"Failed to send direct command 0x{command:02X}: {e}")
    
    def write_fifo(self, data: List[int]):
        """Write data to FIFO buffer"""
        self._check_initialized()
        
        try:
            self.spi.xfer2([self.FIFO_LOAD] + data)
            self.logger.debug(f"Write FIFO: {len(data)} bytes")
        except Exception as e:
            raise ST25R3916Error(f"Failed to write FIFO: {e}")
    
    def read_fifo(self, count: int) -> List[int]:
        """Read data from FIFO buffer"""
        self._check_initialized()
        
        try:
            response = self.spi.xfer2([self.FIFO_READ] + [0x00] * count)
            data = response[1:]  # Skip command echo
            self.logger.debug(f"Read FIFO: {count} bytes")
            return data
        except Exception as e:
            raise ST25R3916Error(f"Failed to read FIFO: {e}")
    
    def set_default_configuration(self):
        """Set ST25R3916 to default configuration"""
        self.send_direct_command(self.CMD_SET_DEFAULT)
        time.sleep(0.001)  # Wait for command completion
        
    def clear_fifo(self):
        """Clear FIFO buffer"""
        self.send_direct_command(self.CMD_CLEAR_FIFO)
        
    def field_on(self):
        """Turn on NFC field"""
        self.send_direct_command(self.CMD_NFC_INITIAL_FIELD_ON)
        time.sleep(0.005)  # Wait for field to stabilize
        
    def field_off(self):
        """Turn off NFC field and go to idle"""
        self.send_direct_command(self.CMD_GOTO_IDLE)
        
    def get_irq_status(self) -> bool:
        """Check interrupt pin status - ST25R3916 IRQ is active LOW"""
        return lgpio.gpio_read(self.gpio_chip, self.irq_pin) == 1
    
    def wait_for_irq(self, timeout: float = 1.0) -> bool:
        """Wait for interrupt signal with timeout - IRQ now works!"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if IRQ pin went HIGH (interrupt occurred)
            if lgpio.gpio_read(self.gpio_chip, self.irq_pin) == 1:
                return True
            time.sleep(0.001)  # 1ms polling
            
        return False
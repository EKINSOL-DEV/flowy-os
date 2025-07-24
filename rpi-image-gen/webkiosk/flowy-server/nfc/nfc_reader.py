#!/usr/bin/env python3
"""
NFC Reader High-Level Operations
Provides NFC tag detection, reading, and writing functionality using ST25R3916
"""

import time
import logging
from typing import List, Optional, Dict, Any
from st25r3916 import ST25R3916, ST25R3916Error


class NFCTag:
    """Represents an NFC tag with its properties"""
    
    def __init__(self, uid: List[int], tag_type: str, size: Optional[int] = None):
        self.uid = uid
        self.tag_type = tag_type
        self.size = size
        self.uid_str = ''.join(f'{b:02X}' for b in uid)
        
    def __str__(self):
        return f"NFC Tag - Type: {self.tag_type}, UID: {self.uid_str}, Size: {self.size}"


class NFCReader:
    """High-level NFC reader operations using ST25R3916"""
    
    # ISO14443A Commands
    CMD_REQA = 0x26
    CMD_WUPA = 0x52
    CMD_ANTICOLL = 0x93
    CMD_SELECT = 0x93
    CMD_HALT = 0x50
    
    # Tag Types
    TAG_TYPE_UNKNOWN = "Unknown"
    TAG_TYPE_MIFARE_CLASSIC = "MIFARE Classic"
    TAG_TYPE_MIFARE_ULTRALIGHT = "MIFARE Ultralight"
    TAG_TYPE_NTAG = "NTAG"
    TAG_TYPE_ISO15693 = "ISO15693"
    
    def __init__(self, st25r3916: ST25R3916):
        """
        Initialize NFC Reader
        
        Args:
            st25r3916: Initialized ST25R3916 instance
        """
        self.reader = st25r3916
        self.logger = logging.getLogger(__name__)
        self.current_tag: Optional[NFCTag] = None
        
    def initialize(self):
        """Initialize NFC reader for operation"""
        try:
            # Set default configuration
            self.reader.set_default_configuration()
            
            # Configure for ISO14443A Type A detection
            self._configure_iso14443a()
            
            self.logger.info("NFC Reader initialized for ISO14443A")
            
        except Exception as e:
            raise ST25R3916Error(f"Failed to initialize NFC reader: {e}")
    
    def _configure_iso14443a(self):
        """Configure ST25R3916 for ISO14443A operation"""
        # Set mode register for ISO14443A
        self.reader.write_register(self.reader.REG_MODE, 0x08)  # ISO14443A mode
        
        # Configure bit rate for 106 kbps
        self.reader.write_register(self.reader.REG_BITRATE, 0x00)  # 106 kbps
        
        # Set operation control
        self.reader.write_register(self.reader.REG_OP_CONTROL, 0x80)  # Enable receiver
        
        # Configure receiver
        self.reader.write_register(self.reader.REG_RX_CONF1, 0x13)
        self.reader.write_register(self.reader.REG_RX_CONF2, 0x2D)
        self.reader.write_register(self.reader.REG_RX_CONF3, 0x00)
        self.reader.write_register(self.reader.REG_RX_CONF4, 0x00)
    
    def detect_tag(self, timeout: float = 1.0) -> Optional[NFCTag]:
        """
        Detect and identify an NFC tag
        
        Args:
            timeout: Detection timeout in seconds
            
        Returns:
            NFCTag object if detected, None otherwise
        """
        try:
            self.logger.debug("Starting NFC tag detection")
            
            # Turn on RF field
            self.reader.field_on()
            time.sleep(0.01)  # Field stabilization time
            
            # Try ISO14443A detection
            tag = self._detect_iso14443a(timeout)
            
            if tag:
                self.current_tag = tag
                self.logger.info(f"NFC tag detected: {tag}")
                return tag
            
            # Could add other protocol detection here (ISO15693, etc.)
            
            self.logger.debug("No NFC tag detected")
            return None
            
        except Exception as e:
            self.logger.error(f"Tag detection failed: {e}")
            return None
        finally:
            # Keep field on if tag detected, otherwise turn off
            if not self.current_tag:
                self.reader.field_off()
    
    def _detect_iso14443a(self, timeout: float) -> Optional[NFCTag]:
        """Detect ISO14443A compliant tags"""
        try:
            # Clear FIFO and send REQA command
            self.reader.clear_fifo()
            
            # Prepare REQA command
            self.reader.write_fifo([self.CMD_REQA])
            
            # Transmit REQA
            self.reader.send_direct_command(self.reader.CMD_TRANSMIT_WITHOUT_CRC)
            
            # Wait for response
            if not self.reader.wait_for_irq(timeout):
                self.logger.debug("No response to REQA")
                return None
            
            # Read ATQA (Answer to Request Type A)
            atqa = self.reader.read_fifo(2)
            if len(atqa) < 2:
                self.logger.debug("Invalid ATQA response")
                return None
                
            self.logger.debug(f"ATQA: {atqa[0]:02X} {atqa[1]:02X}")
            
            # Perform anticollision to get UID
            uid = self._anticollision()
            if not uid:
                return None
                
            # Determine tag type based on ATQA
            tag_type = self._determine_tag_type(atqa, uid)
            
            return NFCTag(uid, tag_type)
            
        except Exception as e:
            self.logger.error(f"ISO14443A detection failed: {e}")
            return None
    
    def _anticollision(self) -> Optional[List[int]]:
        """Perform anticollision to retrieve UID"""
        try:
            # Clear FIFO
            self.reader.clear_fifo()
            
            # Send anticollision command
            anticoll_cmd = [self.CMD_ANTICOLL, 0x20]  # SEL=0x93, NVB=0x20
            self.reader.write_fifo(anticoll_cmd)
            
            # Transmit command
            self.reader.send_direct_command(self.reader.CMD_TRANSMIT_WITHOUT_CRC)
            
            # Wait for response
            if not self.reader.wait_for_irq(1.0):
                self.logger.debug("No response to anticollision")
                return None
            
            # Read UID + BCC (5 bytes total)
            uid_response = self.reader.read_fifo(5)
            if len(uid_response) < 5:
                self.logger.debug("Incomplete UID response")
                return None
            
            # Extract UID (first 4 bytes, last byte is BCC)
            uid = uid_response[:4]
            bcc = uid_response[4]
            
            # Verify BCC (XOR of UID bytes should equal BCC)
            calculated_bcc = uid[0] ^ uid[1] ^ uid[2] ^ uid[3]
            if calculated_bcc != bcc:
                self.logger.warning(f"BCC mismatch: calculated={calculated_bcc:02X}, received={bcc:02X}")
            
            self.logger.debug(f"UID: {' '.join(f'{b:02X}' for b in uid)}")
            return uid
            
        except Exception as e:
            self.logger.error(f"Anticollision failed: {e}")
            return None
    
    def _determine_tag_type(self, atqa: List[int], uid: List[int]) -> str:
        """Determine NFC tag type from ATQA and UID"""
        # Simple tag type detection based on ATQA
        atqa_word = (atqa[1] << 8) | atqa[0]
        
        if atqa_word == 0x0004:
            return self.TAG_TYPE_MIFARE_CLASSIC
        elif atqa_word == 0x0044:
            return self.TAG_TYPE_MIFARE_ULTRALIGHT
        elif atqa_word == 0x0004 and uid[0] == 0x04:
            return self.TAG_TYPE_NTAG
        else:
            return self.TAG_TYPE_UNKNOWN
    
    def read_block(self, block_number: int) -> Optional[List[int]]:
        """
        Read a block from the current NFC tag
        
        Args:
            block_number: Block number to read (0-based)
            
        Returns:
            Block data as list of bytes, or None if failed
        """
        if not self.current_tag:
            self.logger.error("No tag selected")
            return None
        
        try:
            if self.current_tag.tag_type in [self.TAG_TYPE_MIFARE_ULTRALIGHT, self.TAG_TYPE_NTAG]:
                return self._read_ultralight_block(block_number)
            elif self.current_tag.tag_type == self.TAG_TYPE_MIFARE_CLASSIC:
                self.logger.error("MIFARE Classic read not implemented yet")
                return None
            else:
                self.logger.error(f"Unsupported tag type: {self.current_tag.tag_type}")
                return None
            
        except Exception as e:
            self.logger.error(f"Failed to read block {block_number}: {e}")
            return None
    
    def write_block(self, block_number: int, data: List[int]) -> bool:
        """
        Write a block to the current NFC tag
        
        Args:
            block_number: Block number to write (0-based)
            data: Data to write (4 bytes for Ultralight, 16 bytes for Classic)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.current_tag:
            self.logger.error("No tag selected")
            return False
        
        try:
            if self.current_tag.tag_type in [self.TAG_TYPE_MIFARE_ULTRALIGHT, self.TAG_TYPE_NTAG]:
                return self._write_ultralight_block(block_number, data)
            elif self.current_tag.tag_type == self.TAG_TYPE_MIFARE_CLASSIC:
                self.logger.error("MIFARE Classic write not implemented yet")
                return False
            else:
                self.logger.error(f"Unsupported tag type: {self.current_tag.tag_type}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to write block {block_number}: {e}")
            return False
    
    def halt_tag(self):
        """Send HALT command to current tag"""
        if self.current_tag:
            try:
                self.reader.clear_fifo()
                halt_cmd = [self.CMD_HALT, 0x00]
                self.reader.write_fifo(halt_cmd)
                self.reader.send_direct_command(self.reader.CMD_TRANSMIT_WITH_CRC)
                
                self.current_tag = None
                self.logger.debug("Tag halted")
                
            except Exception as e:
                self.logger.error(f"Failed to halt tag: {e}")
    
    def stop_reading(self):
        """Stop reading and turn off RF field"""
        self.halt_tag()
        self.reader.field_off()
        self.current_tag = None
        self.logger.debug("NFC reading stopped")
    
    def get_tag_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current tag
        
        Returns:
            Dictionary with tag information, or None if no tag
        """
        if not self.current_tag:
            return None
        
        return {
            "uid": self.current_tag.uid_str,
            "type": self.current_tag.tag_type,
            "size": self.current_tag.size,
            "present": True
        }
    
    def _read_ultralight_block(self, block_number: int) -> Optional[List[int]]:
        """
        Read block from MIFARE Ultralight/NTAG tag
        
        NTAG213/Ultralight uses READ command that reads 4 blocks (16 bytes) at once
        """
        try:
            # Clear FIFO
            self.reader.clear_fifo()
            
            # READ command: [0x30, block_address]
            read_cmd = [0x30, block_number]
            self.reader.write_fifo(read_cmd)
            
            # Transmit command with CRC
            self.reader.send_direct_command(self.reader.CMD_TRANSMIT_WITH_CRC)
            
            # Wait for response
            if not self.reader.wait_for_irq(1.0):
                self.logger.debug(f"No response to READ block {block_number}")
                return None
            
            # Read response (16 bytes = 4 blocks)
            response = self.reader.read_fifo(16)
            if len(response) < 16:
                self.logger.debug("Incomplete READ response")
                return None
            
            # Return only the requested block (4 bytes)
            block_offset = 0  # We asked for specific block, so it's at start
            block_data = response[block_offset:block_offset + 4]
            
            self.logger.debug(f"Read block {block_number}: {' '.join(f'{b:02X}' for b in block_data)}")
            return block_data
            
        except Exception as e:
            self.logger.error(f"Failed to read Ultralight block {block_number}: {e}")
            return None
    
    def _write_ultralight_block(self, block_number: int, data: List[int]) -> bool:
        """
        Write block to MIFARE Ultralight/NTAG tag
        
        NTAG213/Ultralight uses WRITE command that writes 4 bytes at once
        """
        try:
            # Ensure data is exactly 4 bytes
            if len(data) > 4:
                data = data[:4]
            elif len(data) < 4:
                data = data + [0x00] * (4 - len(data))
            
            # Clear FIFO
            self.reader.clear_fifo()
            
            # WRITE command: [0xA2, block_address, data[0], data[1], data[2], data[3]]
            write_cmd = [0xA2, block_number] + data
            self.reader.write_fifo(write_cmd)
            
            # Transmit command with CRC
            self.reader.send_direct_command(self.reader.CMD_TRANSMIT_WITH_CRC)
            
            # Wait for ACK response
            if not self.reader.wait_for_irq(1.0):
                self.logger.debug(f"No response to WRITE block {block_number}")
                return False
            
            # Read ACK (should be 0x0A for success)
            response = self.reader.read_fifo(1)
            if len(response) < 1:
                self.logger.debug("No ACK received")
                return False
            
            if response[0] == 0x0A:
                self.logger.debug(f"Write block {block_number} successful")
                return True
            else:
                self.logger.debug(f"Write block {block_number} failed, ACK: {response[0]:02X}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to write Ultralight block {block_number}: {e}")
            return False
#!/usr/bin/env python3
"""
Pi Pico NFC Bridge Module
USB/Serial communication with Pico2W NFC Bridge

This module provides an interface compatible with the nfc_reader module
but communicates with the Pi Pico NFC bridge over USB/serial instead
of using I2C/SPI drivers.
"""

import serial
import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PicoNFCTag:
    """Represents an NFC tag detected by the Pico bridge"""
    tag_number: int
    protocol: str
    technology: str
    tag_id: str
    message: str

class NFCError(Exception):
    """Base exception for NFC operations"""
    pass

class NFCInitializationError(NFCError):
    """Exception raised during NFC initialization"""
    pass

class PicoNFCReader:
    """
    Pi Pico NFC Bridge Reader - compatible interface with nfc_reader module
    """
    
    def __init__(self, device_path: Optional[str] = None, baudrate: int = 115200, auto_cleanup: bool = True):
        self.serial_port: Optional[serial.Serial] = None
        self.device_path = device_path
        self.baudrate = baudrate
        self.auto_cleanup = auto_cleanup
        
        # State tracking
        self._initialized = False
        self.discovery_active = False
        self._current_tags: List[PicoNFCTag] = []
        
        # Common Pi Pico USB serial device paths
        self.common_paths = [
            "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2", 
            "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2"
        ]
    
    def initialize(self) -> None:
        """
        Initialize the Pi Pico NFC bridge connection
        
        Raises:
            NFCInitializationError: If initialization fails
        """
        if self._initialized:
            return
        
        paths_to_try = [self.device_path] if self.device_path else self.common_paths
        
        for path in paths_to_try:
            if path is None:
                continue
                
            try:
                logger.info(f"Trying to connect to Pico NFC bridge on {path}")
                self.serial_port = serial.Serial(
                    port=path,
                    baudrate=self.baudrate,
                    timeout=5.0,
                    write_timeout=5.0
                )
                logger.info(f"Serial port opened successfully on {path}")
                
                # Give the Pi Pico time to initialize and send startup messages
                time.sleep(3.0)
                logger.info(f"Waited 3 seconds for Arduino initialization")
                
                # Clear any startup messages from the buffer
                if self.serial_port.in_waiting > 0:
                    startup_data = self.serial_port.read_all().decode('utf-8', errors='ignore')
                    logger.info(f"Cleared {len(startup_data)} bytes of startup data")
                    logger.debug(f"Arduino startup messages: {startup_data}")
                else:
                    logger.info("No startup messages to clear")
                
                # Test connection with ping
                logger.info("Testing connection with PING command")
                ping_result = self._ping()
                logger.info(f"PING test result: {ping_result}")
                
                if ping_result:
                    logger.info(f"Successfully connected to Pi Pico NFC bridge on {path}")
                    self.device_path = path
                    self._initialized = True
                    return
                else:
                    logger.warning(f"PING test failed on {path}")
                    
            except (serial.SerialException, OSError) as e:
                logger.warning(f"Failed to connect to {path}: {e}")
                if self.serial_port:
                    self.serial_port.close()
                    self.serial_port = None
        
        raise NFCInitializationError("Failed to connect to Pi Pico NFC bridge")
    
    def cleanup(self) -> None:
        """Clean up the NFC connection"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        self._initialized = False
        self.discovery_active = False
        self._current_tags.clear()
        logger.info("Pi Pico NFC bridge cleaned up")
    
    def _send_command(self, command: str, timeout: float = 10.0) -> Optional[str]:
        """
        Send a command to the Pi Pico and wait for response
        
        Args:
            command: Command string to send
            timeout: Response timeout in seconds
            
        Returns:
            Response string or None if timeout/error
        """
        if not self.serial_port:
            logger.warning("Serial port not available for command")
            return None
        
        # Allow commands during initialization (when _initialized is False)
        logger.debug(f"Sending command: {command}")
        
        try:
            # Clear any existing data in buffers
            self.serial_port.flushInput()
            self.serial_port.flushOutput()
            
            # Send command
            cmd_bytes = (command + '\n').encode('utf-8')
            self.serial_port.write(cmd_bytes)
            logger.debug(f"Sent command: {command}")
            
            # Read response line by line until we get a complete response
            start_time = time.time()
            response_lines = []
            
            while (time.time() - start_time) < timeout:
                if self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        logger.debug(f"Received: {line}")
                        response_lines.append(line)
                        
                        # Check for command completion markers
                        if line == "POLLEND":
                            # POLL command completed
                            break
                        elif line.startswith("ERROR:"):
                            # Any error response completes the command
                            break
                        elif line.startswith("OK:") and not command.startswith("POLL") and not line.startswith("OK:ENTER:") and not line.startswith("OK:LEAVE:"):
                            # Non-POLL OK response (like OK:PONG, OK:WRITE_SUCCESS)
                            break
                        elif command.startswith("WRITE:") and (line.startswith("ERROR:") or line == "OK:WRITE_SUCCESS"):
                            # WRITE command specific responses
                            break
                
                time.sleep(0.01)  # Small delay to prevent busy waiting
            
            if response_lines:
                return '\n'.join(response_lines)
            else:
                logger.warning(f"Timeout waiting for response to: {command}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            return None
    
    def _ping(self) -> bool:
        """Test connection to Pi Pico"""
        logger.debug("Starting PING test")
        response = self._send_command("PING", timeout=3.0)
        logger.debug(f"PING response received: {repr(response)}")
        
        if response:
            # Check if the response contains "OK:PONG" (may have other lines)
            has_pong = "OK:PONG" in response
            logger.debug(f"Contains 'OK:PONG': {has_pong}")
            return has_pong
        
        logger.debug("No response to PING")
        return False
    
    def _parse_poll_response(self, response: str) -> List[PicoNFCTag]:
        """Parse the response from a POLL command"""
        tags = []
        lines = response.split('\n')
        
        for line in lines:
            if line.startswith("OK:ENTER:"):
                # Format: OK:ENTER:PROTOCOL:TECH:ID:"MESSAGE"
                try:
                    parts = line[9:].split(':', 4)  # Skip "OK:ENTER:" prefix
                    if len(parts) >= 4:
                        protocol = parts[0]
                        technology = parts[1]
                        tag_id = parts[2]
                        
                        # Extract message from quotes
                        message = ""
                        if len(parts) > 3:
                            msg_part = parts[3]
                            if msg_part.startswith('"') and msg_part.endswith('"'):
                                message = msg_part[1:-1]  # Remove quotes
                            else:
                                message = msg_part
                        
                        tag = PicoNFCTag(
                            tag_number=1,  # Single tag detection, always use 1
                            protocol=protocol,
                            technology=technology,
                            tag_id=tag_id,
                            message=message
                        )
                        tags.append(tag)
                        
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse tag line: {line} - {e}")
        
        return tags
    
    def start_discovery(self) -> None:
        """Start NFC tag discovery"""
        if not self._initialized:
            raise NFCError("NFC reader not initialized")
        
        self.discovery_active = True
        logger.debug("NFC discovery started (Pico bridge)")
    
    def stop_discovery(self) -> None:
        """Stop NFC tag discovery"""
        self.discovery_active = False
        self._current_tags.clear()
        logger.debug("NFC discovery stopped (Pico bridge)")
    
    def is_tag_present(self) -> bool:
        """Check if any NFC tag is currently present"""
        return len(self._current_tags) > 0
    
    def get_num_tags(self) -> int:
        """Get number of currently detected tags"""
        return len(self._current_tags)
    
    def wait_for_tag(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """
        Wait for an NFC tag with text content
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Dict with tag data or None if timeout
        """
        if not self._initialized:
            raise NFCError("NFC reader not initialized")
        
        # Use timed polling instead of infinite polling
        command = f"POLL:{int(timeout)}"  # POLL:10 format
        response = self._send_command(command, timeout=timeout + 5.0)
        if not response:
            return None
        
        tags = self._parse_poll_response(response)
        self._current_tags = tags
        
        if tags:
            tag = tags[0]  # Return first tag
            return {
                'text': tag.message if tag.message else None,
                'language': 'en',  # Default language
                'uid': tag.tag_id,
                'technology_name': tag.technology
            }
        
        return None
    
    def wait_for_multiple_tags(self, min_tags: int = 2, timeout: float = 30.0) -> Optional[List[Dict[str, Any]]]:
        """
        Wait for multiple NFC tags
        
        Args:
            min_tags: Minimum number of tags to wait for
            timeout: Timeout in seconds
            
        Returns:
            List of tag data dicts or None if timeout
        """
        if not self._initialized:
            raise NFCError("NFC reader not initialized")
        
        # Poll for multiple tags
        command = f"POLL:{min_tags}"
        response = self._send_command(command, timeout=timeout + 5.0)
        if not response:
            return None
        
        tags = self._parse_poll_response(response)
        self._current_tags = tags
        
        if len(tags) >= min_tags:
            results = []
            for tag in tags:
                tag_data = {
                    'text': tag.message if tag.message else None,
                    'language': 'en',  # Default language
                    'uid': tag.tag_id,
                    'technology_name': tag.technology
                }
                results.append(tag_data)
            return results
        
        return None
    
    def write_text(self, text: str, language_code: str = "en") -> bool:
        """
        Write text to an NFC tag
        
        Args:
            text: Text to write
            language_code: Language code (ignored for Pico bridge)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            raise NFCError("NFC reader not initialized")
        
        if not text:
            return False
        
        # First, make sure no polling is active by sending ENDPOLL
        logger.info("Ensuring no active polling before write")
        self._send_command("ENDPOLL", timeout=2.0)
        
        # Small delay to let Arduino process the ENDPOLL
        time.sleep(0.5)
        
        command = f"WRITE:{text}"
        logger.info(f"Sending write command: {command}")
        response = self._send_command(command, timeout=15.0)
        logger.info(f"Write response: {repr(response)}")
        
        success = response and "OK:WRITE_SUCCESS" in response
        logger.info(f"Write result: {success}")
        return success
    
    def get_tag_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the first detected tag"""
        if not self._current_tags:
            return None
        
        tag = self._current_tags[0]
        return {
            'uid': tag.tag_id,
            'technology_name': tag.technology,
            'protocol': tag.protocol,
            'message': tag.message
        }
    
    def get_all_tags_info(self) -> List[Dict[str, Any]]:
        """Get information about all detected tags"""
        results = []
        for tag in self._current_tags:
            tag_info = {
                'uid': tag.tag_id,
                'technology_name': tag.technology,
                'protocol': tag.protocol,
                'message': tag.message
            }
            results.append(tag_info)
        return results

    def __del__(self):
        """Destructor - cleanup if auto_cleanup is enabled"""
        if self.auto_cleanup:
            self.cleanup()

# Alias for compatibility with existing code
NFCReader = PicoNFCReader
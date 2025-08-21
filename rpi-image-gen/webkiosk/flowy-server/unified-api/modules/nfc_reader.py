#!/usr/bin/env python3
"""
High-level Python interface for reading NFC tags.

This module provides a simple, clean interface for interacting with NFC tags
and extracting text content from NDEF records.

Example usage:
    import nfc_reader
    
    # Simple text reading
    text = nfc_reader.read_text_from_tag(timeout=10)
    if text:
        print(f"Found text: {text}")
    
    # Advanced usage with context manager
    with nfc_reader.NFCReader() as reader:
        result = reader.wait_for_tag(timeout=30)
        if result:
            print(f"Text: {result['text']}")
            print(f"Language: {result['language']}")

Requirements:
    - Root privileges (for NFC hardware access)
    - Built nfc_native extension module
    - NFC hardware connected and configured
"""

import time
import threading
from typing import Optional, Dict, Any, Union, List
import logging

try:
    import nfc_native
except ImportError as e:
    raise ImportError(
        "nfc_native module not found. Please build the extension first:\n"
        "cd python && python setup.py build_ext --inplace"
    ) from e

# Configure logging
logger = logging.getLogger(__name__)

class NFCError(Exception):
    """Base exception for NFC-related errors."""
    pass

class NFCInitializationError(NFCError):
    """Raised when NFC initialization fails."""
    pass

class NFCReader:
    """
    High-level NFC reader class for reading text from NFC tags.
    
    This class provides a convenient interface for NFC operations,
    handling initialization, discovery, and cleanup automatically.
    
    Attributes:
        auto_cleanup (bool): Whether to automatically cleanup on context exit
        discovery_active (bool): Whether tag discovery is currently active
    """
    
    def __init__(self, auto_cleanup: bool = True):
        """
        Initialize the NFC reader.
        
        Args:
            auto_cleanup: Whether to automatically cleanup resources
        
        Raises:
            NFCInitializationError: If NFC initialization fails
        """
        self.auto_cleanup = auto_cleanup
        self.discovery_active = False
        self._initialized = False
        
    def __enter__(self):
        """Context manager entry. Initializes NFC."""
        self.initialize()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit. Cleans up if auto_cleanup is enabled."""
        if self.auto_cleanup:
            self.cleanup()
    
    def initialize(self) -> bool:
        """
        Initialize the NFC stack.
        
        Returns:
            bool: True if initialization succeeded, False otherwise
            
        Raises:
            NFCInitializationError: If initialization fails
        """
        try:
            success = nfc_native.initialize()
            if not success:
                raise NFCInitializationError("Failed to initialize NFC stack")
            self._initialized = True
            logger.info("NFC stack initialized successfully")
            return True
        except Exception as e:
            raise NFCInitializationError(f"NFC initialization failed: {e}") from e
    
    def cleanup(self) -> None:
        """Clean up NFC resources."""
        try:
            if self.discovery_active:
                self.stop_discovery()
            if self._initialized:
                nfc_native.deinitialize()
                self._initialized = False
                logger.info("NFC stack cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def start_discovery(self) -> None:
        """
        Start NFC tag discovery.
        
        Raises:
            NFCError: If discovery fails to start
        """
        if not self._initialized:
            raise NFCError("NFC not initialized")
        
        try:
            nfc_native.start_discovery()
            self.discovery_active = True
            logger.debug("NFC discovery started")
        except Exception as e:
            raise NFCError(f"Failed to start discovery: {e}") from e
    
    def stop_discovery(self) -> None:
        """Stop NFC tag discovery."""
        try:
            if self.discovery_active:
                nfc_native.stop_discovery()
                self.discovery_active = False
                logger.debug("NFC discovery stopped")
        except Exception as e:
            logger.error(f"Error stopping discovery: {e}")
    
    def is_tag_present(self) -> bool:
        """
        Check if an NFC tag is currently present.
        
        Returns:
            bool: True if a tag is detected, False otherwise
        """
        if not self._initialized:
            return False
        
        try:
            return nfc_native.is_tag_present()
        except Exception as e:
            logger.error(f"Error checking tag presence: {e}")
            return False
    
    def read_text(self) -> Optional[Dict[str, str]]:
        """
        Read text from the currently detected NFC tag.
        
        Returns:
            dict: Dictionary with 'text', 'language', and 'type' keys if successful,
                  None if no text found or no tag present
        """
        if not self._initialized:
            logger.error("NFC not initialized")
            return None
        
        try:
            return nfc_native.read_text()
        except Exception as e:
            logger.error(f"Error reading text: {e}")
            return None
    
    def get_tag_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the currently detected tag.
        
        Returns:
            dict: Tag information including technology, UID, etc., or None if no tag
        """
        if not self._initialized:
            return None
        
        try:
            return nfc_native.get_tag_info()
        except Exception as e:
            logger.error(f"Error getting tag info: {e}")
            return None
    
    def get_num_tags(self) -> int:
        """
        Get the number of currently detected tags.
        
        Returns:
            int: Number of detected tags, 0 if none detected
        """
        if not self._initialized:
            return 0
        
        try:
            return nfc_native.get_num_tags()
        except Exception as e:
            logger.error(f"Error getting number of tags: {e}")
            return 0
    
    def select_next_tag(self) -> bool:
        """
        Select the next tag in the field (for multi-tag scenarios).
        
        Returns:
            bool: True if successfully selected next tag, False otherwise
        """
        if not self._initialized:
            logger.error("NFC not initialized")
            return False
        
        try:
            return nfc_native.select_next_tag()
        except Exception as e:
            logger.error(f"Error selecting next tag: {e}")
            return False
    
    def check_next_protocol(self) -> int:
        """
        Check the next valid protocol index.
        
        Returns:
            int: Index of next tag protocol, -1 if no valid index
        """
        if not self._initialized:
            return -1
        
        try:
            return nfc_native.check_next_protocol()
        except Exception as e:
            logger.error(f"Error checking next protocol: {e}")
            return -1
    
    def read_all_text(self) -> Optional[List[Dict[str, Any]]]:
        """
        Read text from all detected tags.
        
        Returns:
            list: List of dictionaries with text data from each tag, or None if no tags
        """
        if not self._initialized:
            logger.error("NFC not initialized")
            return None
        
        try:
            result = nfc_native.read_all_text()
            if result is None:
                return None
            
            # Filter out tags without text
            text_tags = []
            for tag in result:
                if tag.get('text'):
                    text_tags.append(tag)
            
            return text_tags if text_tags else None
        except Exception as e:
            logger.error(f"Error reading all text: {e}")
            return None
    
    def get_all_tags_info(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get information for all detected tags.
        
        Returns:
            list: List of tag information dictionaries, or None if no tags
        """
        if not self._initialized:
            return None
        
        try:
            return nfc_native.get_all_tags_info()
        except Exception as e:
            logger.error(f"Error getting all tags info: {e}")
            return None
    
    def create_text_ndef(self, text: str, language_code: str = "en") -> Optional[bytes]:
        """
        Create an NDEF text record.
        
        Args:
            text: The text content to encode
            language_code: Language code (default: "en")
            
        Returns:
            bytes: NDEF record data, or None if creation failed
        """
        try:
            return nfc_native.create_text_ndef(language_code, text)
        except Exception as e:
            logger.error(f"Error creating NDEF text record: {e}")
            return None
    
    def write_ndef(self, ndef_data: bytes) -> bool:
        """
        Write NDEF data to the currently detected tag.
        
        Args:
            ndef_data: NDEF record data to write
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("NFC not initialized")
            return False
        
        try:
            return nfc_native.write_ndef(ndef_data)
        except Exception as e:
            logger.error(f"Error writing NDEF data: {e}")
            return False
    
    def write_text(self, text: str, language_code: str = "en") -> bool:
        """
        Write text to the currently detected tag.
        
        Args:
            text: Text content to write
            language_code: Language code (default: "en")
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._initialized:
            logger.error("NFC not initialized")
            return False
        
        try:
            return nfc_native.write_text(text, language_code)
        except Exception as e:
            logger.error(f"Error writing text: {e}")
            return False
    
    def wait_for_multiple_tags(self, min_tags: int = 2, timeout: float = 30.0, 
                             check_interval: float = 0.1) -> Optional[List[Dict[str, Any]]]:
        """
        Wait for multiple NFC tags and read data from all of them.
        
        Args:
            min_tags: Minimum number of tags to wait for
            timeout: Maximum time to wait for tags (seconds)
            check_interval: How often to check for tags (seconds)
            
        Returns:
            list: List of tag data if found, None if timeout or insufficient tags
        """
        if not self._initialized:
            self.initialize()
        
        if not self.discovery_active:
            self.start_discovery()
        
        start_time = time.time()
        
        logger.info(f"Waiting for {min_tags} NFC tags (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            num_tags = self.get_num_tags()
            
            if num_tags >= min_tags:
                logger.info(f"Found {num_tags} tags, reading data...")
                
                # Get all tag data
                all_tags = self.read_all_text()
                if all_tags and len(all_tags) >= min_tags:
                    logger.info(f"Successfully read data from {len(all_tags)} tags")
                    return all_tags
                else:
                    logger.debug(f"Found {num_tags} tags but only {len(all_tags) if all_tags else 0} with text")
            
            time.sleep(check_interval)
        
        logger.info("Timeout waiting for multiple tags")
        return None
    
    def wait_for_tag(self, timeout: float = 30.0, check_interval: float = 0.1) -> Optional[Dict[str, str]]:
        """
        Wait for an NFC tag and read text from it.
        
        Args:
            timeout: Maximum time to wait for a tag (seconds)
            check_interval: How often to check for tags (seconds)
            
        Returns:
            dict: Text data if found, None if timeout or no text
        """
        if not self._initialized:
            self.initialize()
        
        if not self.discovery_active:
            self.start_discovery()
        
        start_time = time.time()
        
        logger.info(f"Waiting for NFC tag (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            if self.is_tag_present():
                logger.info("Tag detected, reading text...")
                text_data = self.read_text()
                if text_data:
                    logger.info(f"Text found: {text_data['text']}")
                    return text_data
                else:
                    logger.debug("Tag present but no text found")
            
            time.sleep(check_interval)
        
        logger.info("Timeout waiting for tag")
        return None


# Convenience functions for simple usage

def read_text_from_tag(timeout: float = 30.0, check_interval: float = 0.1) -> Optional[str]:
    """
    Simple function to read text from an NFC tag.
    
    This is a convenience function that handles all the setup and cleanup
    automatically. Just call it and wait for a tag.
    
    Args:
        timeout: Maximum time to wait for a tag (seconds)
        check_interval: How often to check for tags (seconds)
        
    Returns:
        str: The text content if found, None otherwise
        
    Example:
        text = nfc_reader.read_text_from_tag(timeout=10)
        if text:
            print(f"Found: {text}")
    """
    with NFCReader() as reader:
        result = reader.wait_for_tag(timeout=timeout, check_interval=check_interval)
        return result['text'] if result else None


def read_text_with_language(timeout: float = 30.0, check_interval: float = 0.1) -> Optional[Dict[str, str]]:
    """
    Read text and language information from an NFC tag.
    
    Args:
        timeout: Maximum time to wait for a tag (seconds)
        check_interval: How often to check for tags (seconds)
        
    Returns:
        dict: Dictionary with 'text' and 'language' keys, or None
        
    Example:
        result = nfc_reader.read_text_with_language(timeout=10)
        if result:
            print(f"Text: {result['text']} (Language: {result['language']})")
    """
    with NFCReader() as reader:
        return reader.wait_for_tag(timeout=timeout, check_interval=check_interval)


def get_tag_data(timeout: float = 30.0, check_interval: float = 0.1) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive information about an NFC tag including text content.
    
    Args:
        timeout: Maximum time to wait for a tag (seconds)
        check_interval: How often to check for tags (seconds)
        
    Returns:
        dict: Combined tag info and text data, or None
        
    Example:
        data = nfc_reader.get_tag_data(timeout=10)
        if data:
            print(f"UID: {data['uid']}")
            print(f"Technology: {data['technology_name']}")
            print(f"Text: {data.get('text', 'No text found')}")
    """
    with NFCReader() as reader:
        result = reader.wait_for_tag(timeout=timeout, check_interval=check_interval)
        if result:
            tag_info = reader.get_tag_info()
            if tag_info:
                # Combine text data with tag info
                combined_data = {**tag_info, **result}
                return combined_data
        return None


# Multi-tag convenience functions

def read_multiple_tags(min_tags: int = 2, timeout: float = 30.0, check_interval: float = 0.1) -> Optional[List[Dict[str, Any]]]:
    """
    Read text from multiple NFC tags simultaneously.
    
    Args:
        min_tags: Minimum number of tags to wait for
        timeout: Maximum time to wait for tags (seconds)
        check_interval: How often to check for tags (seconds)
        
    Returns:
        list: List of tag data dictionaries, or None if insufficient tags found
        
    Example:
        tags = nfc_reader.read_multiple_tags(min_tags=2, timeout=30)
        if tags:
            for i, tag in enumerate(tags):
                print(f"Tag {i+1}: {tag['text']} (UID: {tag['uid']})")
    """
    with NFCReader() as reader:
        return reader.wait_for_multiple_tags(min_tags=min_tags, timeout=timeout, check_interval=check_interval)


def get_all_tag_info(timeout: float = 10.0, check_interval: float = 0.1) -> Optional[List[Dict[str, Any]]]:
    """
    Get information for all currently detected NFC tags.
    
    Args:
        timeout: Maximum time to wait for tags (seconds)
        check_interval: How often to check for tags (seconds)
        
    Returns:
        list: List of tag information dictionaries, or None if no tags
        
    Example:
        tags = nfc_reader.get_all_tag_info(timeout=10)
        if tags:
            print(f"Found {len(tags)} tags:")
            for tag in tags:
                print(f"  UID: {tag['uid']}, Tech: {tag['technology_name']}")
    """
    with NFCReader() as reader:
        reader.start_discovery()
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if reader.get_num_tags() > 0:
                return reader.get_all_tags_info()
            time.sleep(check_interval)
        
        return None


def monitor_multiple_tags(callback=None, min_tags: int = 1, check_interval: float = 0.5):
    """
    Continuously monitor for multiple NFC tags and call callback when tags change.
    
    Args:
        callback: Function to call with tag data when tags change
        min_tags: Minimum number of tags to trigger callback
        check_interval: How often to check for tag changes (seconds)
        
    Example:
        def on_tags_changed(tags):
            print(f"Tags changed: {len(tags)} tags detected")
            for tag in tags:
                print(f"  {tag.get('text', 'No text')}")
        
        nfc_reader.monitor_multiple_tags(callback=on_tags_changed, min_tags=1)
    """
    with NFCReader() as reader:
        last_tag_count = 0
        last_tags = []
        
        while True:
            try:
                current_count = reader.get_num_tags()
                
                if current_count != last_tag_count and current_count >= min_tags:
                    current_tags = reader.read_all_text() or []
                    
                    # Check if tag content has changed
                    if current_tags != last_tags:
                        if callback:
                            callback(current_tags)
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] Found {len(current_tags)} tags with text")
                            for i, tag in enumerate(current_tags):
                                text = tag.get('text', 'No text')
                                uid = tag.get('uid', 'Unknown')[:8] + "..."
                                print(f"  Tag {i+1}: '{text}' (UID: {uid})")
                        
                        last_tags = current_tags
                
                last_tag_count = current_count
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped")
                break
            except Exception as e:
                print(f"Error during monitoring: {e}")
                time.sleep(1)


# Convenience functions for writing

def write_text_to_tag(text: str, language_code: str = "en", timeout: float = 30.0) -> bool:
    """
    Simple function to write text to an NFC tag.
    
    Args:
        text: Text content to write
        language_code: Language code (default: "en")
        timeout: Maximum time to wait for a tag (seconds)
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        success = nfc_reader.write_text_to_tag("Hello, World!", "en", timeout=30)
        if success:
            print("Text written successfully!")
    """
    with NFCReader() as reader:
        reader.start_discovery()
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if reader.is_tag_present():
                logger.info("Tag detected, writing text...")
                success = reader.write_text(text, language_code)
                if success:
                    logger.info(f"Successfully wrote text: '{text}'")
                    return True
                else:
                    logger.error("Failed to write text to tag")
                    return False
            time.sleep(0.1)
        
        logger.info("Timeout waiting for tag")
        return False


def create_ndef_text_record(text: str, language_code: str = "en") -> Optional[bytes]:
    """
    Create an NDEF text record without writing it to a tag.
    
    Args:
        text: Text content to encode
        language_code: Language code (default: "en")
        
    Returns:
        bytes: NDEF record data, or None if creation failed
        
    Example:
        ndef_data = nfc_reader.create_ndef_text_record("Hello, World!", "en")
        if ndef_data:
            print(f"Created NDEF record ({len(ndef_data)} bytes)")
    """
    try:
        return nfc_native.create_text_ndef(language_code, text)
    except Exception as e:
        logger.error(f"Error creating NDEF text record: {e}")
        return None


def write_ndef_to_tag(ndef_data: bytes, timeout: float = 30.0) -> bool:
    """
    Write pre-created NDEF data to an NFC tag.
    
    Args:
        ndef_data: NDEF record data to write
        timeout: Maximum time to wait for a tag (seconds)
        
    Returns:
        bool: True if successful, False otherwise
        
    Example:
        ndef_data = nfc_reader.create_ndef_text_record("Hello, World!")
        if ndef_data:
            success = nfc_reader.write_ndef_to_tag(ndef_data, timeout=30)
            if success:
                print("NDEF data written successfully!")
    """
    with NFCReader() as reader:
        reader.start_discovery()
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if reader.is_tag_present():
                logger.info("Tag detected, writing NDEF data...")
                success = reader.write_ndef(ndef_data)
                if success:
                    logger.info(f"Successfully wrote NDEF data ({len(ndef_data)} bytes)")
                    return True
                else:
                    logger.error("Failed to write NDEF data to tag")
                    return False
            time.sleep(0.1)
        
        logger.info("Timeout waiting for tag")
        return False


# Module-level functions for backward compatibility and convenience

def initialize() -> bool:
    """Initialize NFC (convenience function)."""
    return nfc_native.initialize()

def deinitialize() -> bool:
    """Deinitialize NFC (convenience function)."""
    return nfc_native.deinitialize()

def start_discovery() -> None:
    """Start discovery (convenience function)."""
    nfc_native.start_discovery()

def stop_discovery() -> None:
    """Stop discovery (convenience function)."""
    nfc_native.stop_discovery()


if __name__ == "__main__":
    # Simple test/demo when run directly
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("NFC Text Reader Demo")
    print("===================")
    print("Place an NFC tag with text near the reader...")
    
    try:
        # Test simple text reading
        text = read_text_from_tag(timeout=30)
        if text:
            print(f"\n✓ Success! Found text: '{text}'")
        else:
            print("\n✗ No text found or timeout reached")
            
        # Test comprehensive data reading
        print("\nGetting detailed tag information...")
        data = get_tag_data(timeout=30)
        if data:
            print("\n✓ Tag details:")
            for key, value in data.items():
                print(f"  {key}: {value}")
        else:
            print("\n✗ No tag found or timeout reached")
            
    except NFCInitializationError as e:
        print(f"\n✗ NFC initialization failed: {e}")
        print("Make sure you're running as root and NFC hardware is connected.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
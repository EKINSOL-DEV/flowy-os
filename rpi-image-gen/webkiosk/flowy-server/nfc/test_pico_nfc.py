#!/usr/bin/env python3
"""
Test script for Pi Pico NFC Bridge
"""

import sys
import time
import argparse
from pico_nfc_bridge import PicoNFCReader, NFCError, NFCInitializationError

def test_basic_connection(device_path=None):
    """Test basic connection and ping"""
    print("=== Testing Basic Connection ===")
    
    try:
        reader = PicoNFCReader(device_path=device_path)
        reader.initialize()
        print("✓ Successfully connected to Pi Pico NFC bridge")
        
        # Test ping
        if reader._ping():
            print("✓ Ping test successful")
        else:
            print("✗ Ping test failed")
        
        reader.cleanup()
        return True
        
    except NFCInitializationError as e:
        print(f"✗ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_tag_polling(device_path=None):
    """Test NFC tag polling"""
    print("\n=== Testing Tag Polling ===")
    
    try:
        reader = PicoNFCReader(device_path=device_path)
        reader.initialize()
        print("✓ Connected to Pi Pico NFC bridge")
        
        reader.start_discovery()
        print("✓ Started discovery")
        
        print("Please place an NFC tag near the reader within 10 seconds...")
        tag_data = reader.wait_for_tag(timeout=10.0)
        
        if tag_data:
            print("✓ Tag detected!")
            print(f"  UID: {tag_data.get('uid', 'N/A')}")
            print(f"  Technology: {tag_data.get('technology_name', 'N/A')}")
            print(f"  Text: '{tag_data.get('text', 'No text content')}'")
            print(f"  Language: {tag_data.get('language', 'N/A')}")
        else:
            print("✗ No tag detected within timeout")
        
        reader.cleanup()
        return tag_data is not None
        
    except Exception as e:
        print(f"✗ Error during tag polling: {e}")
        return False

def test_tag_writing(device_path=None, text="Hello from Pi Pico NFC!"):
    """Test NFC tag writing"""
    print("\n=== Testing Tag Writing ===")
    
    try:
        reader = PicoNFCReader(device_path=device_path)
        reader.initialize()
        print("✓ Connected to Pi Pico NFC bridge")
        
        reader.start_discovery()
        print("✓ Started discovery")
        
        print(f"Please place a writable NFC tag near the reader...")
        print(f"Will write text: '{text}'")
        
        success = reader.write_text(text)
        
        if success:
            print("✓ Text written successfully!")
        else:
            print("✗ Failed to write text to tag")
        
        reader.cleanup()
        return success
        
    except Exception as e:
        print(f"✗ Error during tag writing: {e}")
        return False

def test_multiple_tags(device_path=None):
    """Test multiple tag detection"""
    print("\n=== Testing Multiple Tag Detection ===")
    
    try:
        reader = PicoNFCReader(device_path=device_path)
        reader.initialize()
        print("✓ Connected to Pi Pico NFC bridge")
        
        reader.start_discovery()
        print("✓ Started discovery")
        
        print("Please place 2 NFC tags near the reader within 15 seconds...")
        tag_data_list = reader.wait_for_multiple_tags(min_tags=2, timeout=15.0)
        
        if tag_data_list:
            print(f"✓ Detected {len(tag_data_list)} tags!")
            for i, tag_data in enumerate(tag_data_list, 1):
                print(f"  Tag {i}:")
                print(f"    UID: {tag_data.get('uid', 'N/A')}")
                print(f"    Technology: {tag_data.get('technology_name', 'N/A')}")
                print(f"    Text: '{tag_data.get('text', 'No text content')}'")
        else:
            print("✗ Failed to detect minimum number of tags")
        
        reader.cleanup()
        return tag_data_list is not None
        
    except Exception as e:
        print(f"✗ Error during multiple tag detection: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test Pi Pico NFC Bridge")
    parser.add_argument("--device", help="USB serial device path (e.g., /dev/ttyACM0)")
    parser.add_argument("--test", choices=["connection", "polling", "writing", "multiple", "all"], 
                       default="all", help="Test to run")
    parser.add_argument("--write-text", default="Hello from Pi Pico NFC!", 
                       help="Text to write in writing test")
    
    args = parser.parse_args()
    
    print("Pi Pico NFC Bridge Test Suite")
    print("=" * 40)
    
    if args.device:
        print(f"Using device: {args.device}")
    else:
        print("Auto-detecting USB device...")
    
    results = {}
    
    if args.test in ["connection", "all"]:
        results["connection"] = test_basic_connection(args.device)
    
    if args.test in ["polling", "all"]:
        results["polling"] = test_tag_polling(args.device)
    
    if args.test in ["writing", "all"]:
        results["writing"] = test_tag_writing(args.device, args.write_text)
    
    if args.test in ["multiple", "all"]:
        results["multiple"] = test_multiple_tags(args.device)
    
    # Summary
    print("\n=== Test Results Summary ===")
    passed = 0
    total = 0
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        total += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
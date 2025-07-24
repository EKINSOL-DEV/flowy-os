# ST25R3916 NFC Reader

This module provides NFC tag reading and writing functionality using the ST25R3916 chip over SPI.

## Hardware Setup

Connect the ST25R3916 module to your Raspberry Pi:

- **SPI0 MOSI** (GPIO 10) → ST25R3916 MOSI
- **SPI0 MISO** (GPIO 9) → ST25R3916 MISO  
- **SPI0 SCLK** (GPIO 11) → ST25R3916 SCLK
- **SPI0 CE0** (GPIO 8) → ST25R3916 CS
- **GPIO 22** → ST25R3916 RST (Reset)
- **GPIO 18** → ST25R3916 IRQ (Interrupt)
- **3.3V** → ST25R3916 VCC
- **GND** → ST25R3916 GND

## Testing the Hardware

### 1. Enable SPI

Make sure SPI is enabled on your Pi:
```bash
sudo raspi-config
# Go to Interface Options > SPI > Enable
```

### 2. Run the Test Script

Navigate to the NFC directory and run the test:
```bash
cd /flowy/server/nfc
sudo python test_nfc.py
```

**Why sudo?** GPIO and SPI access require root permissions.

### 3. Expected Output

```
ST25R3916 NFC Test
==============================

1. Initializing ST25R3916...
   ✓ ST25R3916 initialized

2. Testing register communication...
   Register 0x00 (IO_CONF1): 0x00
   Write/Read test - Expected: 0x55, Got: 0x55
   ✓ Register communication working

3. Initializing NFC reader...
   ✓ NFC reader initialized

4. Testing NFC tag detection...
   Place an NFC tag near the reader...
   Attempt 1/5...
   ✓ NFC tag detected!
     UID: 04A1B2C3D4E5F6
     Type: MIFARE Ultralight
     UID bytes: ['0x04', '0xA1', '0xB2', '0xC3', '0xD4', '0xE5', '0xF6']

5. Testing field control...
   Turning field off...
   Turning field on...
   ✓ Field control working

6. Test completed!

Cleanup completed
```

## Supported NFC Tags

- **NTAG213** - Your tags will be detected as "MIFARE Ultralight"
- **MIFARE Ultralight** - 4-byte blocks, no authentication needed
- **MIFARE Classic** - Not yet implemented (needs authentication)

## Using the API Server

Start the NFC API server:
```bash
cd /flowy/server/nfc
sudo /flowy/server/.venv/bin/python nfc_api.py
```

The server runs on **http://localhost:10001**

### API Endpoints

- `GET /status` - Check if NFC reader is working
- `GET /detect` - Detect NFC tag in field
- `POST /tag/read` - Read block from tag
- `POST /tag/write` - Write block to tag
- `POST /field/on` - Turn on NFC field
- `POST /field/off` - Turn off NFC field

### Example Usage

```bash
# Check status
curl http://localhost:10001/status

# Detect a tag (place NTAG213 near reader first)
curl http://localhost:10001/detect

# Read block 4 (first user data block)
curl -X POST http://localhost:10001/tag/read -H "Content-Type: application/json" -d '{"block_number": 4}'

# Write "TEST" to block 4
curl -X POST http://localhost:10001/tag/write -H "Content-Type: application/json" -d '{"block_number": 4, "data": [84, 69, 83, 84]}'
```

## NTAG213 Memory Layout

- **Block 0-3**: Header/UID (read-only)
- **Block 4-39**: User data (180 bytes total)
- **Block 40-44**: Configuration pages

**Safe blocks to write:** 4-39

## Troubleshooting

### "Permission denied" errors
Run with `sudo` - SPI and GPIO need root access.

### "No response" errors  
- Check wiring connections
- Verify SPI is enabled
- Make sure ST25R3916 has power (3.3V)

### "No tag detected"
- Place tag closer to antenna
- Try different tag orientation
- Verify tag is NTAG213 or compatible

### Service not starting
Check logs: `sudo journalctl -u flowy-nfcserver -f`
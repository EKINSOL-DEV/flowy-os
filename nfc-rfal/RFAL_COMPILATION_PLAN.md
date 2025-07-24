# RFAL Compilation Plan for ST25R3916 on Raspberry Pi 5

## Current Status
- ✅ Complete RFAL package downloaded and organized
- ✅ Pi 5 platform layer created (platform_pi5.c, platform_pi5.h)
- ✅ Platform configuration header (rfal_platform.h) 
- ✅ Makefile structure in place
- ❌ Compilation fails with missing `rfalAnalogConfigDefaultSettings`

## Root Cause Analysis
The missing symbol `rfalAnalogConfigDefaultSettings` is defined in:
- **File**: `source/st25r3916/rfal_analogConfigTbl.h`
- **Type**: Large const uint8_t array with ST25R3916 analog configuration
- **Issue**: Header file not being included properly during compilation

## Next Steps to Fix Compilation

### Step 1: Test Minimal Compilation
```bash
# From within /home/builder/nfc_comp directory:
gcc -I./include -I./source/st25r3916 -I./source -I. -c platform_pi5.c -o platform_pi5.o
```

### Step 2: Compile Analog Config Source
```bash
gcc -I./include -I./source/st25r3916 -I./source -I. -c source/rfal_analogConfig.c -o source/rfal_analogConfig.o
```

### Step 3: Create Simple Test Program
Compile `test_minimal.c` to verify symbols are accessible:
```bash
gcc -I./include -I./source/st25r3916 -I./source -I. -o test_minimal test_minimal.c platform_pi5.o source/rfal_analogConfig.o -lm
```

### Step 4: Build Complete Library
```bash
make clean
make all
```

### Step 5: Test Platform Integration
```bash
./test_minimal
```

## Key Files and Their Roles

### Core Platform Files
- `platform_pi5.c` - Pi 5 hardware abstraction (SPI, GPIO, timing)
- `platform_pi5.h` - Platform function declarations
- `rfal_platform.h` - RFAL configuration overrides for Pi 5

### Critical RFAL Sources
- `source/rfal_analogConfig.c` - Uses `rfalAnalogConfigDefaultSettings`
- `source/st25r3916/rfal_analogConfigTbl.h` - Defines `rfalAnalogConfigDefaultSettings`
- `source/st25r3916/st25r3916.c` - Main ST25R3916 driver
- `source/st25r3916/st25r3916_com.c` - SPI communication layer

### Header Dependencies
- `include/rfal_analogConfig.h` - Main analog config interface
- `source/st25r3916/st25r3916.h` - Chip definitions
- `source/st25r3916/rfal_features.h` - Feature configuration

## Expected Compilation Issues and Solutions

### Issue 1: Missing rfalAnalogConfigDefaultSettings
**Solution**: Ensure `source/st25r3916/rfal_analogConfigTbl.h` is included
**Fix**: Add explicit include in Makefile or source files

### Issue 2: Platform Function Conflicts  
**Solution**: Our platform functions match RFAL expected signatures
**Verify**: Check `platform_pi5.h` declarations match RFAL requirements

### Issue 3: Missing Hardware Dependencies
**Solution**: Install build tools and SPI libraries
```bash
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r)
```

## Hardware Configuration Confirmed Working
From our Python testing, we know these ST25R3916 settings work:
- **SPI Bus**: 0 (not 10)
- **IRQ Pin**: GPIO 17 
- **Reset Pin**: GPIO 22
- **SPI Speed**: 1MHz
- **Register Config**: Working analog frontend values identified

## Success Criteria
1. ✅ Clean compilation with no undefined symbols
2. ✅ `test_minimal` runs without errors
3. ✅ Platform init/deinit functions work
4. ✅ RFAL library accessible from test programs

## Next Phase: NFC Tag Detection
Once compilation works:
1. Create RFAL-based NTAG213 detection test
2. Compare results with our Python attempts
3. Implement full read/write operations
4. Integrate into existing NFC API

## Fallback Plan
If RFAL compilation proves too complex:
- Document what we learned about ST25R3916 analog configuration
- Recommend PN532 module for production use
- Keep ST25R3916 driver for basic presence detection

## Notes
- All Pi 5 hardware interfaces confirmed working (SPI, GPIO, IRQ)
- ST25R3916 can transmit (proven by IRQ timing)
- RF reception needs proper analog tuning (RFAL's strength)
- Python implementation showed RF field can affect tags
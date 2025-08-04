# NFC Progress Log

## Hardware Setup
- **Target System**: Raspberry Pi CM5 (not Pi 5)
- **NFC Reader**: Custom wiring (not standard Pi pins)
- **I2C Bus**: Custom bus 4 (`/dev/i2c-4`)
- **Device Address**: 0x28 (when working)
- **GPIO Pins**: INT=25, ENABLE=9, FWDNLD=8

## Current Status (2025-08-04)
- ✅ **HARDWARE CONFIRMED WORKING**: Device appears at 0x28 on I2C bus 4 with manual GPIO sequence
- ✅ **GPIO CONFLICTS RESOLVED**: 
  - Fixed gpiochip4 → gpiochip0 in library
  - Disabled SPI to free GPIO8 from conflict
  - VEN logic inverted to match CM5 hardware (VEN=1 → GPIO9=0)
  - FWDNLD initialization fixed (starts at 0 instead of 1)
- ✅ **MANUAL SEQUENCE WORKS**: 
  - `gpioset gpiochip0 8=0 9=0` (LED bright)
  - `gpioset gpiochip0 9=1` (LED dimmer, device at 0x28)
- ❌ **LIBRARY STILL HANGS**: NfcService Init fails despite correct GPIO sequence

## Working Manual Sequence
```bash
# This sequence reliably brings device online at 0x28:
gpioset gpiochip0 8=0 9=0  # FWDNLD=0, VEN=0 (with inversion)
gpioset gpiochip0 9=1      # VEN=1 (with inversion) 
sudo i2cdetect -y 4        # Shows device at 0x28
```

## Library Issues Identified
1. **VEN Polarity**: Fixed - library now inverts VEN (0→GPIO high, 1→GPIO low)
2. **FWDNLD Init**: Fixed - starts at 0 instead of 1
3. **GPIO Chip**: Fixed - uses gpiochip0 instead of gpiochip4
4. **SPI Conflict**: Fixed - disabled SPI to free GPIO8

## Current Problem - DEBUGGER RESULTS
**Main thread stuck in nfcManager_doInitialize()** waiting on condition variable
**Thread 7 stuck in ioctl()** - likely I2C communication hanging
**Missing debug output**: OpenAndConfigure() and phTmlNfc_Init() debug messages never appear

**Key Finding**: Library gets stuck in GPIO reset loop BEFORE trying I2C
- GPIO reset works correctly (proper sequence observed)
- But library never progresses to I2C transport initialization  
- One thread is stuck in ioctl() call (probably I2C communication)
- Reset loop continues because some communication thread is blocked

**Root Cause IDENTIFIED**: Thread stuck in `wait4interrupt()` trying to read GPIO interrupt pin
- Stack: `ioctl()` → `gpiod_line_get_value()` → `wait4interrupt()` → `Read()`
- Background read thread is waiting for IRQ pin (GPIO25) to signal data ready
- But IRQ pin is not working/configured properly
- This blocks all I2C communication, causing endless reset attempts

## Investigation Status - BREAKTHROUGH!
- ✅ **FULL DEBUG TRACE WORKING**: All initialization steps now visible
- ✅ **I2C OPENS SUCCESSFULLY**: fd=7, transport layer working
- ✅ **IRQ PIN PARTIALLY WORKING**: Goes high during VEN=0 (power off), low during VEN=1 (power on)
- ❌ **IRQ TIMING ISSUE**: Pin goes high briefly then stays low, causing timeouts

## Key Pattern Discovered
**IRQ Pin Behavior**:
- VEN=0 (GPIO9=1, power off): IRQ pin = 1 (high) ✅
- VEN=1 (GPIO9=0, power on): IRQ pin = 0 (low) ❌
- First IRQ read usually succeeds, subsequent reads timeout
- Chip responds to initial commands but then stops asserting IRQ

**Root Cause**: Chip initialization sequence issue - NFC chip starts responding but gets stuck in a state where it stops asserting IRQ for new data
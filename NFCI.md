# PN7160 NFC Module Configuration for CM5 Board

## �� Hardware Connection Summary

| PN7160 Module Pin | Function                   | Connect to CM5 Pin | GPIO | Notes                          |
| ----------------- | -------------------------- | ------------------ | ---- | ------------------------------ |
| SDA               | I²C Data                   | Pin 22             | 25   | Software I²C Data              |
| SCL               | I²C Clock                  | Pin 21             | 9    | Software I²C Clock             |
| VEN               | Enable NFC chip            | Pin 7              | 4    | Chip enable/reset control      |
| IRQ               | Interrupt (active low)     | Pin 11             | 17   | Interrupt from NFC chip        |
| DWL               | Firmware download (unused) | Leave unconnected  | —    | Not used in normal operation   |
| BDD               | VCC for NFC IC             | Pin 1 or 17        | —    | 3.3V power                     |
| VANT              | VCC for antenna driver     | Pin 2 or 4         | —    | 5V power                       |
| GND               | Ground                     | Any GND pin        | —    | Ground connection              |

## �� Required Code Changes

### 1. Update I²C Transport Configuration

**File:** `src/nfcandroid_nfc_hidlimpl/halimpl/tml/transport/NfccAltTransport.h`

**Line 26:** Change I²C bus device path
```cpp
// Current:
#define I2C_BUS "/dev/i2c-1"

// Change to:
#define I2C_BUS "/dev/i2c-3"
```

### 2. Update GPIO Pin Definitions

**Same file:** `src/nfcandroid_nfc_hidlimpl/halimpl/tml/transport/NfccAltTransport.h`

**Lines 28-30:** Update pin assignments to match hardware
```cpp
// Current:
#define PIN_INT 23
#define PIN_ENABLE 24
#define PIN_FWDNLD 25

// Change to:
#define PIN_INT 17     // IRQ connected to GPIO17 (Pin 11)
#define PIN_ENABLE 4   // VEN connected to GPIO4 (Pin 7)
#define PIN_FWDNLD 25  // Keep unchanged (DWL unused)
```

### 3. Verify Transport Mode Configuration

**File:** `conf/libnfc-nxp.conf`

**Line 30:** Ensure alternative I²C transport is selected
```ini
# Should be set to:
NXP_TRANSPORT=0x02
```

**Transport options:**
- `0x00` - Normal I²C/SPI driver
- `0x01` - Not used
- `0x02` - Alternative I²C (what we need)
- `0x03` - Alternative SPI

## ��️ System Configuration

### 1. Raspberry Pi Boot Configuration

**File:** `/boot/config.txt`

Add the following line to enable software I²C on the specified pins:
```ini
dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=25,i2c_gpio_scl=9
```

**Reboot required after making this change:**
```bash
sudo reboot
```

### 2. Install I²C Tools (if not already installed)

```bash
sudo apt update
sudo apt install -y i2c-tools
```

## �� Testing and Verification

### 1. Verify I²C Bus Creation

After reboot, check that the software I²C bus was created:
```bash
ls /dev/i2c-*
# Should show: /dev/i2c-1 and /dev/i2c-3
```

### 2. Test I²C Communication

Scan for the PN7160 device on the new I²C bus:
```bash
sudo i2cdetect -y 3
```

**Expected output:**
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- 28 -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- --                         
```

The device should appear at address `0x28` (PN7160 default I²C address).

### 3. Verify GPIO Configuration

Once the NFC stack is running, check that GPIOs are properly exported:
```bash
ls /sys/class/gpio/
# Should show gpio4 and gpio17 directories after NFC service starts
```

### 4. Check GPIO States

```bash
# Check VEN pin (should be high when NFC is enabled)
cat /sys/class/gpio/gpio4/value

# Check IRQ pin direction (should be input)
cat /sys/class/gpio/gpio17/direction
```

## ��️ Build and Installation

### 1. Clean Build

```bash
make clean
make
```

### 2. Install Libraries

```bash
sudo make install
sudo ldconfig
```

### 3. Update Configuration

Ensure the configuration files are in the correct location:
```bash
sudo cp conf/libnfc-nxp.conf /etc/
sudo cp conf/libnfc-nci.conf /etc/
```

## �� Troubleshooting

### Problem: I²C Bus Not Created
**Symptoms:** `/dev/i2c-3` doesn't exist after reboot
**Solutions:**
1. Check `/boot/config.txt` syntax
2. Verify GPIO pins are not used by other overlays
3. Check `dmesg | grep i2c` for error messages

### Problem: Device Not Detected at 0x28
**Symptoms:** `i2cdetect` shows no device at address 0x28
**Solutions:**
1. Check physical connections
2. Verify power supplies (3.3V and 5V)
3. Check if PN7160 is properly powered
4. Measure voltages on VEN and IRQ pins

### Problem: GPIO Export Errors
**Symptoms:** Cannot export GPIO pins or permission denied
**Solutions:**
1. Run NFC service with sudo initially
2. Check if GPIOs are already exported by other processes
3. Verify GPIO numbers are correct for your Pi model

### Problem: Build Errors
**Symptoms:** Compilation fails
**Solutions:**
1. Ensure all dependencies are installed
2. Check for 64-bit specific patches if needed
3. Verify kernel headers are installed: `sudo apt install raspberrypi-kernel-headers`

## �� Additional Notes

### Software I²C vs Hardware I²C
- **Hardware I²C:** Uses dedicated I²C controllers (faster, less CPU overhead)
- **Software I²C:** Bit-banged via GPIO (more flexible pin assignment, slightly higher CPU usage)

### Pin Considerations
- GPIO25 and GPIO9 chosen for software I²C to avoid conflicts with other peripherals
- GPIO4 and GPIO5 selected for control signals as they're readily available
- Ensure these pins aren't used by other device tree overlays

### Performance Notes
- Software I²C typically operates at lower frequencies than hardware I²C
- For NFC applications, the speed difference is usually not significant
- Monitor CPU usage if running other intensive applications simultaneously

## �� References

- [NXP PN7160 Documentation](https://www.nxp.com/products/identification-and-security/nfc/nfc-reader-ics:NFC-READER)
- [Raspberry Pi GPIO Pinout](https://pinout.xyz/)
- [I²C Device Tree Overlays](https://www.raspberrypi.org/documentation/configuration/device-tree.md)

---
**Last Updated:** August 2025  
**Tested On:** Raspberry Pi 5 with CM5 custom board  
**NFC Module:** Elechouse PN7160/1 V2
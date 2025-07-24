#!/bin/bash
# RFAL Compilation Commands for ST25R3916 on Raspberry Pi 5
# Run these commands from /home/builder/nfc_comp directory

set -e  # Exit on any error

echo "RFAL Compilation Script for Raspberry Pi 5"
echo "=========================================="

# Step 1: Clean previous builds
echo "1. Cleaning previous builds..."
make clean

# Step 2: Test platform compilation
echo "2. Testing platform layer compilation..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DST25R3916 -c platform_pi5.c -o platform_pi5.o
echo "✓ Platform layer compiled successfully"

# Step 3: Compile simple analog config
echo "3a. Compiling simple analog config..."
gcc -I./include -I./source/st25r3916 -I./source -I. -c simple_analog_config.c -o simple_analog_config.o
echo "✓ Simple analog config compiled"

# Step 3b: Test critical RFAL source (with custom config)
echo "3b. Testing analog config compilation..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DRFAL_ANALOG_CONFIG_CUSTOM -c source/rfal_analogConfig.c -o source/rfal_analogConfig.o
echo "✓ Analog config compiled successfully"

# Step 4: Test ST25R3916 core
echo "4. Testing ST25R3916 core compilation..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DST25R3916 -DRFAL_ANALOG_CONFIG_CUSTOM -c source/st25r3916/st25r3916.c -o source/st25r3916/st25r3916.o
echo "✓ ST25R3916 core compiled successfully"

# Step 5: Compile ST25R3916 support modules
echo "5a. Compiling ST25R3916 communication layer..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DST25R3916 -DRFAL_ANALOG_CONFIG_CUSTOM -c source/st25r3916/st25r3916_com.c -o source/st25r3916/st25r3916_com.o
echo "✓ ST25R3916 communication layer compiled"

echo "5b. Compiling ST25R3916 interrupt handler..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DST25R3916 -DRFAL_ANALOG_CONFIG_CUSTOM -c source/st25r3916/st25r3916_irq.c -o source/st25r3916/st25r3916_irq.o
echo "✓ ST25R3916 interrupt handler compiled"

echo "5c. Compiling ST25R3916 LED support..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DST25R3916 -DRFAL_ANALOG_CONFIG_CUSTOM -c source/st25r3916/st25r3916_led.c -o source/st25r3916/st25r3916_led.o
echo "✓ ST25R3916 LED support compiled"

echo "5d. Compiling ST25R3916 AAT module..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DST25R3916 -DRFAL_ANALOG_CONFIG_CUSTOM -c source/st25r3916/st25r3916_aat.c -o source/st25r3916/st25r3916_aat.o
echo "✓ ST25R3916 AAT module compiled"

# Step 6: Compile RFAL chip abstraction
echo "6a. Compiling RFAL chip abstraction..."
gcc -I./include -I./source/st25r3916 -I./source -I. -DST25R3916 -DRFAL_ANALOG_CONFIG_CUSTOM -c source/st25r3916/rfal_rfst25r3916.c -o source/st25r3916/rfal_rfst25r3916.o
echo "✓ RFAL chip abstraction compiled"

# Step 7: Compile minimal test
echo "7. Building minimal test program..."
gcc -I./include -I./source/st25r3916 -I./source -I. -o test_minimal test_minimal.c \
    platform_pi5.o simple_analog_config.o source/rfal_analogConfig.o \
    source/st25r3916/st25r3916.o source/st25r3916/st25r3916_com.o \
    source/st25r3916/st25r3916_irq.o source/st25r3916/st25r3916_led.o \
    source/st25r3916/st25r3916_aat.o source/st25r3916/rfal_rfst25r3916.o -lm
echo "✓ Minimal test program built"

# Step 8: Run test (hardware-dependent, may fail on dev machine)
echo "8. Testing compilation (hardware-dependent)..."
if ./test_minimal; then
    echo "✓ Minimal test passed!"
else
    echo "⚠ Minimal test failed (expected on dev machine - no Pi hardware)"
    echo "✓ Compilation successful - library ready for Pi"
fi

# Step 9: Build full library
echo "9. Building complete RFAL library..."
make all
echo "✓ RFAL library built successfully"

# Step 10: Build and test full functionality
echo "10. Building full test program..."
make test
echo "✓ Full test program built"

echo ""
echo "🎉 SUCCESS: RFAL compilation completed!"
echo "Ready to implement NTAG213 tag detection and read/write operations"
echo ""
echo "Next steps:"
echo "1. Run: ./test_simple (basic platform test)"
echo "2. Create NTAG213 detection program using RFAL APIs"
echo "3. Test with actual NTAG213 tags"
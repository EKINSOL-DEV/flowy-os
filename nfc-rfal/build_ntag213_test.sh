#!/bin/bash
# Build NTAG213 RFAL test program for Raspberry Pi

set -e

echo "Building NTAG213 RFAL Test Program"
echo "=================================="

# First build the complete RFAL library (if not already built)
if [ ! -f "librfal.so" ]; then
    echo "1. Building RFAL library..."
    make clean
    make all
else
    echo "1. RFAL library already exists"
fi

# Build the simple NTAG213 test program
echo "2. Building simple NTAG213 test program..."
gcc -I./include -I./source/st25r3916 -I./source -I. \
    -o simple_ntag213_test simple_ntag213_test.c -L. -lrfal -lm

echo "✓ Simple NTAG213 test program built successfully!"
echo ""
echo "To test on Raspberry Pi:"
echo "1. Copy simple_ntag213_test and librfal.so to your Pi"
echo "2. Run: sudo LD_LIBRARY_PATH=. ./simple_ntag213_test"
echo "3. Place NTAG213 tag near ST25R3916 reader"
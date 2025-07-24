#!/bin/bash
# Build RFAL library and create source archive for Pi deployment

echo "Building RFAL library..."
cd /home/builder/flowy-os/nfc-rfal

# Clean and attempt to build (will fail without lgpio, but that's expected)
make clean
make all
build_result=$?

# Always create the source archive regardless of build success
echo ""
echo "Creating source archive for Pi deployment..."
cd /home/builder/flowy-os
tar -czf drivers/nfc-rfal-source.tar.gz \
    --exclude='*.o' \
    --exclude='*.so' \
    --exclude='*test' \
    --exclude='.git*' \
    nfc-rfal/

if [ -f drivers/nfc-rfal-source.tar.gz ]; then
    archive_size=$(du -h drivers/nfc-rfal-source.tar.gz | cut -f1)
    echo "✓ Source archive created: drivers/nfc-rfal-source.tar.gz ($archive_size)"
    echo "✓ Available for download at: http://your-server/drivers/nfc-rfal-source.tar.gz"
else
    echo "✗ Failed to create source archive"
    exit 1
fi

# Report build status and copy binaries
if [ $build_result -eq 0 ]; then
    echo ""
    echo "✓ RFAL library compiled successfully!"
    
    # Copy built binaries to drivers directory for web download
    echo "📦 Copying built binaries to drivers directory..."
    if [ -f nfc-rfal/librfal.so ]; then
        cp nfc-rfal/librfal.so drivers/
        echo "  ✓ librfal.so ($(du -h drivers/librfal.so | cut -f1))"
    fi
    
    if [ -f nfc-rfal/simple_ntag213_test ]; then
        cp nfc-rfal/simple_ntag213_test drivers/
        chmod +x drivers/simple_ntag213_test
        echo "  ✓ simple_ntag213_test ($(du -h drivers/simple_ntag213_test | cut -f1))"
    fi
    
    echo ""
    echo "🌐 All files now available for download:"
    echo "   http://your-server/drivers/librfal.so"
    echo "   http://your-server/drivers/simple_ntag213_test" 
    echo "   http://your-server/drivers/nfc-rfal-source.tar.gz"
    echo ""
    echo "📋 To test on Pi:"
    echo "   wget http://your-server/drivers/librfal.so"
    echo "   wget http://your-server/drivers/simple_ntag213_test"
    echo "   chmod +x simple_ntag213_test"
    echo "   sudo LD_LIBRARY_PATH=. ./simple_ntag213_test"
else
    echo ""
    echo "ℹ RFAL compilation failed (expected without lgpio on build machine)"
    echo "📋 To build on Pi:"
    echo "   wget http://your-server/drivers/nfc-rfal-source.tar.gz"
    echo "   tar -xzf nfc-rfal-source.tar.gz"
    echo "   cd nfc-rfal"
    echo "   sudo apt install build-essential liblgpio-dev"
    echo "   make clean && make all"
    echo "   sudo LD_LIBRARY_PATH=. ./simple_ntag213_test"
fi
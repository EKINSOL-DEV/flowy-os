#!/bin/bash
set -e

# APT Repository Update Script
# Automates the process of updating the Flowy OS APT repository

REPO_DIR="/var/www/apt-repo"
POOL_DIR="$REPO_DIR/pool/main"
DISTS_DIR="$REPO_DIR/dists/stable"
PACKAGES_DIR="$DISTS_DIR/main/binary-arm64"

echo "🔄 Updating Flowy OS APT Repository..."

# Check if we're in the right directory
if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Repository directory not found: $REPO_DIR"
    exit 1
fi

cd "$REPO_DIR"

# 1. Regenerate package metadata
echo "📦 Regenerating package metadata..."
dpkg-scanpackages pool/main /dev/null | sudo tee "$PACKAGES_DIR/Packages" > /dev/null
sudo gzip -f -k "$PACKAGES_DIR/Packages"

# 2. Create Release file with proper headers
echo "📝 Creating Release file..."
sudo tee "$DISTS_DIR/Release" > /dev/null << EOF
Origin: Flowy OS Repository
Label: Flowy OS Repository
Suite: stable
Codename: stable
Version: 1.0
Architectures: arm64
Components: main
Description: Flowy OS Application Repository
Date: $(date -u '+%a, %d %b %Y %H:%M:%S GMT')
EOF

# 3. Append checksums to Release file
echo "🔐 Adding checksums to Release file..."
apt-ftparchive release dists/stable | sudo tee -a "$DISTS_DIR/Release" > /dev/null

# 4. Fix ownership
echo "👤 Fixing file ownership..."
sudo chown www-data:www-data "$DISTS_DIR/Release"
sudo chown www-data:www-data "$PACKAGES_DIR/Packages"
sudo chown www-data:www-data "$PACKAGES_DIR/Packages.gz"

# 5. Generate GPG key if needed
if ! gpg --list-secret-keys "apt@funnpunn.com" > /dev/null 2>&1; then
    echo "🔑 Generating new GPG key..."
    gpg --batch --generate-key <<EOF
%no-protection
Key-Type: RSA
Key-Length: 2048
Name-Real: Flowy APT Repository
Name-Email: apt@funnpunn.com
Expire-Date: 2y
%commit
EOF
    echo "✅ GPG key generated"
    
    # Export public key
    echo "📤 Exporting public key..."
    gpg --armor --export apt@funnpunn.com > "$REPO_DIR/flowy-apt-key.gpg"
    sudo chown www-data:www-data "$REPO_DIR/flowy-apt-key.gpg"
fi

# 6. Sign Release file
echo "✍️  Signing Release file..."
if gpg --armor --detach-sign --default-key "apt@funnpunn.com" --output /tmp/Release.gpg "$DISTS_DIR/Release" 2>/dev/null; then
    sudo mv /tmp/Release.gpg "$DISTS_DIR/Release.gpg"
    sudo chown www-data:www-data "$DISTS_DIR/Release.gpg"
    echo "✅ Release file signed successfully"
else
    echo "⚠️  GPG signing failed, removing old signature"
    sudo rm -f "$DISTS_DIR/Release.gpg"
fi

echo ""
echo "✅ Repository update complete!"
echo ""
echo "📊 Repository status:"
echo "   Packages: $(ls -1 $POOL_DIR/*.deb 2>/dev/null | wc -l) deb files"
echo "   Signed: $([ -f "$DISTS_DIR/Release.gpg" ] && echo "Yes" || echo "No")"
echo ""
echo "🔧 To update on Pi devices:"
if [ -f "$DISTS_DIR/Release.gpg" ]; then
    echo "   # First time setup (add GPG key):"
    echo "   wget -qO- http://apt.funnpunn.com/apt/flowy-apt-key.gpg | sudo tee /etc/apt/trusted.gpg.d/flowy.asc > /dev/null"
    echo ""
    echo "   # Then update normally:"
    echo "   sudo apt update"
else
    echo "   sudo apt update --allow-unauthenticated"
fi
echo ""
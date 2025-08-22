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

# 1. Regenerate package metadata (with multiversion support)
echo "📦 Regenerating package metadata..."
dpkg-scanpackages --multiversion pool/main /dev/null | sudo tee "$PACKAGES_DIR/Packages" > /dev/null
sudo gzip -f -k "$PACKAGES_DIR/Packages"

# 2. Create Release file with proper headers (using current UTC time to avoid future timestamp issues)
echo "📝 Creating Release file..."
CURRENT_DATE=$(date -u '+%a, %d %b %Y %H:%M:%S GMT')
echo "Using timestamp: $CURRENT_DATE"

# Use apt-ftparchive to generate the entire Release file with proper checksums
apt-ftparchive -o APT::FTPArchive::Release::Origin="Flowy OS Repository" \
  -o APT::FTPArchive::Release::Label="Flowy OS Repository" \
  -o APT::FTPArchive::Release::Suite="stable" \
  -o APT::FTPArchive::Release::Codename="stable" \
  -o APT::FTPArchive::Release::Version="1.0" \
  -o APT::FTPArchive::Release::Architectures="arm64" \
  -o APT::FTPArchive::Release::Components="main" \
  -o APT::FTPArchive::Release::Description="Flowy OS Application Repository" \
  release dists/stable | sudo tee "$DISTS_DIR/Release" > /dev/null

# 4. Fix ownership
echo "👤 Fixing file ownership..."
sudo chown www-data:www-data "$DISTS_DIR/Release"
sudo chown www-data:www-data "$PACKAGES_DIR/Packages"
sudo chown www-data:www-data "$PACKAGES_DIR/Packages.gz"

# 5. Use the stable GPG key (from APT_Repo.md documentation)
echo "🔑 Using stable GPG key..."
STABLE_KEY_ID="09ACB7381B4C0DD989E0A72F9E405D6740651822"

if gpg --list-secret-keys "$STABLE_KEY_ID" > /dev/null 2>&1; then
    echo "✅ Stable GPG key found: $STABLE_KEY_ID"
    SIGNING_KEY="$STABLE_KEY_ID"
else
    echo "❌ Stable GPG key not found: $STABLE_KEY_ID"
    echo ""
    echo "Available keys for apt@funnpunn.com:"
    gpg --list-secret-keys "apt@funnpunn.com" 2>/dev/null || echo "   No keys found"
    echo ""
    echo "Please ensure the stable key is available or import it."
    exit 1
fi

# Always export the stable public key
echo "📤 Exporting stable public key..."
gpg --armor --export "$STABLE_KEY_ID" | sudo tee "$REPO_DIR/flowy-apt-key.gpg" > /dev/null
sudo chown www-data:www-data "$REPO_DIR/flowy-apt-key.gpg"

# 6. Sign Release file with the stable key
echo "✍️  Signing Release file with stable key..."
if gpg --armor --detach-sign --default-key "$SIGNING_KEY" --output /tmp/Release.gpg "$DISTS_DIR/Release" 2>/dev/null; then
    sudo mv /tmp/Release.gpg "$DISTS_DIR/Release.gpg"
    sudo chown www-data:www-data "$DISTS_DIR/Release.gpg"
    echo "✅ Release file signed successfully with key: $SIGNING_KEY"
else
    echo "❌ GPG signing failed with key: $SIGNING_KEY"
    echo "   Removing old signature file"
    sudo rm -f "$DISTS_DIR/Release.gpg"
    exit 1
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
    echo "   # First time setup (add GPG key to correct location):"
    echo "   sudo mkdir -p /usr/share/keyrings/"
    echo "   wget -qO- http://apt.funnpunn.com/apt/flowy-apt-key.gpg | sudo tee /usr/share/keyrings/flowy.asc > /dev/null"
    echo "   sudo chmod a+r /usr/share/keyrings/flowy.asc"
    echo ""
    echo "   # Then update normally:"
    echo "   sudo apt update"
else
    echo "   sudo apt update --allow-unauthenticated"
fi
echo ""
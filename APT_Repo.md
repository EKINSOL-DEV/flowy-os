# Flowy OS APT Repository

## Repository Information
- **URL**: http://apt.funnpunn.com/apt
- **Distribution**: stable
- **Component**: main
- **Architecture**: arm64
- **Location**: `/var/www/apt-repo/`

## Client Setup

### Adding the Repository
```bash
# Download and add the GPG key
wget -qO- http://apt.funnpunn.com/apt/flowy-apt-key.gpg | sudo apt-key add -

# Add repository to sources list
echo "deb http://apt.funnpunn.com/apt stable main" | sudo tee /etc/apt/sources.list.d/flowy.list

# Update package list
sudo apt update

# Install packages
sudo apt install flowy-app
```

### Modern Key Management (Recommended)
```bash
# Add GPG key to new location (avoids deprecation warning)
wget -qO- http://apt.funnpunn.com/apt/flowy-apt-key.gpg | sudo tee /etc/apt/trusted.gpg.d/flowy.asc

# Add repository
echo "deb http://apt.funnpunn.com/apt stable main" | sudo tee /etc/apt/sources.list.d/flowy.list
sudo apt update
```

## Repository Management

### Adding New Packages
1. Copy `.deb` files to `/var/www/apt-repo/pool/main/`
2. Regenerate package metadata:
   ```bash
   cd /var/www/apt-repo
   dpkg-scanpackages pool/main /dev/null > dists/stable/main/binary-arm64/Packages
   gzip -k dists/stable/main/binary-arm64/Packages
   ```
3. Update Release file:
   ```bash
   apt-ftparchive release dists/stable > /tmp/release-body
   cat > /tmp/release-header << EOF
   Origin: Flowy OS Repository
   Label: Flowy OS Repository
   Suite: stable
   Codename: stable
   Version: 1.0
   Architectures: arm64
   Components: main
   Description: Flowy OS Application Repository
   EOF
   cat /tmp/release-header /tmp/release-body > /tmp/Release
   sudo mv /tmp/Release dists/stable/Release
   sudo chown www-data:www-data dists/stable/Release
   ```
4. Re-sign the Release file:
   ```bash
   gpg --armor --detach-sign --output /tmp/Release.gpg dists/stable/Release
   sudo mv /tmp/Release.gpg dists/stable/Release.gpg
   sudo chown www-data:www-data dists/stable/Release.gpg
   ```

### Directory Structure
```
/var/www/apt-repo/
├── dists/
│   └── stable/
│       ├── Release
│       ├── Release.gpg
│       └── main/
│           └── binary-arm64/
│               ├── Packages
│               └── Packages.gz
├── pool/
│   └── main/
│       └── *.deb files
└── flowy-apt-key.gpg
```

### Nginx Configuration
The repository is served via nginx with this location block in `/etc/nginx/sites-available/default`:
```nginx
location /apt/ {
    alias /var/www/apt-repo/;
    autoindex on;
}
```

### GPG Key Information
- **Key ID**: 09ACB7381B4C0DD989E0A72F9E405D6740651822
- **Name**: Flowy APT Repository
- **Email**: apt@funnpunn.com
- **Type**: RSA 3072-bit
- **Expires**: 2027-08-19

## Troubleshooting

### Permission Issues
Ensure all files are owned by `www-data`:
```bash
sudo chown -R www-data:www-data /var/www/apt-repo/
```

### Testing Repository
Visit http://apt.funnpunn.com/apt/ in a browser to verify the repository is accessible.

### Re-signing After Updates
Always re-sign the Release file after making changes:
```bash
gpg --armor --detach-sign --output /tmp/Release.gpg /var/www/apt-repo/dists/stable/Release
sudo mv /tmp/Release.gpg /var/www/apt-repo/dists/stable/Release.gpg
sudo chown www-data:www-data /var/www/apt-repo/dists/stable/Release.gpg
```
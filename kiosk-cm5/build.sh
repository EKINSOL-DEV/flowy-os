#!/bin/bash
# Kiosk CM5 Image Build Script

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_NAME="kiosk-multi-service"
EXAMPLE_DIR="./examples/kiosk-cm5"
OUTPUT_DIR="work/${CONFIG_NAME}/artefacts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is required for image building."
    else
        log_error "This script requires root privileges. Please run with sudo."
        exit 1
    fi
    
    # Check if we're in the rpi-image-gen directory
    if [[ ! -f "build.sh" ]] || [[ ! -d "scripts" ]]; then
        log_error "This script must be run from the rpi-image-gen directory."
        log_info "Please clone rpi-image-gen and copy the kiosk-cm5 example into examples/"
        exit 1
    fi
    
    # Check if dependencies are installed
    if [[ ! -f ".deps_installed" ]]; then
        log_warning "Dependencies may not be installed. Running install_deps.sh..."
        ./install_deps.sh
        touch .deps_installed
    fi
    
    # Check available disk space (need at least 10GB)
    available_space=$(df . | awk 'NR==2 {print $4}')
    required_space=10485760  # 10GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        log_error "Insufficient disk space. Need at least 10GB free."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Prepare build environment
prepare_environment() {
    log_info "Preparing build environment..."
    
    # Create work directory if it doesn't exist
    mkdir -p "work"
    
    # Copy example to correct location if not already there
    if [[ ! -d "examples/kiosk-cm5" ]]; then
        log_info "Copying kiosk-cm5 example to examples directory..."
        cp -r "${SCRIPT_DIR}" "examples/kiosk-cm5"
    fi
    
    # Validate configuration files
    if [[ ! -f "examples/kiosk-cm5/${CONFIG_NAME}.cfg" ]]; then
        log_error "Configuration file ${CONFIG_NAME}.cfg not found"
        exit 1
    fi
    
    # Check customization scripts
    for script in examples/kiosk-cm5/bdebstrap/customize*; do
        if [[ -f "$script" ]] && [[ ! -x "$script" ]]; then
            log_warning "Making $script executable"
            chmod +x "$script"
        fi
    done
    
    log_success "Build environment prepared"
}

# Validate configuration
validate_config() {
    log_info "Validating configuration..."
    
    local config_file="examples/kiosk-cm5/${CONFIG_NAME}.cfg"
    
    # Basic syntax check
    if ! grep -q "^\[" "$config_file"; then
        log_error "Invalid configuration file format"
        exit 1
    fi
    
    # Check for required packages
    required_packages=("nginx" "python3" "docker.io" "chromium-browser")
    for package in "${required_packages[@]}"; do
        if ! grep -q "$package" "$config_file"; then
            log_warning "Package $package not found in configuration"
        fi
    done
    
    log_success "Configuration validation passed"
}

# Build image
build_image() {
    log_info "Starting image build process..."
    log_info "This may take 30-60 minutes depending on your system..."
    
    # Record start time
    start_time=$(date +%s)
    
    # Run the build
    log_info "Executing: ./build.sh -c $CONFIG_NAME -D $EXAMPLE_DIR"
    
    if ./build.sh -c "$CONFIG_NAME" -D "$EXAMPLE_DIR"; then
        log_success "Image build completed successfully"
    else
        log_error "Image build failed"
        exit 1
    fi
    
    # Record end time and calculate duration
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    minutes=$((duration / 60))
    seconds=$((duration % 60))
    
    log_success "Build completed in ${minutes}m ${seconds}s"
}

# Post-build operations
post_build() {
    log_info "Performing post-build operations..."
    
    # Check if output exists
    if [[ ! -d "$OUTPUT_DIR" ]]; then
        log_error "Output directory not found: $OUTPUT_DIR"
        exit 1
    fi
    
    # Find the generated image
    image_file=$(find "$OUTPUT_DIR" -name "*.img" -type f | head -1)
    
    if [[ -n "$image_file" ]]; then
        log_success "Image created: $image_file"
        
        # Get image size
        image_size=$(du -h "$image_file" | cut -f1)
        log_info "Image size: $image_size"
        
        # Create checksum
        log_info "Generating checksums..."
        cd "$(dirname "$image_file")"
        sha256sum "$(basename "$image_file")" > "$(basename "$image_file").sha256"
        md5sum "$(basename "$image_file")" > "$(basename "$image_file").md5"
        
        # Create deployment script
        create_deployment_script "$(dirname "$image_file")"
        
        log_success "Post-build operations completed"
        
        # Display final information
        echo ""
        echo "========================================"
        echo "         BUILD COMPLETED SUCCESSFULLY   "
        echo "========================================"
        echo "Image location: $image_file"
        echo "Image size: $image_size"
        echo "Checksums: SHA256 and MD5 created"
        echo ""
        echo "To deploy:"
        echo "1. Flash to SD card: sudo dd if=$image_file of=/dev/sdX bs=4M status=progress"
        echo "2. Or use Raspberry Pi Imager"
        echo "3. Run deployment script for additional setup"
        echo ""
        
    else
        log_error "No image file found in output directory"
        exit 1
    fi
}

# Create deployment script
create_deployment_script() {
    local output_dir="$1"
    local deploy_script="$output_dir/deploy.sh"
    
    cat > "$deploy_script" << 'EOF'
#!/bin/bash
# Kiosk CM5 Deployment Script

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Flash image to SD card
flash_image() {
    local image_file="$1"
    local device="$2"
    
    if [[ ! -f "$image_file" ]]; then
        log_error "Image file not found: $image_file"
        exit 1
    fi
    
    if [[ ! -b "$device" ]]; then
        log_error "Device not found: $device"
        exit 1
    fi
    
    log_info "Flashing $image_file to $device..."
    log_info "This will erase all data on $device. Continue? (y/N)"
    read -r response
    
    if [[ "$response" != "y" ]] && [[ "$response" != "Y" ]]; then
        log_info "Cancelled by user"
        exit 0
    fi
    
    # Unmount any existing partitions
    umount "${device}"* 2>/dev/null || true
    
    # Flash the image
    dd if="$image_file" of="$device" bs=4M status=progress conv=fsync
    
    log_success "Image flashed successfully"
}

# Main
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <device> [image_file]"
    echo "Example: $0 /dev/sdb"
    echo ""
    echo "Available devices:"
    lsblk -d -o NAME,SIZE,TYPE | grep disk
    exit 1
fi

device="$1"
image_file="${2:-$(ls *.img 2>/dev/null | head -1)}"

if [[ -z "$image_file" ]]; then
    log_error "No image file specified and none found in current directory"
    exit 1
fi

flash_image "$image_file" "$device"
EOF
    
    chmod +x "$deploy_script"
    log_info "Created deployment script: $deploy_script"
}

# Main execution
main() {
    echo "========================================"
    echo "     Kiosk CM5 Image Build Script       "
    echo "========================================"
    echo ""
    
    check_prerequisites
    prepare_environment
    validate_config
    build_image
    post_build
}

# Handle script arguments
case "${1:-build}" in
    "build")
        main
        ;;
    "clean")
        log_info "Cleaning build artifacts..."
        rm -rf work
        log_success "Build artifacts cleaned"
        ;;
    "validate")
        check_prerequisites
        validate_config
        log_success "Validation passed"
        ;;
    *)
        echo "Usage: $0 {build|clean|validate}"
        echo ""
        echo "Commands:"
        echo "  build     - Build the kiosk image (default)"
        echo "  clean     - Clean build artifacts"
        echo "  validate  - Validate configuration only"
        exit 1
        ;;
esac
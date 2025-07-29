#!/bin/bash
# Pack Plymouth themes from themes directory into archives

set -e

# Set paths
THEMES_DIR="themes"
OUTPUT_DIR="output/themes"

echo "📦 Packing Plymouth themes..."

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if themes directory exists
if [ ! -d "$THEMES_DIR" ]; then
    echo "❌ Themes directory not found: $THEMES_DIR"
    exit 1
fi

# Pack each theme directory into a tar.xz archive
theme_count=0
for theme_dir in "$THEMES_DIR"/*; do
    if [ -d "$theme_dir" ]; then
        theme_name=$(basename "$theme_dir")
        archive_name="${theme_name}.tar.xz"
        
        echo "📦 Packing theme: $theme_name"
        
        # Create archive from theme directory
        cd "$THEMES_DIR"
        tar -cJf "../$OUTPUT_DIR/$archive_name" "$theme_name"
        cd - > /dev/null
        
        echo "✅ Created: $OUTPUT_DIR/$archive_name"
        theme_count=$((theme_count + 1))
    fi
done

if [ $theme_count -eq 0 ]; then
    echo "⚠️  No themes found in $THEMES_DIR"
else
    echo "✅ Packed $theme_count themes into $OUTPUT_DIR/"
    echo "📋 Available themes:"
    ls -la "$OUTPUT_DIR/"*.tar.xz 2>/dev/null | awk '{print "   " $9}' || echo "   (none)"
fi
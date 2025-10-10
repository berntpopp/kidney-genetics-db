#!/bin/bash
#
# Favicon Generation Script
# Generates all required favicon sizes from KGDB_logo_with_letters.svg
#
# Requirements:
#   - ImageMagick (convert command)
#   - Source file: frontend/public/KGDB_logo_with_letters.svg
#
# Usage:
#   chmod +x scripts/generate-favicons.sh
#   ./scripts/generate-favicons.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_SVG="$PROJECT_ROOT/public/KGDB_logo_with_letters.svg"
OUTPUT_DIR="$PROJECT_ROOT/public"

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}   KGDB Favicon Generation Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
    echo -e "${RED}✗ Error: ImageMagick is not installed${NC}"
    echo ""
    echo "Please install ImageMagick first:"
    echo "  Ubuntu/Debian: sudo apt-get install imagemagick"
    echo "  macOS: brew install imagemagick"
    echo "  Fedora: sudo dnf install ImageMagick"
    echo ""
    exit 1
fi

# Check if source SVG exists
if [ ! -f "$SOURCE_SVG" ]; then
    echo -e "${RED}✗ Error: Source SVG not found${NC}"
    echo "Expected: $SOURCE_SVG"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo -e "  Source: ${YELLOW}$(basename $SOURCE_SVG)${NC}"
echo -e "  Output: ${YELLOW}$OUTPUT_DIR${NC}"
echo ""

# Function to generate a favicon
generate_favicon() {
    local size=$1
    local filename=$2
    local background=$3

    echo -n "  Generating ${filename}... "

    if [ "$background" = "transparent" ]; then
        convert "$SOURCE_SVG" \
            -resize ${size}x${size} \
            -background none \
            -alpha on \
            "$OUTPUT_DIR/$filename" 2>/dev/null
    else
        convert "$SOURCE_SVG" \
            -resize ${size}x${size} \
            -background "$background" \
            -alpha remove \
            -alpha off \
            "$OUTPUT_DIR/$filename" 2>/dev/null
    fi

    if [ $? -eq 0 ]; then
        local filesize=$(du -h "$OUTPUT_DIR/$filename" | cut -f1)
        echo -e "${GREEN}✓${NC} (${filesize})"
    else
        echo -e "${RED}✗ Failed${NC}"
        return 1
    fi
}

# Generate PNG favicons
echo -e "${BLUE}Generating PNG favicons:${NC}"
generate_favicon 16 "favicon-16x16.png" "transparent"
generate_favicon 32 "favicon-32x32.png" "transparent"
generate_favicon 180 "apple-touch-icon.png" "white"
generate_favicon 192 "icon-192.png" "transparent"
generate_favicon 512 "icon-512.png" "transparent"

# Optional enhanced sizes
echo ""
echo -e "${BLUE}Generating optional enhanced icons:${NC}"
generate_favicon 144 "icon-144.png" "transparent"
generate_favicon 384 "icon-384.png" "transparent"

# Generate ICO favicon (multi-resolution)
echo ""
echo -e "${BLUE}Generating ICO favicon:${NC}"
echo -n "  Generating favicon.ico... "

convert "$SOURCE_SVG" \
    -define icon:auto-resize=32,16 \
    -background none \
    -alpha on \
    "$OUTPUT_DIR/favicon.ico" 2>/dev/null

if [ $? -eq 0 ]; then
    local filesize=$(du -h "$OUTPUT_DIR/favicon.ico" | cut -f1)
    echo -e "${GREEN}✓${NC} (${filesize})"
else
    echo -e "${RED}✗ Failed${NC}"
fi

# Copy and optimize SVG favicon
echo ""
echo -e "${BLUE}Creating SVG favicon:${NC}"
echo -n "  Copying icon.svg... "

cp "$SOURCE_SVG" "$OUTPUT_DIR/icon.svg"

if [ $? -eq 0 ]; then
    local filesize=$(du -h "$OUTPUT_DIR/icon.svg" | cut -f1)
    echo -e "${GREEN}✓${NC} (${filesize})"
else
    echo -e "${RED}✗ Failed${NC}"
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Favicon generation complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo ""
echo "Generated files:"
echo "  ├── favicon.ico              (32×32 + 16×16 multi-res)"
echo "  ├── icon.svg                 (scalable vector)"
echo "  ├── apple-touch-icon.png     (180×180 iOS)"
echo "  ├── icon-192.png             (192×192 PWA minimum)"
echo "  ├── icon-512.png             (512×512 PWA recommended)"
echo "  ├── icon-144.png             (144×144 Windows Metro)"
echo "  └── icon-384.png             (384×384 Android)"
echo ""
echo "Next steps:"
echo "  1. Update index.html with favicon links"
echo "  2. Test favicons in multiple browsers"
echo "  3. Validate PWA manifest"
echo ""

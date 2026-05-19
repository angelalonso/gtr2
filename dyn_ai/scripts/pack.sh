#!/usr/bin/env bash

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Function to display help
show_help() {
    cat << EOF
${SCRIPT_NAME} - Package the Dyn AI build artifacts

USAGE:
    ./${SCRIPT_NAME}
    ./${SCRIPT_NAME} -h|--help

DESCRIPTION:
    This script packages the built executables and required files into zip archives.
    The zip files are named dyn_ai.zip (or dyn_ai.z01, dyn_ai.z02, etc. for split archives).
    Version information is read from VERSION.md if it exists.

EOF
}

# Function to read version from VERSION.md
read_version() {
    local version_file="${SCRIPT_DIR}/../VERSION.md"
    if [ -f "$version_file" ]; then
        local version=$(cat "$version_file" | tr -d '\n\r')
        if [[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "$version"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Try '$SCRIPT_NAME --help' for more information."
            exit 1
            ;;
    esac
done

# Navigate to parent directory (where executables are)
cd "${SCRIPT_DIR}/.."
echo "Working directory: $(pwd)"

# Read version from VERSION.md if it exists
VERSION=$(read_version)
if [ -n "$VERSION" ]; then
    echo "Version from VERSION.md: ${VERSION}"
else
    echo "No VERSION.md found or invalid version format"
fi

# Check if required files exist
echo ""
echo "Checking for required files..."

if [ ! -f "dyn_ai.exe" ]; then
    echo "ERROR: dyn_ai.exe not found in $(pwd)"
    echo "Please run cross_compile_main.sh first"
    exit 1
fi

if [ ! -f "dyn_ai_setup.exe" ]; then
    echo "ERROR: dyn_ai_setup.exe not found in $(pwd)"
    echo "Please run cross_compile_setup.sh first"
    exit 1
fi

if [ ! -f "dyn_ai_visualizer.exe" ]; then
    echo "ERROR: dyn_ai_visualizer.exe not found in $(pwd)"
    echo "Please run cross_compile_visualizer.sh first"
    exit 1
fi

echo "  ✓ Required files found"

# Prepare file list for zipping
ZIP_FILES="dyn_ai.exe dyn_ai_setup.exe dyn_ai_visualizer.exe README.md vehicle_classes.json"

if [ -f "VERSION.md" ]; then
    ZIP_FILES="$ZIP_FILES VERSION.md"
    echo "  ✓ Including VERSION.md"
fi

if [ -f "ai_data.db" ]; then
    ZIP_FILES="$ZIP_FILES ai_data.db"
    echo "  ✓ Including ai_data.db"
else
    echo "  ⚠ ai_data.db not found, skipping"
fi

# Remove old packages
echo ""
echo "Cleaning up old packages..."
rm -f "dyn_ai.zip"
rm -f "dyn_ai.z"*
rm -f "dyn_ai_full.zip"
echo "  ✓ Cleanup complete"

# Create full zip (single file)
echo ""
echo "Creating full archive: dyn_ai_full.zip"
zip -r "dyn_ai_full.zip" $ZIP_FILES
echo "  ✓ Created: dyn_ai_full.zip"

# Create split zip (49MB parts)
echo ""
echo "Creating split archive: dyn_ai.zip (49MB parts)"
zip -s 49m -r "dyn_ai.zip" $ZIP_FILES
echo "  ✓ Created: dyn_ai.zip and parts (dyn_ai.z01, dyn_ai.z02, ...)"

# Summary
echo ""
echo "=========================================="
echo "PACKAGING COMPLETED"
echo "=========================================="
if [ -n "$VERSION" ]; then
    echo "Version: ${VERSION}"
fi
echo "Files created:"
echo "  - dyn_ai_full.zip"
echo "  - dyn_ai.zip (and dyn_ai.z01, dyn_ai.z02, ...)"
echo "=========================================="

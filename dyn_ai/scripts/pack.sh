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
    ./${SCRIPT_NAME} [VERSION]
    ./${SCRIPT_NAME} -h|--help

DESCRIPTION:
    This script packages the built executables and required files into zip archives.
    If a version is provided, it will be used for the package name.
    If no version is provided, it will find the latest version from existing
    dyn_ai_vX.Y.Z.zip files in the parent directory and use that version.

VERSION PARAMETER:
    Must match the pattern vX.Y.Z (where X, Y, Z are digits)

EXAMPLES:
    # Package with auto-detected latest version
    ./${SCRIPT_NAME}
    
    # Package with specific version
    ./${SCRIPT_NAME} v1.2.3

EOF
}

# Function to validate version format
validate_version() {
    [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

# Function to find the latest version from existing zip files
find_latest_version() {
    cd ${SCRIPT_DIR}
    local latest=""
    local highest="0.0.0"
    
    # Look for dyn_ai_vX.Y.Z.zip files in parent directory
    for zipfile in ../dyn_ai_v*.zip; do
        if [ -f "$zipfile" ]; then
            # Extract version pattern vX.Y.Z
            if [[ "$zipfile" =~ v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
                local found="${BASH_REMATCH[0]}"
                local found_num="${found#v}"  # Remove the 'v' prefix
                
                # Compare versions using sort -V (version sort)
                if [ "$(printf '%s\n' "$highest" "$found_num" | sort -V | tail -n1)" = "$found_num" ] && [ "$found_num" != "$highest" ]; then
                    highest="$found_num"
                    latest="$found"
                fi
            fi
        fi
    done
    
    if [ -z "$latest" ]; then
        echo "ERROR: No existing dyn_ai_vX.Y.Z.zip files found in parent directory" >&2
        echo "Please specify a version manually: ./${SCRIPT_NAME} vX.Y.Z" >&2
        exit 1
    fi
    
    echo "$latest"
}

# Parse command line arguments
VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            echo "ERROR: Unknown option: $1"
            echo "Try '$SCRIPT_NAME --help' for more information."
            exit 1
            ;;
        *)
            if validate_version "$1"; then
                VERSION="$1"
                shift
            else
                echo "ERROR: Invalid version format: $1"
                echo "Version must match pattern: vX.Y.Z (e.g., v1.2.3)"
                exit 1
            fi
            ;;
    esac
done

# Navigate to parent directory (where executables are)
cd "${SCRIPT_DIR}/.."
echo "Working directory: $(pwd)"

# Determine the version to use
if [ -z "$VERSION" ]; then
    echo "No version specified, finding latest version from existing zip files..."
    VERSION=$(find_latest_version)
    echo "Using latest version: ${VERSION}"
else
    echo "Using specified version: ${VERSION}"
fi

# Check if required files exist
echo ""
echo "Checking for required files..."

if [ ! -f "dyn_ai.exe" ]; then
    echo "ERROR: dyn_ai.exe not found in $(pwd)"
    echo "Please run cross_compile.sh first"
    exit 1
fi

if [ ! -f "datamgmt_dyn_ai.exe" ]; then
    echo "ERROR: datamgmt_dyn_ai.exe not found in $(pwd)"
    echo "Please run cross_compile_datamgmt.sh first"
    exit 1
fi

echo "  ✓ Required files found"

# Prepare file list for zipping
ZIP_FILES="dyn_ai.exe datamgmt_dyn_ai.exe README.md vehicle_classes.json"
if [ -f "ai_data.db" ]; then
    ZIP_FILES="$ZIP_FILES ai_data.db"
    echo "  ✓ Including ai_data.db"
else
    echo "  ⚠ ai_data.db not found, skipping"
fi

# Remove old packages with this version
echo ""
echo "Cleaning up old packages for version ${VERSION}..."
rm -f "dyn_ai_${VERSION}_full.zip"
rm -f "dyn_ai_${VERSION}.z"*
echo "  ✓ Cleanup complete"

# Create full zip
echo ""
echo "Creating full archive: dyn_ai_${VERSION}_full.zip"
zip -r "dyn_ai_${VERSION}_full.zip" $ZIP_FILES
echo "  ✓ Created: dyn_ai_${VERSION}_full.zip"

# Create split zip (49MB parts)
echo ""
echo "Creating split archive: dyn_ai_${VERSION}.zip (49MB parts)"
zip -s 49m -r "dyn_ai_${VERSION}.zip" $ZIP_FILES
echo "  ✓ Created: dyn_ai_${VERSION}.zip and parts"

# Summary
echo ""
echo "=========================================="
echo "PACKAGING COMPLETED"
echo "=========================================="
echo "Version: ${VERSION}"
echo "Files created:"
echo "  - dyn_ai_${VERSION}_full.zip"
echo "  - dyn_ai_${VERSION}.zip (and .z01, .z02, ...)"
echo "=========================================="

#!/bin/bash

set -e  # Exit on error

COMPILEDIR="$HOME/.wine/drive_c/file_logger"
CWD=$(pwd)

echo "=== Starting build process ==="

# Clean up previous builds
echo "Cleaning previous builds..."
rm -rf ${COMPILEDIR}/build ${COMPILEDIR}/dist
rm -f ${COMPILEDIR}/file_logger.py ${COMPILEDIR}/cfg.yml

# Create compile directory if it doesn't exist
mkdir -p ${COMPILEDIR}

# Copy files
echo "Copying files to ${COMPILEDIR}..."
cp file_logger.py ${COMPILEDIR}/
if [ -f "cfg.yml" ]; then
    cp cfg.yml ${COMPILEDIR}/
    echo "Copied cfg.yml"
fi

cd ${COMPILEDIR}

# Upgrade pip and install dependencies
echo "Installing/upgrading dependencies..."
wine python -m pip install --upgrade pip setuptools wheel
wine python -m pip install watchdog pyyaml PyInstaller

# Verify installations
echo "Verifying installations..."
if ! wine python -c "import watchdog" 2>/dev/null; then
    echo "ERROR: watchdog not installed correctly"
    exit 1
fi
echo "✓ watchdog installed"

if ! wine python -c "import yaml" 2>/dev/null; then
    echo "ERROR: pyyaml not installed correctly"
    exit 1
fi
echo "✓ pyyaml installed"

# Get package paths for debugging
echo "Package locations:"
wine python -c "import watchdog; print(f'  watchdog: {watchdog.__file__}')"
wine python -c "import yaml; print(f'  yaml: {yaml.__file__}')"

# Build the executable
echo "Building executable with PyInstaller..."
wine python -m PyInstaller \
    --onefile \
    --windowed \
    --name=file_logger \
    --hidden-import=watchdog \
    --hidden-import=watchdog.observers \
    --hidden-import=watchdog.events \
    --hidden-import=yaml \
    --hidden-import=_yaml \
    --collect-all=watchdog \
    --collect-all=yaml \
    --log-level=INFO \
    file_logger.py

# Check if build succeeded
if [ -f "dist/file_logger.exe" ]; then
    echo "Build successful!"
    
    # Get file size for verification
    SIZE=$(wc -c < "dist/file_logger.exe")
    echo "Executable size: $SIZE bytes"
    
    # Copy back to original directory
    cp dist/file_logger.exe ${CWD}/
    echo "Copied executable to ${CWD}/file_logger.exe"
    
    # Optional: Test the executable (might fail if no config)
    echo "Testing executable (may fail if no cfg.yml present)..."
    wine file_logger.exe --help 2>&1 || echo "Test completed with warnings"
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build process completed ==="
cp dist/file_logger.exe .
wine file_logger.exe
cd ${CWD}
cp ${COMPILEDIR}/dist/file_logger.exe .

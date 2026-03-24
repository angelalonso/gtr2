#!/bin/bash

set -e  # Exit on error

COMPILEDIR="$HOME/.wine/drive_c/live_ai_tuner"
CWD=$(pwd)

echo "=== Starting build process ==="

# Clean up previous builds
echo "Cleaning previous builds..."
rm -rf ${COMPILEDIR}/build ${COMPILEDIR}/dist
rm -f ${COMPILEDIR}/live_ai_tuner.py ${COMPILEDIR}/cfg.yml

# Create compile directory if it doesn't exist
mkdir -p ${COMPILEDIR}

# Copy files
echo "Copying files to ${COMPILEDIR}..."
cp *.py ${COMPILEDIR}/
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
    --name=live_ai_tuner \
    --hidden-import=watchdog \
    --hidden-import=watchdog.observers \
    --hidden-import=watchdog.events \
    --hidden-import=yaml \
    --hidden-import=_yaml \
    --hidden-import=race_results_parser \
    --collect-all=watchdog \
    --collect-all=yaml \
    --add-data="race_results_parser.py;." \
    --log-level=INFO \
    live_ai_tuner.py

# Check if build succeeded
if [ -f "dist/live_ai_tuner.exe" ]; then
    echo "Build successful!"
    
    # Get file size for verification
    SIZE=$(wc -c < "dist/live_ai_tuner.exe")
    echo "Executable size: $SIZE bytes"
    
    # Copy back to original directory
    cp dist/live_ai_tuner.exe ${CWD}/
    echo "Copied executable to ${CWD}/live_ai_tuner.exe"
    
    # Optional: Test the executable (might fail if no config)
    echo "Testing executable (may fail if no cfg.yml present)..."
    wine live_ai_tuner.exe --help 2>&1 || echo "Test completed with warnings"
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build process completed ==="
cp dist/live_ai_tuner.exe .
wine live_ai_tuner.exe
cd ${CWD}
cp ${COMPILEDIR}/dist/live_ai_tuner.exe .

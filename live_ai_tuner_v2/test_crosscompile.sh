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

# Copy all Python files
echo "Copying files to ${COMPILEDIR}..."
# List all Python files to copy
PYTHON_FILES=(
    "main.py"
    "gui.py"
    "cfg_manage.py"
    "file_monitor.py"
    "results_parser.py"
    "global_curve.py"
    "aiw_manager.py"
    "ratio_calculator.py"
)

for file in "${PYTHON_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" ${COMPILEDIR}/
        echo "  Copied $file"
    else
        echo "  WARNING: $file not found"
    fi
done

# Create a main entry point file if it doesn't exist as live_ai_tuner.py
# (PyInstaller expects the main file)
if [ ! -f "${COMPILEDIR}/live_ai_tuner.py" ]; then
    echo "Creating live_ai_tuner.py as entry point..."
    # Create a symlink or copy main.py to live_ai_tuner.py
    cp ${COMPILEDIR}/main.py ${COMPILEDIR}/live_ai_tuner.py
    echo "  Created live_ai_tuner.py from main.py"
fi

# Copy cfg.yml if it exists
if [ -f "cfg.yml" ]; then
    cp cfg.yml ${COMPILEDIR}/
    echo "  Copied cfg.yml"
else
    echo "  No cfg.yml found, will create default on first run"
fi

cd ${COMPILEDIR}

# Upgrade pip and install dependencies
echo "Installing/upgrading dependencies..."
wine python -m pip install --upgrade pip setuptools wheel
wine python -m pip install watchdog pyyaml PyQt5 numpy scipy matplotlib

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

if ! wine python -c "import PyQt5" 2>/dev/null; then
    echo "ERROR: PyQt5 not installed correctly"
    exit 1
fi
echo "✓ PyQt5 installed"

if ! wine python -c "import numpy" 2>/dev/null; then
    echo "ERROR: numpy not installed correctly"
    exit 1
fi
echo "✓ numpy installed"

if ! wine python -c "import scipy" 2>/dev/null; then
    echo "ERROR: scipy not installed correctly"
    exit 1
fi
echo "✓ scipy installed"

# Get package paths for debugging
echo "Package locations:"
wine python -c "import watchdog; print(f'  watchdog: {watchdog.__file__}')"
wine python -c "import yaml; print(f'  yaml: {yaml.__file__}')"
wine python -c "import PyQt5; print(f'  PyQt5: {PyQt5.__file__}')"
wine python -c "import numpy; print(f'  numpy: {numpy.__file__}')"
wine python -c "import scipy; print(f'  scipy: {scipy.__file__}')"

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
    --hidden-import=PyQt5 \
    --hidden-import=PyQt5.QtCore \
    --hidden-import=PyQt5.QtWidgets \
    --hidden-import=PyQt5.QtGui \
    --hidden-import=numpy \
    --hidden-import=numpy.core._methods \
    --hidden-import=numpy.lib.format \
    --hidden-import=scipy \
    --hidden-import=scipy.optimize \
    --hidden-import=scipy.optimize._minimize \
    --hidden-import=scipy.special \
    --hidden-import=scipy.integrate \
    --hidden-import=scipy.linalg \
    --hidden-import=matplotlib \
    --hidden-import=matplotlib.backends \
    --hidden-import=matplotlib.backends.backend_qt5agg \
    --hidden-import=matplotlib.figure \
    --hidden-import=matplotlib.pyplot \
    --hidden-import=cfg_manage \
    --hidden-import=file_monitor \
    --hidden-import=results_parser \
    --hidden-import=global_curve \
    --hidden-import=aiw_manager \
    --hidden-import=ratio_calculator \
    --hidden-import=gui \
    --collect-all=watchdog \
    --collect-all=yaml \
    --collect-all=PyQt5 \
    --collect-all=numpy \
    --collect-all=scipy \
    --collect-all=matplotlib \
    --add-data="cfg_manage.py;." \
    --add-data="file_monitor.py;." \
    --add-data="results_parser.py;." \
    --add-data="global_curve.py;." \
    --add-data="aiw_manager.py;." \
    --add-data="ratio_calculator.py;." \
    --add-data="gui.py;." \
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

# Optional: Run the executable (uncomment if you want to run after build)
# echo "Running executable..."
# cd ${CWD}
# wine live_ai_tuner.exe

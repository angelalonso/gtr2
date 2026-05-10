#!/bin/bash

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Navigate to the parent directory (where the project files are)
cd "${SCRIPT_DIR}/.."

COMPILEDIR="$HOME/.wine/drive_c/datamgmt_dyn_ai"
CWD=$(pwd)

echo "=== Building Dyn AI Data Manager ==="
echo "Working directory: ${CWD}"

# Clean and create build directory
rm -rf ${COMPILEDIR}
mkdir -p ${COMPILEDIR}

# Copy all required files
echo "Copying files to ${COMPILEDIR}..."
cp -R ./* ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies
echo "Installing dependencies..."
wine python -m pip install --upgrade pip
wine python -m pip install PyQt5 pyyaml numpy pandas

# Build with PyInstaller
echo "Building executable with PyInstaller..."
wine python -m PyInstaller \
    --onefile \
    --windowed \
    --name="datamgmt_dyn_ai" \
    --add-data="gui_data_manager.py;." \
    --add-data="gui_common.py;." \
    --add-data="gui_vehicle_manager.py;." \
    --add-data="gui_common_dialogs.py;." \
    --add-data="gui_data_manager_common.py;." \
    --add-data="core_database.py;." \
    --add-data="core_config.py;." \
    --add-data="core_vehicle_scanner.py;." \
    --add-data="cfg_funcs.py;." \
    --hidden-import=gui_data_manager \
    --hidden-import=gui_data_manager_common \
    --hidden-import=gui_common \
    --hidden-import=gui_vehicle_manager \
    --hidden-import=gui_common_dialogs \
    --hidden-import=core_database \
    --hidden-import=core_config \
    --hidden-import=core_vehicle_scanner \
    --hidden-import=cfg_funcs \
    --hidden-import=PyQt5.QtCore \
    --hidden-import=PyQt5.QtWidgets \
    --hidden-import=PyQt5.QtGui \
    dyn_ai_data_manager.py

# Copy result
if [ -f "dist/datamgmt_dyn_ai.exe" ]; then
    cp dist/datamgmt_dyn_ai.exe ${CWD}/
    echo "Success! Executable: ${CWD}/datamgmt_dyn_ai.exe"
    
    # Copy required data files alongside the exe
    cp vehicle_classes.json ${CWD}/ 2>/dev/null || true
    cp cfg.yml ${CWD}/ 2>/dev/null || true
    
    echo ""
    echo "Note: Make sure vehicle_classes.json and cfg.yml are in the same folder as datamgmt_dyn_ai.exe"
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build completed ==="

# Return to original directory (optional)
cd "${SCRIPT_DIR}"

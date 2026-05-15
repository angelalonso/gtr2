#!/bin/bash

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Navigate to the parent directory (where the project files are)
cd "${SCRIPT_DIR}/.."

COMPILEDIR="$HOME/.wine/drive_c/dyn_ai_visualizer"
CWD=$(pwd)

echo "=== Starting build process ==="
echo "Working directory: ${CWD}"

# Clean up previous builds
rm -rf ${COMPILEDIR}
mkdir -p ${COMPILEDIR}

# Copy ALL files from current directory
echo "Copying files to ${COMPILEDIR}..."

cp dyn_ai_visualizer.py ${COMPILEDIR}/
cp core_aiw_utils.py ${COMPILEDIR}/
cp core_autopilot.py ${COMPILEDIR}/
cp core_config.py ${COMPILEDIR}/
cp core_database.py ${COMPILEDIR}/
cp core_data_extraction.py ${COMPILEDIR}/
cp core_formula.py ${COMPILEDIR}/
cp core_user_laptimes.py ${COMPILEDIR}/
cp gui_common.py ${COMPILEDIR}/
cp gui_common_dialogs.py ${COMPILEDIR}/
cp gui_curve_graph.py ${COMPILEDIR}/
cp gui_session_panel.py ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies (including PyInstaller)
echo "Installing dependencies..."
## wine python -m pip install --upgrade pip
## wine python -m pip install watchdog pyyaml numpy scipy matplotlib PyQt5 pyinstaller

# Build with PyInstaller - using --add-data for all required files
echo "Building executable with PyInstaller..."

wine python -m PyInstaller \
    --upx-dir /usr/bin/ \
    --onefile \
    --windowed \
    --exclude-module PIL \
    --exclude-module contourpy \
    --exclude-module cycler \
    --exclude-module fonttools \
    --exclude-module kiwisolver \
    --exclude-module matplotlib \
    --exclude-module pandas \
    --exclude-module pyparsing \
    --exclude-module scipy \
    --exclude-module tkinter \
    --exclude-module watchdog \
    --name="dyn_ai_visualizer" \
    --hidden-import=cfg_funcs \
    --hidden-import=core_aiw_utils \
    --hidden-import=core_autopilot \
    --hidden-import=core_config \
    --hidden-import=core_database \
    --hidden-import=core_data_extracion \
    --hidden-import=core_formula \
    --hidden-import=core_user_laptimes \
    --hidden-import=gui_common \
    --hidden-import=gui_common_dialogs \
    --hidden-import=gui_curve_graph \
    --hidden-import=gui_session_panel \
    dyn_ai_visualizer.py

# Check if build succeeded
if [ -f "dist/dyn_ai_visualizer.exe" ]; then
    echo "Build successful!"
    
    # Copy back to original directory (parent of script directory)
    cp dist/dyn_ai_visualizer.exe ${CWD}/
    echo "Copied executable to ${CWD}/dyn_ai_visualizer.exe"
    
    # Also copy required data files to be alongside the exe
    cp cfg.yml ${CWD}/ 2>/dev/null || true
    cp vehicle_classes.json ${CWD}/ 2>/dev/null || true
    
    echo "Build completed! Make sure cfg.yml and vehicle_classes.json are in the same folder as dyn_ai_visualizer.exe"
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build process completed ==="

# Return to original directory (optional)
cd "${SCRIPT_DIR}"


#!/bin/bash

set -e  # Exit on error

COMPILEDIR="$HOME/.wine/drive_c/dyn_ai"
CWD=$(pwd)

echo "=== Starting build process ==="

# Clean up previous builds
rm -rf ${COMPILEDIR}
mkdir -p ${COMPILEDIR}

# Copy ALL files from current directory
echo "Copying files to ${COMPILEDIR}..."
cp -R ./* ${COMPILEDIR}/

cd ${COMPILEDIR}

# Install dependencies
echo "Installing dependencies..."
wine python -m pip install --upgrade pip
wine python -m pip install watchdog pyyaml numpy scipy matplotlib PyQt5

# Build with PyInstaller, explicitly adding all Python files
echo "Building executable with PyInstaller..."
wine python -m PyInstaller \
    --onefile \
    --windowed \
    --add-data="ai_target_analyzer.py;." \
    --add-data="aiw_utils.py;." \
    --add-data="autopilot.py;." \
    --add-data="cfg_funcs.py;." \
    --add-data="data_daemon.py;." \
    --add-data="data_extraction.py;." \
    --add-data="db_funcs.py;." \
    --add-data="dialogs_base_path.py;." \
    --add-data="dialogs_info_message.py;." \
    --add-data="formula_funcs.py;." \
    --add-data="gui_funcs.py;." \
    --add-data="main_window.py;." \
    --add-data="pre_run_check.py;." \
    --add-data="dyn_ai.py;." \
    --hidden-import=ai_target_analyzer \
    --hidden-import=aiw_utils \
    --hidden-import=autopilot \
    --hidden-import=cfg_funcs \
    --hidden-import=data_daemon \
    --hidden-import=data_extraction \
    --hidden-import=db_funcs \
    --hidden-import=dialogs_base_path \
    --hidden-import=dialogs_info_message \
    --hidden-import=formula_funcs \
    --hidden-import=gui_funcs \
    --hidden-import=main_window \
    --hidden-import=pre_run_check \
    dyn_ai.py

# Check if build succeeded
if [ -f "dist/dyn_ai.exe" ]; then
    echo "Build successful!"
    
    # Copy back to original directory
    cp dist/dyn_ai.exe ${CWD}/
    echo "Copied executable to ${CWD}/dyn_ai.exe"
    
    # Optional: Test the executable
    echo "Testing executable..."
    cd ${CWD}
    wine dyn_ai.exe --config=./cfg.yml | head -5 || echo "Test completed"
    
else
    echo "ERROR: Build failed - executable not created"
    exit 1
fi

echo "=== Build process completed ==="

COMPILEDIR="$HOME/.wine/drive_c/dyn_ai"
rm -rf ${COMPILEDIR}/build ${COMPILEDIR}/dist
rm ${COMPILEDIR}/*.py ${COMPILEDIR}/dyn_ai.spec 
rm ${COMPILEDIR}/Pipfile ${COMPILEDIR}/Pipfile.lock
CWD=$(pwd)
cp -R ./* ${COMPILEDIR}
cd ${COMPILEDIR}
wine python -m PyInstaller --onefile --windowed dyn_ai.py
cp dist/dyn_ai.exe .
wine dyn_ai.exe
cd ${CWD}
cp ${COMPILEDIR}/dist/dyn_ai.exe .

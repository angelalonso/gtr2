COMPILEDIR="$HOME/.wine/drive_c/tyr_editor"
rm -rf ${COMPILEDIR}/build ${COMPILEDIR}/dist
rm ${COMPILEDIR}/tyr_editor.py ${COMPILEDIR}/tyr_editor.spec 
rm ${COMPILEDIR}/Pipfile ${COMPILEDIR}/Pipfile.lock
CWD=$(pwd)
cp -R ./* ${COMPILEDIR}
cd ${COMPILEDIR}
wine python -m PyInstaller --onefile --windowed tyr_editor.py
cp dist/tyr_editor.exe .
wine tyr_editor.exe files/Yokohama_Elise.tyr
cd ${CWD}
cp ${COMPILEDIR}/dist/tyr_editor.exe .

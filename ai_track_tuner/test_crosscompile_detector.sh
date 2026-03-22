COMPILEDIR="$HOME/.wine/drive_c/ai_track_tuner"
rm -rf ${COMPILEDIR}/build ${COMPILEDIR}/dist
rm ${COMPILEDIR}/detector.py ${COMPILEDIR}/detector.spec 
rm ${COMPILEDIR}/Pipfile ${COMPILEDIR}/Pipfile.lock
CWD=$(pwd)
cp -R ./* ${COMPILEDIR}
cd ${COMPILEDIR}
wine python -m PyInstaller --onefile --windowed detector.py
cp dist/detector.exe .
wine detector.exe
cd ${CWD}
cp ${COMPILEDIR}/dist/detector.exe .

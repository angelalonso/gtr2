COMPILEDIR="$HOME/.wine/drive_c/ai_track_tuner"
rm -rf ${COMPILEDIR}/build ${COMPILEDIR}/dist
rm ${COMPILEDIR}/ai_track_tuner.py ${COMPILEDIR}/ai_track_tuner.spec 
rm ${COMPILEDIR}/Pipfile ${COMPILEDIR}/Pipfile.lock
CWD=$(pwd)
cp -R ./* ${COMPILEDIR}
cd ${COMPILEDIR}
wine python -m PyInstaller --onefile --windowed ai_track_tuner.py
cp dist/ai_track_tuner.exe .
wine ai_track_tuner.exe
cd ${CWD}
cp ${COMPILEDIR}/dist/ai_track_tuner.exe .

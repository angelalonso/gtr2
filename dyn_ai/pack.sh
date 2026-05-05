OLDVERSION="v1.0.6"
NEWVERSION="v1.0.7"
rm -f dyn_ai_${OLDVERSION}_full.zip && zip -r dyn_ai_${NEWVERSION}_full.zip dyn_ai.exe ai_data.db README.md datamgmt_dyn_ai.exe vehicle_classes.json
rm -f dyn_ai_${OLDVERSION}.z* && zip -s 49m -r dyn_ai_${NEWVERSION}.zip dyn_ai.exe ai_data.db README.md datamgmt_dyn_ai.exe vehicle_classes.json

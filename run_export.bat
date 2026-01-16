@echo off
echo Starting script... > script_output.txt
python get_full_firestore_data.py >> script_output.txt 2>&1
echo Finished script. >> script_output.txt

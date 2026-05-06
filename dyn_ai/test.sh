#!/usr/bin/env bash

pipenv run python3 test_run_all.py
echo "PRESS ENTER TO CONTINUE"
read continue
pipenv run python3 test_races_simulation.py

# GTR2 TYR Editor

This is an editor for TYR files in GTR2

# Requirements
I usually run it with pipenv:  

pipenv install; pipenv run pip install PyQt5 pyqtgraph scipy numpy

# RUN

pipenv run python3 tyr_editor.py <path to .tyr file>

# Features
- Modify one of the slip curves in the file graphically, point by point
- Compare slip curves with those from other files (or other slip curves from the same file)
- Modify compounds
- Compare them with those from other files (or other compounds within the same file)



# WISHLIST
- selecting two entries would allow us to proportionally modify a value at our file. 
  - example: we select SpringBase and SpringkPa, with these values:

  ours     | comparison
  70000.0  | 50000.0
    925.00 |   700.00

  , then we will be allowed to make either our SpringBase 66071 or our SpringkPa 980.00 automatically (proportional to the relation of 50000.0 to 700.00)
  - this should be useful for variables that are way off and other quick changes

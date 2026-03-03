# What is this?

A "telemetry overlay" for Motec data. 

Basically you take your Motec file and this shows an overlay of speed, RPM, throttle/brake, steering angle...

# what is this good for?

This comes in handy to compare your runs in GTR2 with others. The main use case is to have this open while you check an onboard video on youtube.

To me, this is needed to match (as much as possible) a mod to how a given car behaves in reality on a given track.

Obviously the track should also be very precisely built, but hopefully this tool helps you get as close to real as possible.

# How to use

(temporary solution, see ISSUES below) Get to motec and export your file as CSV.

pipenv install; pipenv run pip install 
pipenv run python3 motec_viewer.py <path to motec file>

, then you can adapt the speed at which the data is shown, play it or move the silder to the point in time you want.

# ISSUES

I did not manage to make this work with autosaved Motec data yet.

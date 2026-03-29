//Elise Suspension file
//////////////////////////////////////////////////////////////////////////
//
// Conventions:
//
// +x = left
// +z = rear
// +y = up
// +pitch = nose up
// +yaw = nose right
// +roll = right
//
// [BODY]  - a rigid mass with mass and inertial properties
// [JOINT] - a ball joint constraining an offset of one body to an
//           offset of another body (eliminates 3 DOF)
// [HINGE] - a constraint restricting the relative rotations of two
//           bodies to be around a single axis (eliminates 2 DOF).
// [BAR]   - a constraint holding an offset of one body from an offset of
//           another body at a fixed distance (eliminates 1 DOF).
// [JOINT&HINGE] - both the joint and hinge constraints, forming the
//           conventional definition of a hinge (eliminates 5 DOF).
//
//////////////////////////////////////////////////////////////////////////

// Body including all rigidly attached parts (wings, barge boards, etc.)
[BODY]
name=body mass=(0.0) inertia=(0.0,0.0,0.0)
pos=(0.0,0.0,0.0) ori=(0.0,0.0,0.0)

// Front spindles
[BODY]
name=fl_spindle mass=(12.0) inertia=(0.0275,0.0260,0.0245)
pos=(0.72,0.0,-1.65) ori=(0.0,0.0,0.0)

[BODY]
name=fr_spindle mass=(12.0) inertia=(0.0275,0.0260,0.0245)
pos=(-0.72,0.0,-1.65) ori=(0.0,0.0,0.0)

// Front wheels
[BODY]
name=fl_wheel mass=(18.0) inertia=(1.292,0.724,0.724)
pos=(0.72,0.0,-1.65) ori=(0.0,0.0,0.0)

[BODY]
name=fr_wheel mass=(18.0) inertia=(1.292,0.724,0.724)
pos=(-0.72,0.0,-1.65) ori=(0.0,0.0,0.0)

// Rear spindles
[BODY]
name=rl_spindle mass=(15.0) inertia=(0.0275,0.0260,0.0245)
pos=(0.68,0.0,1.35) ori=(0.0,0.0,0.0)

[BODY]
name=rr_spindle mass=(15.0) inertia=(0.0275,0.0260,0.0245)
pos=(-0.68,0.0,1.35) ori=(0.0,0.0,0.0)

// Rear wheels (includes half of rear-axle)
[BODY]
name=rl_wheel mass=(21.0) inertia=(1.446,0.875,0.875)
pos=(0.74,0.0,1.35) ori=(0.0,0.0,0.0)

[BODY]
name=rr_wheel mass=(21.0) inertia=(1.446,0.875,0.875)
pos=(-0.74,0.0,1.35) ori=(0.0,0.0,0.0)

 Fuel in tank is not rigidly attached - it is attached with springs and
// dampers to simulate movement.  Properties are defined in the HDV file.

[BODY]
name=fuel_tank mass=(1.0) inertia=(1.0,1.0,1.0)
pos=(0.0,0.0,0.0) ori=(0.0,0.0,0.0)

// Driver's head is not rigidly attached, and it does NOT affect the vehicle
// physics.  Position is from the eyepoint defined in the VEH file, while
// other properties are defined in the head physics file.

[BODY]
name=driver_head mass=(5.0) inertia=(0.02,0.02,0.02)
pos=(0.0,0.0,0.0) ori=(0.0,0.0,0.0)


//////////////////////////////////////////////////////////////////////////
//
// Constraints
//
//////////////////////////////////////////////////////////////////////////

// Front wheel and spindle connections
[JOINT&HINGE]
posbody=fl_wheel negbody=fl_spindle pos=fl_wheel axis=(-0.75,0.0,0.0)

[JOINT&HINGE]
posbody=fr_wheel negbody=fr_spindle pos=fr_wheel axis=(0.75,0.0,0.0)

// Front left suspension (2 A-arms + 1 steering arm = 5 links)
[BAR] // forward upper arm
name=fl_fore_upper posbody=body negbody=fl_spindle pos=(0.437,0.115,-1.65) neg=(0.662,0.140,-1.635)

[BAR] // rearward upper arm
posbody=body negbody=fl_spindle pos=(0.437,0.115,-1.45) neg=(0.662,0.140,-1.635)

[BAR] // forward lower arm
posbody=body negbody=fl_spindle pos=(0.222,-0.140,-1.65) neg=(0.672,-0.140,-1.65)

[BAR] // rearward lower arm
name=fl_fore_lower posbody=body negbody=fl_spindle pos=(0.222,-0.140,-1.40) neg=(0.672,-0.140,-1.65)

[BAR] // steering arm (must be named for identification)
name=fl_steering posbody=body negbody=fl_spindle pos=(0.330,-0.020,-1.802) neg=(0.660,0.0,-1.802)

// Front right suspension (2 A-arms + 1 steering arm = 5 links)
[BAR] // forward upper arm (used in steering lock calculation)
name=fr_fore_upper posbody=body negbody=fr_spindle pos=(-0.437,0.115,-1.65) neg=(-0.662,0.140,-1.635)

[BAR] // rearward upper arm
posbody=body negbody=fr_spindle pos=(-0.437,0.115,-1.45) neg=(-0.662,0.140,-1.635)

[BAR] // forward lower arm
name=fr_fore_lower posbody=body negbody=fr_spindle pos=(-0.222,-0.140,-1.65) neg=(-0.672,-0.140,-1.65)

[BAR] // rearward lower arm
posbody=body negbody=fr_spindle pos=(-0.222,-0.140,-1.40) neg=(-0.672,-0.113,-1.65)

[BAR] // steering arm (must be named for identification)
name=fr_steering posbody=body negbody=fr_spindle pos=(-0.330,-0.020,-1.802) neg=(-0.660,0.0,-1.802)

// Rear left suspension (2 A-arms + 1 straight link = 5 links)
[BAR] // forward upper arm
posbody=body negbody=rl_spindle pos=(0.500,0.115,1.05) neg=(0.660,0.140,1.35)

[BAR] // rearward upper arm
posbody=body negbody=rl_spindle pos=(0.500,0.115,1.40) neg=(0.660,0.140,1.35)

[BAR] // forward lower arm
posbody=body negbody=rl_spindle pos=(0.270,-0.140,1.05) neg=(0.660,-0.140,1.35)

[BAR] // rearward lower arm
posbody=body negbody=rl_spindle pos=(0.270,-0.140,1.40) neg=(0.660,-0.140,1.35)

[BAR] // straight link
posbody=body negbody=rl_spindle pos=(0.350,-0.02,1.52) neg=(0.660,0.00,1.52)

// Rear right suspension (2 A-arms + 1 straight link = 5 links)
[BAR] // forward upper arm
posbody=body negbody=rr_spindle pos=(-0.500,0.115,1.05) neg=(-0.660,0.140,1.35)

[BAR] // rearward upper arm
posbody=body negbody=rr_spindle pos=(-0.500,0.115,1.40) neg=(-0.660,0.140,1.35)

[BAR] // forward lower arm
posbody=body negbody=rr_spindle pos=(-0.270,-0.140,1.05) neg=(-0.660,-0.140,1.35)

[BAR] // rearward lower arm
posbody=body negbody=rr_spindle pos=(-0.270,-0.140,1.40) neg=(-0.660,-0.140,1.35)

[BAR] // straight link
posbody=body negbody=rr_spindle pos=(-0.350,-0.02,1.52) neg=(-0.660,0.00,1.52)

// Rear spindle and wheel connections
[JOINT&HINGE]
posbody=rl_wheel negbody=rl_spindle pos=rl_wheel axis=(-0.75,0.0,0.0)

[JOINT&HINGE]
posbody=rr_wheel negbody=rr_spindle pos=rr_wheel axis=(0.75,0.0,0.0)




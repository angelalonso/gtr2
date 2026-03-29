4Zhuhai
{
  AI Vehicle Filter = Zhuhai

  TestDayDay = Wednesday
  TestDayStart = 7:00
  Practice1Day = Friday
  Practice1Start = 10:00
  Practice2Day = Friday
  Practice2Start = 16:00
  Qualify1Day = Saturday
  Qualify1Start = 9:00
  Qualify2Day = Saturday
  Qualify2Start = 16:00
  WarmupDay = Sunday
  WarmupStart = 9:10
  RaceDay = Sunday
  RaceStart = 11:30
  RaceLaps = 118
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15

  TrackName = Zhuhai, FIA GT Championship Round 11
  GrandPrixName = Zhuhai, 2004
  EventName = Round 11: Zhuhai
  VenueName = Zhuhai GP, 2004
  Location = China, Zhuhai
  Length = 2.651 m./4.266 km.
  Track Record = Matteo Bobbi, 1:31.121, #001 Ferrari 550 Maranello

  SettingsFolder = Zhuhai
  SettingsCopy = Zhuhai.svm
  SettingsAI = Zhuhai.svm
  Qualify Laptime = 89.000
  Race Laptime = 91.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.02
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 1.00
  
// Locality
  Region = South
  Average rain = 0.5
  RainLightScale = 0.75
  RainFogScale = 0.15
  RainFogColourScale = 0.15
  RainCloudScale = 1.0

  // Scene Lighting
  ShadowMinSunAngle=20.0

  SunriseAmbientColour = (165,185,195)
  SunriseDirectionalColour = (120,110,105)
  SunriseFogColour = (50,55,80)
  SunriseFogIn = 0.0
  SunriseFogOut = 2350.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -50.0
  RainSunriseFogOut = 2450.0

  DayAmbientColour = (210,235,215)
  DayDirectionalColour = (235,255,240)
  DayFogColour = (150,175,165)
  DayFogIn = 20.0
  DayFogOut = 2450.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (232,248,238)
  RainDayFogIn = -50.0
  RainDayFogOut = 2450.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (61,63,80)
  SunsetFogIn = 100.0
  SunsetFogOut = 2300.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -50.0
  RainSunsetFogOut = 2450.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 120.0
  NightFogOut = 1200.0
  RainNightAmbientColour = (25,25,25)
  RainNightDirectionalColour = (15,15,15)
  RainNightFogColour = (23,25,24)
  RainNighttFogIn = -100.0
  RainNightFogOut = 2450.0

  // Sun position
  // Latitude affects day/night length, used with date.
  // Latitude also controls the sun/moon vector across the sky
  // NorthDir controls where sun rises/sets
  // RaceDate affects length of day/night, used with latitude

  Latitude = 25 // in degrees, -90 ... +90 (def. 0)
  NorthDir = 270 // in degrees (def. 245)
  RaceDate = August 30 // (def. July 1)

  HorizonRadius = 706.18
  HorizonMaxHeight = 133
  HorizonMinHeight = 67


// Pitstop locations in order from front to back ... if these need to be
// reversed on an individual track, set "ReversePitOrder=1" in the
// track-specific GDB file.
// These are now "pit group" names, not necessarily team names.
// In the VEH file, the pit group defaults to the team name but
// can be overridden by defining "PitGroup=<name>".

Max Vehicles = 42 


// Pitstop locations in order from front to back ... if these need to be
// reversed on an individual track, set "ReversePitOrder=1" in the
// track-specific GDB file.

 PitOrder
 {
  PitGroup=BMS
  PitGroup=Vit_Kon
  PitGroup=RML
  PitGroup=JMB575
  PitGroup=GPC
  PitGroup=AFC
  PitGroup=DAMS
  PitGroup=Freisinger04
  PitGroup=GPC360
  PitGroup=Proton
 }

 // Number of vehicles sharing each pitstall.  The number of entries
 // here must match the number of entries in the PitOrder above.

 NumberSharingPit
 {
  Vehicles=2 // BMS
  Vehicles=2 // Vit_Kon
  Vehicles=2 // RML
  Vehicles=2 // JMB575
  Vehicles=2 // GPC (575)
  Vehicles=2 // AFC
  Vehicles=2 // DAMS
  Vehicles=2 // Freisinger04
  Vehicles=2 // GPC360
  Vehicles=2 // Proton
 } 
} 

4Magny
{
  AI Vehicle Filter = Magny

  TestDayDay = Wednesday
  TestDayStart = 9:00
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
  RaceLaps = 114
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15

  TrackName = Magny-Cours, 2004 FIA GT Championship Round 3
  GrandPrixName = Magny-Cours, 2004
  EventName = Round 3: MAGNY-COURS
  VenueName = Magny-Cours GP, 2004
  Location = France, Magny-Cours
  Length = 2.741 mi/4.411 km
  Track Record = Walter Lechner Jr, 1:36.174, #004 Saleen S7-R

  SettingsFolder = Magny-Cours
  SettingsCopy = Magny-Cours.svm
  SettingsAI = Magny-Cours.svm
  Qualify Laptime = 93.000
  Race Laptime = 95.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.00
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 1.00

  Pit Board Location = Left

// Locality
  Region = Central
  Average rain = 0.3
  RainLightScale = 0.85
  RainFogScale = 0.95
  RainFogColourScale = 0.15
  RainCloudScale = 1.0

  // Scene Lighting
  ShadowMinSunAngle=20.0

  SunriseAmbientColour = (165,185,195)
  SunriseDirectionalColour = (120,110,105)
  SunriseFogColour = (30,35,60)
  SunriseFogIn = 0.0
  SunriseFogOut = 1450.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45) 
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -50.0
  RainSunriseFogOut = 650.0

  DayAmbientColour = (210,200,195)
  DayDirectionalColour = (255,250,245)
  DayFogColour = (150,160,170)
  DayFogIn = 90.0
  DayFogOut = 1600.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (79,83,82)
  RainDayFogIn = -10.0
  RainDayFogOut = 950.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,70)
  SunsetFogIn = 100.0
  SunsetFogOut = 1400.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -50.0
  RainSunsetFogOut = 750.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 220.0
  NightFogOut = 1000.0
  RainNightAmbientColour = (25,25,25)
  RainNightDirectionalColour = (15,15,15)
  RainNightFogColour = (23,25,24)
  RainNighttFogIn = -50.0
  RainNightFogOut = 650.0

  // Sun position
  // Latitude affects day/night length, used with date.
  // Latitude also controls the sun/moon vector across the sky
  // NorthDir controls where sun rises/sets
  // RaceDate affects length of day/night, used with latitude

  Latitude = 25 // in degrees, -90 ... +90 (def. 0)
  NorthDir = 270 // in degrees (def. 245)
  RaceDate = August 30 // (def. July 1)

  HorizonRadius = 948.7
  HorizonMaxHeight = 48.7
  HorizonMinHeight = 10.39

Max Vehicles = 36 

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
  PitGroup=Zwaans
  PitGroup=Freisinger04
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
  Vehicles=2 // Zwaans
  Vehicles=2 // Freisinger04
 } 
} 
 


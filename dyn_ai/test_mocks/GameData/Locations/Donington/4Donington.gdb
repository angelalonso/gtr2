4Donington
{
  AI Vehicle Filter = DONI

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
  RaceLaps = 125
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15
  Pit Board Location = Left

  TrackName = Donington Park GP, 2004 FIA GT Championship Round 6
  GrandPrixName = Donington Park, 2004
  EventName = Round 6: DONINGTON
  VenueName = Donington Park GP, 2004
  Location = Great Britain, Donington
  Length = 2.497 mi/4.020 km
  Track Record = Michael Bartels, 1:28.906, #005 Saleen S7-R

  SettingsFolder = Donington
  SettingsCopy = Donington.svm
  SettingsAI = Donington.svm
  Qualify Laptime = 85.000
  Race Laptime = 87.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.00
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 1.00

  RoadBumpAmp=0.010
  RoadBumpLen=14.0

  // Locality
  Region = North
  Average rain = 0.5
  RainLightScale = 0.85
  RainFogScale = 0.95
  RainFogColourScale = 0.15
  RainCloudScale = 1.0

  // Scene Lighting
  ShadowMinSunAngle=20.0

  SunriseAmbientColour = (165,185,195)
  SunriseDirectionalColour = (120,110,105)
  SunriseFogColour = (30,35,55)
  SunriseFogIn = 0.0
  SunriseFogOut = 1800.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -100.0
  RainSunriseFogOut = 650.0

  DayAmbientColour = (200,205,220)
  DayDirectionalColour = (245,250,255)
  DayFogColour = (130,140,155)
  DayFogIn = 0.0
  DayFogOut = 2000.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (77,80,81)
  RainDayFogIn = -100.0
  RainDayFogOut = 850.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,75)
  SunsetFogIn = 60.0
  SunsetFogOut = 2100.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -100.0
  RainSunsetFogOut = 600.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 80.0
  NightFogOut = 1800.0
  RainNightAmbientColour = (25,25,25)
  RainNightDirectionalColour = (15,15,15)
  RainNightFogColour = (23,25,24)
  RainNighttFogIn = -100.0
  RainNightFogOut = 650.0

  // Sun position
  // Latitude affects day/night length, used with date.
  // Latitude also controls the sun/moon vector across the sky
  // NorthDir controls where sun rises/sets
  // RaceDate affects length of day/night, used with latitude

  Latitude = 25 // in degrees, -90 ... +90 (def. 0)
  NorthDir = 270 // in degrees (def. 245)
  RaceDate = August 30 // (def. July 1) 

  HorizonRadius = 649.08
  HorizonMaxHeight = 58.8
  HorizonMinHeight = 56.62

  Max Vehicles = 30

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

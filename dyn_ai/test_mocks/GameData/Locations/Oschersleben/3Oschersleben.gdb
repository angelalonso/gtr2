3Oschersleben
{
  AI Vehicle Filter = Oschers

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
  RaceLaps = 136
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15
  Pit Board Location = Left

  UnlockPoints = 24
  UnlockPass = 4
  UnlockGold = 0

  TrackName = Oschersleben, 2003 FIA GT Championship Round 8
  GrandPrixName = Oschersleben, 2003
  EventName = Round 8: OSCHERSLEBEN
  VenueName = Oschersleben GP, 2003
  Location = Germany, Oschersleben
  Length = 2.278 m./3.667 km.
  Track Record = Walter Lechner Jr, 1:23.869, #002 Saleen S7-R

  SettingsFolder = Oschersleben
  SettingsCopy = Oschersleben.svm
  SettingsAI = Oschersleben.svm
  Qualify Laptime = 83.000
  Race Laptime = 84.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.00
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 1.00

 
// Locality
  Region = Central
  Average rain = 0.4
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
  SunriseFogOut = 1500.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -50.0
  RainSunriseFogOut = 750.0

  DayAmbientColour = (210,200,195)
  DayDirectionalColour = (255,250,245)
  DayFogColour = (150,160,170)
  DayFogIn = 20.0
  DayFogOut = 2050.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (79,83,82)
  RainDayFogIn = -25.0
  RainDayFogOut = 950.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,80)
  SunsetFogIn = 200.0
  SunsetFogOut = 1550.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -50.0
  RainSunsetFogOut = 650.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 220.0
  NightFogOut = 1250.0
  RainNightAmbientColour = (25,25,25)
  RainNightDirectionalColour = (15,15,15)
  RainNightFogColour = (23,25,24)
  RainNighttFogIn = -50.0
  RainNightFogOut = 750.0

  // Sun position
  // Latitude affects day/night length, used with date.
  // Latitude also controls the sun/moon vector across the sky
  // NorthDir controls where sun rises/sets
  // RaceDate affects length of day/night, used with latitude

  Latitude = 25 // in degrees, -90 ... +90 (def. 0)
  NorthDir = 270 // in degrees (def. 245)
  RaceDate = August 30 // (def. July 1)

  HorizonRadius = 736.4
  HorizonMaxHeight = 87.7
  HorizonMinHeight = 34.9

  Max Vehicles= 32


// Pitstop locations in order from front to back ... if these need to be
// reversed on an individual track, set "ReversePitOrder=1" in the
// track-specific GDB file.

  PitOrder
  {
   PitGroup=BMS
   PitGroup=JMB360
   PitGroup=JMB550
   PitGroup=Freisinger03
   PitGroup=ForceOne
   PitGroup=ListerRacing
   PitGroup=RWSYukos
   PitGroup=Eurotech
   PitGroup=GrahamNash
   PitGroup=Cirtek03
   PitGroup=TMC
   PitGroup=JVG
   PitGroup=Creation
   PitGroup=Larbre
  }

// Number of vehicles sharing each pitstall.  The number of entries
// here must match the number of entries in the PitOrder above.

  NumberSharingPit
  {
   Vehicles=2 // BMS
   Vehicles=2 // JMB360
   Vehicles=2 // JMB550
   Vehicles=2 // Freisinger03
   Vehicles=2 // ForceOne
   Vehicles=2 // ListerRacing
   Vehicles=2 // RWSYukos
   Vehicles=2 // Eurotech
   Vehicles=2 // GrahamNash
   Vehicles=2 // Cirtek03
   Vehicles=2 // TMC
   Vehicles=2 // JVG
   Vehicles=2 // Creation
   Vehicles=2 // Larbre
  } 
}

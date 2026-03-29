SAnderstorp
{
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
  RaceLaps = 250
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 14

  UnlockPoints = 40
  UnlockPass = 6
  UnlockGold = 1

  TrackName = Anderstorp South
  GrandPrixName = AnderstorpSouth
  EventName = ANDERSTORP South
  VenueName = Anderstorp South
  Location = Sweden, Anderstorp
  Length = 1.243 mi/2.000 km

  SettingsFolder = Anderstorp
  SettingsCopy = Anderstorp.svm
  SettingsAI = Anderstorp.svm
  Qualify Laptime = 45.500
  Race Laptime = 47.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.02
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 1.00

  Pit Board Location = Left
  
 // Locality
  Region = North
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
  SunriseFogOut = 3250.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -100.0
  RainSunriseFogOut = 650.0

  DayAmbientColour = (200,205,220)
  DayDirectionalColour = (245,250,255)
  DayFogColour = (130,138,145)
  DayFogIn = 90.0
  DayFogOut = 3000.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,46,45)
  RainDayFogColour = (67,73,71)
  RainDayFogIn = -100.0
  RainDayFogOut = 1050.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,75)
  SunsetFogIn = 200.0
  SunsetFogOut = 2800.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -100.0
  RainSunsetFogOut = 650.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 220.0
  NightFogOut = 1750.0
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
  
  HorizonRadius = 614.3
  HorizonMaxHeight = 65.06
  HorizonMinHeight = 31.1

Max Vehicles = 28 


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
  PitGroup=GrahamNash
  PitGroup=Creation
  PitGroup=TMC
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
  Vehicles=2 // GrahamNash
  Vehicles=2 // Creation
  Vehicles=2 // TMC
 } 
}
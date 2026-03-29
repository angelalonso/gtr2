3Barcelona
{
  AI Vehicle Filter = Barcelona

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
  RaceLaps = 106
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15

  TrackName = Barcelona, 2003 FIA GT Championship Round 1
  GrandPrixName = Barcelona, 2003
  EventName = Round 1: BARCELONA
  VenueName = Barcelona GP, 2003
  Location = Spain, Barcelona
  Length = 2.938 m./4.728 km.
  Track Record = Jamie Campbell-Walter, 1:40.975, #014 Lister Storm

  SettingsFolder = Barcelona
  SettingsCopy = Barcelona.svm
  SettingsAI = Barcelona.svm
  Qualify Laptime = 97.00
  Race Laptime = 99.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.00
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 1.00

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
  SunriseFogOut = 1550.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -50.0
  RainSunriseFogOut = 750.0

  DayAmbientColour = (210,200,195)
  DayDirectionalColour = (255,250,245)
  DayFogColour = (130,140,150)
  DayFogIn = 0.0
  DayFogOut = 1300.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (77,80,82)
  RainDayFogIn = -100.0
  RainDayFogOut = 950.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55) 
  SunsetFogColour = (60,63,85)
  SunsetFogIn = 100.0
  SunsetFogOut = 1200.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -50.0
  RainSunsetFogOut = 750.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 150.0
  NightFogOut = 950.0
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

  HorizonRadius = 614.5
  HorizonMaxHeight = 37.7
  HorizonMinHeight = -6.9

  Max Vehicles = 40 


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
  PitGroup=Eurotech
  PitGroup=Cirtek03
  PitGroup=Larbre
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
  Vehicles=2 // Eurotech
  Vehicles=2 // Cirtek03
  Vehicles=2 // Larbre
  Vehicles=2 // TMC
 } 
}







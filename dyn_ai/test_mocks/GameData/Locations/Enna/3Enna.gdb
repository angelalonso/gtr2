3Enna
{
  AI Vehicle Filter = Enna

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
  RaceLaps = 101
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15

  TrackName = Enna Pergusa, 2003 FIA GT Championship Round 3
  GrandPrixName = Enna Pergusa, 2003
  EventName = Round 3: ENNA PERGUSA
  VenueName = Enna Pergusa GP, 2003
  Location = Italy, Enna
  Length = 3.075 m./4.950 km.
  Track Record = Toni Seiler, 1:34.939, #002 Saleen S7-R

  SettingsFolder = Enna
  SettingsCopy = Enna.svm
  SettingsAI = Enna.svm
  Qualify Laptime = 91.500
  Race Laptime = 93.500

  AIDryGrip = 1.08
  AIWetGrip = 0.78
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 0.80
  RoadBumpAmp=0.015
  RoadBumpLen=10.0
  
// Locality

  Region = South
  Average rain = 0.1
  RainLightScale = 0.85
  RainFogScale = 0.95
  RainFogColourScale = 0.15
  RainCloudScale = 1.0

  // Scene Lighting
  ShadowMinSunAngle=20.0

  SunriseAmbientColour = (165,185,195)
  SunriseDirectionalColour = (120,110,105)
  SunriseFogColour = (50,55,80)
  SunriseFogIn = 0.0
  SunriseFogOut = 4250.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = 0.0
  RainSunriseFogOut = 650.0

  DayAmbientColour = (220,205,195)
  DayDirectionalColour = (255,245,240)
  DayFogColour = (155,160,165)
  DayFogIn = 10.0
  DayFogOut = 4850.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (79,82,81)
  RainDayFogIn = -50.0
  RainDayFogOut = 950.0

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,85)
  SunsetFogIn = 100.0
  SunsetFogOut = 3800.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -50.0
  RainSunsetFogOut = 600.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 120.0
  NightFogOut = 3600.0
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

  HorizonRadius = 706.18
  HorizonMaxHeight = 133
  HorizonMinHeight = 67

  Max Vehicles = 36

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
   Vehicles=2 // Eurotech
   Vehicles=2 // GrahamNash
   Vehicles=2 // TMC 
  } 
}

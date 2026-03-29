3Estoril
{
  AI Vehicle Filter = Estoril

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
  RaceLaps = 120
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15

  TrackName = Estoril, 2003 FIA GT Championship Round 9
  GrandPrixName = Estoril, 2003
  EventName = Round 9: ESTORIL
  VenueName = Estoril GP, 2003
  Location = Portugal, Estoril
  Length = 2.598 m./4.182 km.
  Track Record = Mike Hezemans, 1:36.222, #005 Chrysler Viper GTS-R

  SettingsFolder = Estoril
  SettingsCopy = Estoril.svm
  SettingsAI = Estoril.svm
  Qualify Laptime = 94.000
  Race Laptime = 95.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.02
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 1.00

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
  SunriseFogOut = 1450.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = 0.0
  RainSunriseFogOut = 450.0

  DayAmbientColour = (220,205,195)
  DayDirectionalColour = (255,245,240)
  DayFogColour = (155,160,165)
  DayFogIn = 20.0
  DayFogOut = 1550.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (79,81,82)
  RainDayFogIn = -200.0
  RainDayFogOut = 850.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,85)
  SunsetFogIn = 100.0
  SunsetFogOut = 1400.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -50.0
  RainSunsetFogOut = 500.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 120.0
  NightFogOut = 1000.0
  RainNightAmbientColour = (25,25,25)
  RainNightDirectionalColour = (15,15,15)
  RainNightFogColour = (23,25,24)
  RainNighttFogIn = -50.0
  RainNightFogOut = 550.0

  // Sun position
  // Latitude affects day/night length, used with date.
  // Latitude also controls the sun/moon vector across the sky
  // NorthDir controls where sun rises/sets
  // RaceDate affects length of day/night, used with latitude

  Latitude = 25 // in degrees, -90 ... +90 (def. 0)
  NorthDir = 270 // in degrees (def. 245)
  RaceDate = August 30 // (def. July 1)

  HorizonRadius = 662.751
  HorizonMaxHeight = 51
  HorizonMinHeight = 32

  Max Vehicles = 32
  

// Pitstop locations in order from front to back ... if these need to be
// reversed on an individual track, set "ReversePitOrder=1" in the
// track-specific GDB file.

  PitOrder
  {
   PitGroup=BMS
   PitGroup=JMB360
   PitGroup=JMB575
   PitGroup=Freisinger03
   PitGroup=ListerRacing
   PitGroup=RWSYukos
   PitGroup=Eurotech
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
   Vehicles=2 // JMB575
   Vehicles=2 // Freisinger03
   Vehicles=2 // ListerRacing
   Vehicles=2 // RWSYukos
   Vehicles=2 // Eurotech
   Vehicles=2 // GrahamNash
   Vehicles=2 // Creation
   Vehicles=2 // TMC
  } 
}

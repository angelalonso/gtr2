3Monza
{
  AI Vehicle Filter = Monza

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
  RaceLaps = 87
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15

  UnlockPoints = 75
  UnlockPass = 9
  UnlockGold = 2

  TrackName = Monza, 2003 FIA GT Championship Round 10
  GrandPrixName = Monza, 2003
  EventName = Round 10: MONZA
  VenueName = Monza GP, 2003
  Location = Italy, Monza
  Length = 3.585 mi/5.770 km
  Track Record = Anthony Kumpen, 1:43.559, #005 Chrysler Viper GTS-R

  SettingsFolder = Monza
  SettingsCopy = Monza.svm
  SettingsAI = Monza.svm
  Qualify Laptime = 101.000
  Race Laptime = 103.000

  RoadDryGrip = 1.00
  AIDryGrip = 1.02
  RoadWetGrip = 0.75
  AIWetGrip = 0.76
  PlayerTireWear = 1.0
  FrontTireHeatMult = 1.00
  RearTireHeatMult = 0.90

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
  SunriseFogOut = 2150.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -10.0
  RainSunriseFogOut = 650.0

  DayAmbientColour = (210,200,195)
  DayDirectionalColour = (255,250,245)
  DayFogColour = (150,160,170)
  DayFogIn = 160.0
  DayFogOut = 2100.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,45,45)
  RainDayFogColour = (79,83,82)
  RainDayFogIn = -25.0
  RainDayFogOut = 1050.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,85)
  SunsetFogIn = 100.0
  SunsetFogOut = 1700.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -10.0
  RainSunsetFogOut = 650.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 220.0
  NightFogOut = 1900.0
  RainNightAmbientColour = (25,25,25)
  RainNightDirectionalColour = (15,15,15)
  RainNightFogColour = (23,25,24)
  RainNighttFogIn = -10.0
  RainNightFogOut = 750.0

  // Sun position
  // Latitude affects day/night length, used with date.
  // Latitude also controls the sun/moon vector across the sky
  // NorthDir controls where sun rises/sets
  // RaceDate affects length of day/night, used with latitude

  Latitude = 25 // in degrees, -90 ... +90 (def. 0)
  NorthDir = 270 // in degrees (def. 245)
  RaceDate = August 30 // (def. July 1)
  
  HorizonRadius = 871.45
  HorizonMaxHeight = 51.90
  HorizonMinHeight = 39.64

 Max Vehicles = 48 

 PitOrder
 {
  PitGroup=BMS
  PitGroup=JMB360 
  PitGroup=JMB575
  PitGroup=Freisinger03
  PitGroup=ForceOne
  PitGroup=JVG
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
  Vehicles=2 // ForceOne
  Vehicles=2 // JVG
  Vehicles=2 // ListerRacing
  Vehicles=2 // RWSYukos
  Vehicles=2 // Eurotech
  Vehicles=2 // GrahamNash
  Vehicles=2 // Creation
  Vehicles=2 // TMC
 } 
}
4Spa
{
  AI Vehicle Filter = Spa

  TestDayDay = Wednesday
  TestDayStart = 7:00
  Practice1Day = Thursday
  Practice1Start = 10:30
  Practice2Day = Thursday
  Practice2Start = 14:30
  Qualify1Day = Thursday
  Qualify1Start = 20:30 
  Qualify2Day = Friday
  Qualify2Start = 12:15
  WarmupDay = Saturday
  WarmupStart = 8:10
  RaceDay = Saturday
  RaceStart = 16:00
  RaceLaps = 72
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15

  TrackName = Spa-Francorchamps, 2004 FIA GT Championship Round 7
  GrandPrixName = Spa-Francorchamps 2004
  EventName = Round 7: SPA-FRANCORCHAMPS
  VenueName = Spa-Francorchamps GP, 2004
  Location = Belgium, Francorchamps
  Length = 4.330 mi/6.968 km
  Track Record = Fabrizio Gollin, 2:15.047, #002 Ferrari 550 Maranello

  SettingsFolder = Spa
  SettingsCopy = spa.svm
  SettingsAI = spa.svm
  Qualify Laptime = 131.000
  Race Laptime = 133.000

  Max Vehicles = 62

  RoadDryGrip = 1.00
  AIDryGrip = 1.00
  RoadWetGrip = 0.75
  AIWetGrip = 0.75
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
  SunriseFogOut = 3550.0
  RainSunriseAmbientColour = (85,85,85)
  RainSunriseDirectionalColour = (45,45,45)
  RainSunriseFogColour = (43,53,55)
  RainSunriseFogIn = -35.0
  RainSunriseFogOut = 750.0

  DayAmbientColour = (210,200,195)
  DayDirectionalColour = (255,250,245)
  DayFogColour = (230,240,250)
  DayFogIn = 40.0
  DayFogOut = 3200.0
  RainDayAmbientColour = (105,105,105)
  RainDayDirectionalColour = (45,46,45)
  RainDayFogColour = (69,73,72)
  RainDayFogIn = -35.0
  RainDayFogOut = 1050.0 

  SunsetAmbientColour = (166,160,200)
  SunsetDirectionalColour = (120,90,55)
  SunsetFogColour = (60,63,85)
  SunsetFogIn = 100.0
  SunsetFogOut = 3100.0
  RainSunsetAmbientColour = (72,70,70)
  RainSunsetDirectionalColour = (35,32,32)
  RainSunsetFogColour = (37,41,35) 
  RainSunsetFogIn = -35.0
  RainSunsetFogOut = 750.0

  NightAmbientColour = (25,27,30)
  NightDirectionalColour = (19,20,24)
  NightFogColour = (4,7,10)
  NightFogIn = 220.0
  NightFogOut = 2250.0
  RainNightAmbientColour = (25,25,25)
  RainNightDirectionalColour = (15,15,15)
  RainNightFogColour = (23,25,24)
  RainNightFogIn = -15.0
  RainNightFogOut = 750.0

  // Sun position
  // Latitude affects day/night length, used with date.
  // Latitude also controls the sun/moon vector across the sky
  // NorthDir controls where sun rises/sets
  // RaceDate affects length of day/night, used with latitude

  Latitude = 25 // in degrees, -90 ... +90 (def. 0)
  NorthDir = 270 // in degrees (def. 245)
  RaceDate = August 30 // (def. July 1)

  HorizonRadius = 657.0 //Radius of skybox horizon mesh
  HorizonMaxHeight = 91.3 //Highest point of horizon, flare starts to fade out at this height
  HorizonMinHeight = 71.0 //Lowest point of horizon, flare is all gone

 PitOrder
 {
  PitGroup=BMS
  PitGroup=Vit_Kon
  PitGroup=RML
  PitGroup=JMB575
  PitGroup=GPC
  PitGroup=Zwaans
  PitGroup=Freisinger04
  PitGroup=BMWM3
  PitGroup=Cirtek04
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
  Vehicles=2 // BMWM3
  Vehicles=2 // Cirtek04
 } 
}







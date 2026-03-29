nDonington
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
  RaceLaps = 159
  RaceTime = 180
  RaceTimeScaled = 180

  Attrition = 15
  Pit Board Location = Left

  TrackName = Donington Park National
  GrandPrixName = Donington Park National
  EventName = DONINGTON PARK NATIONAL
  VenueName = Donington Park National
  Location = Great Britain, Donington
  Length = 1.957 mi/3.149 km

  SettingsFolder = Donington
  SettingsCopy = Donington.svm
  SettingsAI = Donington.svm
  Qualify Laptime = 63.000
  Race Laptime = 64.500

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
// These are now "pit group" names, not necessarily team names.
// In the VEH file, the pit group defaults to the team name but
// can be overridden by defining "PitGroup=<name>".

PitOrder
{
  
 PitGroup=BMS
 PitGroup=JMB360
 PitGroup=JMB550
 PitGroup=Freisinger
 PitGroup=ForceOne
 PitGroup=Konrad_Zwaans
 PitGroup=ListerRacing
 PitGroup=RWSYukos
 PitGroup=Eurotech
 PitGroup=GrahamNash
 PitGroup=EMKA_Proton996
 PitGroup=Roos_Wieth
 PitGroup=TMC

   
}

// Number of vehicles sharing each pitstall.  The number of entries
// here must match the number of entries in the PitOrder above.

NumberSharingPit
{

 Vehicles=2 // BMS
 Vehicles=2 // JMB360
 Vehicles=2 // JMB550
 Vehicles=2 // Freisinger
 Vehicles=2 // ForceOne
 Vehicles=2 // Konrad_Zwaans
 Vehicles=2 // ListerRacing
 Vehicles=2 // RWSYukos
 Vehicles=2 // Eurotech
 Vehicles=2 // GrahamNash
 Vehicles=2 // EMKA_Proton996
 Vehicles=2 // Roos_Wieth
 Vehicles=2 // TMC
 
} 
  Qualifying
  {
//FIA TC 1976
	Wolfgang Schachinger =			// BMW CSL
	Dr Helmut Stein =				// Ford Escort RS2000
	Dieter Tögel =				// BMW CSL
	Dr Armin Zumtobel =			// Porsche 906
	Peter Muecke =				// Ford Capri RS3100 Widebody
	Henrik Lindberg =				// Detomaso Pantera
	Pekka Nyström =				// 1972 Chevrolet Corvette
	Jorge Ferreira =				// Ford Escort RS2000
	Ingo Zeitz =				// Porsche 911
	Antonio Nogueira =			// Ford Escort RS2000
	Artur Haas =				// 1974 Chevrolet Corvette
	Carlos Santos =				// Porsche 911
	Claus Damgaard =				// Detomaso Pantera
	Andris Nolendorfs =			// Porsche 911
	Claus Bjerglund =				// Detomaso Pantera
	Fritz Kozka	=				// Porsche 911
	Ferdinand Schreckensteiner =		// Porsche 914/6
	Douglas Titford =				// Ford Capri RS2600
	Thomas Verhoeven =			// Porsche 911
//FIA GTC 1965
	Bo Warmenius =				// Lotus Elan
	Hans-Jurgen Malsbenden =		// Corvette Stingray
	Bernard Peruch =				// AC Shelby Cobra 
	Jamie Boot =				// TVR Griffith 400
	Wolfgang Schachinger =			// Corvette Stingray
	Bill Shepherd =				// AC Shelby Cobra
	Chris Chiles =				// Austin Healey
	Ian Cox =					// Austin Healey
	Michael Menden =				// Corvette Stingray
	Henrik Lindberg =				// Lotus Elan
	Claus Damgaard =				// Lotus Elan
	Peter Kroeber =				// Lotus Elan
	Andre Bailly =				// Jaguar E-Type
	Udo Voßhenrich =				// Lotus Elite
	Theo van Bree =				// Renault Alpine A110
	Leo Voyazides =				// Ford GT40
	Gunther Alth =				// Jaguar E-Type
	Michael Lombard =				// Renault Alpine A110
	Pat van Broeck =				// TVR Griffith 400
	Harry Wyndham =				// Jaguar E-Type
	Ad Verkuijlen =				// Shelby GT350
	Andreas Mayer =				// AC Shelby Cobra
	Jose Albuquerque =			// Ferrari 275GTB
	Ronny Bredhauer =				// Corvette Stingray
	Christian Graf von Wedel =		// Austin Healey
	Michael Kühn =				// Mercedes 300SL
	Rene Weidig =				// Corvette Stingray
	Per Wistoft =				// Lotus Elan
	Wolfram Seehaus =			// Corvette Stingray
	Wulf Goetze =				// Austin Healey
	François Guy =				// Lotus Elan
	Hans Kleissl =				// Mercedes 300SL
	Roddie Feilden =			// Corvette Stingray
	Dr Thomas Kargus =			// Lotus Elan
	Hans Jorgen Krag =			// Shelby GT350
	Richard Bateman =			// Lotus Elan
	John Vandevenne =			// TVR Griffith 400
	Lawrence Bailey =			// TVR Griffith 400
	Ludovic Caron =				// Shelby Daytona Coupe
	Reimer Stöhrmann =			// Lotus Elite
	Veit Avemarg =				// Lotus Elan
	Rolf Nilsson =				// Lotus Elan
//FIA TC-1965
	Max Rostron =				// Ford Mustang
	Nigel Vaulkhard =			// Ford Mustang
	Dieter Karl Anton =			// Alfa Romeo GTA
	Kerry Michael =				// Lotus Cortina
	Bo Warmenius =				// Lotus Cortina
	Alexander Furiani =			// Alfa Romeo GTA
	Mikael Gustavsson =			// Lotus Cortina
	Matthias Oertz =			// Alfa Romeo GTA
	Simon Tate =				// Alfa Romeo GTA
	Fritz Vogel =				// Ford Mustang
	Peter Govaerts =			// Lotus Cortina
	Bill Shepherd =				// Ford Falcon Sprint
	Reinhold Gröpper =			// Ford Mustang
	Richard Oldworth =			// Ford Mustang
	Andy Bacon =				// Ford Falcon Sprint
	Frans de Vos =				// Lotus Cortina
	Richard Styles =			// Ford Mustang
	Don Salvage =				// Jaguar MKII
	Cees van Hauer =			// Alfa Romeo GTA
	Dr Manfred Sontheimer =			// Jaguar MKII
	Richard Bateman =			// Lotus Cortina
	Gary Townsend =				// Lotus Cortina
	Jim Chapman =				// Ford Mustang
	Pantelis Christoforou =			// Lotus Cortina
	Basil Ball =				// Lotus Cortina
	Roland d'Abel de Libran =		// Lotus Cortina
	Allen Tice =				// Mini Cooper‘S’
	Erwin Derichs =				// Ford Mustang
	Graham Churchhill =			// Mini Cooper‘S’
	Niklas Johansson =			// Mini Cooper‘S’
	Ulf von Hauswolf =			// Mini Cooper‘S’
	Graziano Tessaro =			// Abarth 1000TC
	Manuel Ferrao =				// Mini Cooper‘S’
	Bengt Bengtzon =			// Mini Cooper‘S’
  }
  RaceEvents
  {
  }
  Weather
  {
    Practice1
    {
      Conditions = Nice
      TrackWetness = Dry
      AmbientTemp = 20
      TrackTemp = 26
    }
    Practice2
    {
      Conditions = Overcast
      TrackWetness = Damp
      AmbientTemp = 20
      TrackTemp = 21
      Minute = 5
      {
        Conditions = Drizzle
      }
      Minute = 10
      {
        Conditions = Overcast
      }
      Minute = 40
      {
        Conditions = Drizzle
      }
      Minute = 60
      {
        Conditions = Overcast
      }
    }
    Qualify1
    {
      Conditions = Fine
      TrackWetness = Dry
      AmbientTemp = 18
      TrackTemp = 24
    }
    Qualify2
    {
      Conditions = Clear
      TrackWetness = Dry
      AmbientTemp = 18
      TrackTemp = 25
    }
    Warmup
    {
      Conditions = Clear
      TrackWetness = Dry
      AmbientTemp = 22
      TrackTemp = 27
    }
    Race
    {
      Conditions = Best
      TrackWetness = Dry
      AmbientTemp = 23
      TrackTemp = 32
    }
  }
  PitStopStrategies
  {
  }
}




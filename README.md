## Daten vom WeatherSense Server auslesen und per MQTT versenden

Handy Icon:

![Screenshot](https://github.com/ltspicer/WeatherSense/blob/main/weathersense.png)

Manche Wifi Wetterstationen nutzen die WeatherSense Cloud.

Beispielsweise diese Wifi Wetterstationen von Ideoon (Pearl):

![Screenshot](https://github.com/ltspicer/WeatherSense/blob/main/wetterstation.png)

![Screenshot](https://github.com/ltspicer/WeatherSense/blob/main/casativo_ideoon_weatherstation.png)


Dieses Python3 Script liest die Daten vom WeatherSense Server und sendet diese per MQTT (mosquitto) an ein Smarthome System.

Bedingung ist, dass ein MQTT Broker (Server) auf diesem Smarthome System läuft.

Das Script ist nach zBsp /home/pi zu kopieren.

Die Rechte auf 754 setzen ( chmod 754 weathersense.py )

Crontab erstellen ( crontab -e ):

*/10 * * * * /home/pi/weathersense.py # Pfad ggf anpassen!

Weitere Instruktionen sind im Script-Kopf zufinden. Da werden auch die notwendigen Daten wie Logins, IP Adresse, Passwörter usw. eingetragen.

Hier können auch die json Dateien weathersense.{DEVICE-ID}.devData.json und weathersense.{DEVICE-ID}.forecast.json angefordert werden.

## 🚀 Nutzung mehrerer Wetterstationen

Der originale WeatherSense-Cloud-Server hat eine softwareseitige Einschränkung bzw. einen Bug: Wenn du zwei oder mehr identische Wetterstationen im selben Smartphone-Account registrierst, überschreiben sie sich gegenseitig und verschwinden aus deiner Geräteliste.

Um die Daten von mehreren Stationen gleichzeitig und ohne Konflikte auszulesen, kannst du ganz einfach einen zweiten Account anlegen und die DEVICE_ID da auf 2 setzen.

### Einrichten eines zweiten Accounts:

1. **Separate Cloud-Accounts erstellen:** Registriere in der WeatherSense-App für **jede** deiner Wetterstationen einen eigenen, kostenlosen Account (z. B. *Email A* für Station 1 und *Email B* für Station 2).
2. **Eine Station pro Account binden:** Kopple deine erste Station strikt mit Account A und deine zweite Station strikt mit Account B.
3. **Zweites weathersense.py Script anlegen:**
   * Script 1: Account A, DEVICE_ID = 1
   * Script 2: Account B, DEVICE_ID = 2

## Changelog

### V3.3 (2026-07-22)

- Bugfix: Path to “weathersense_topics.txt” in the script directory

### V3.2 (2026-07-22)

- Set existing data point to 0 if not provided by the cloud

### V3.0 (2026-06-20)

- Added automatic sea‑level pressure correction for atmos values based on the configured altitude (altitude_masl).
- Added configuration options for:
  - Rain unit (mm or inch)
  - Temperature unit (°C or °F)
- Previous combined JSON objects are now stored as separate, individual data points to improve clarity and reduce parsing overhead.

### V2.3 (2026-03-06)

- "Ignore powerStatus:0" option added

### V2.2 (2026-01-24)

- DP renamed from allStatesOk to AllStatesOk


### V2.1 (2026-01-23)

- "All status OK" flag added
- MQTT topic changed from WEATHERSENSE to WeatherSense


### V2.0 (2025-08-18)

- Type und Channel Position getauscht für sinnvollere Sortierung


### V1.4 (2025-08-16)

- Datenpunkte dynamischer
- Kanäle korrekt ausgeben
- Ausgabe der Statusdaten


### V1.3 (2025-07-18)

- Hardgecodete IP durch Domain ersetzt


### V1.2 (2025-07-05)

- Alle Felder in devData.json per MQTT versenden

### V1.1 (2025-07-03)

- Zufällige Verzögerung 0-59s


### V1.0 (2025-06-28)

- Erstes Release


------------------------
------------------------


This Python3 script reads the data from the WeatherSense server and sends it via MQTT (mosquitto) to a smart home system.

The prerequisite is that an MQTT broker (server) is running on this smart home system.

The script must be copied to, for example, /home/pi.

Set the permissions to 754 (chmod 754 weathersense.py).

Create crontab (crontab -e):

*/10 * * * * /home/pi/weathersense.py # Adjust the path if necessary!

Further instructions can be found in the script header. The necessary data such as logins, IP address, passwords, etc. are also entered there.

The json files devData.json and forecast.json can also be requested here.

## Handling Multiple Weather Stations

The original WeatherSense cloud server has a software limitation/bug: if you register two or more identical weather stations within the same smartphone account, they will overwrite each other and disappear from your device list.

To read data from multiple stations at the same time without any conflicts, you can simply create a second account and set the DEVICE_ID to 2 there.

### Setting up a second account:

1. **Create Separate Cloud Accounts:** Register a unique, free account for **each** of your weather stations inside the WeatherSense mobile app (e.g., *email A* for Station 1 and *email B* for Station 2).
2. **Bind One Station Per Account:** Pair your first station strictly with Account A and your second station strictly with Account B.
3. **Create a second weathersense.py script:**
   * Script 1: Account A, DEVICE_ID = 1
   * Script 2: Account B, DEVICE_ID = 2

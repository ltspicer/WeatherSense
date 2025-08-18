## Daten vom WeatherSense Server auslesen und per MQTT versenden

Handy Icon:

![Screenshot](https://github.com/ltspicer/WeatherSense/blob/main/weathersense.png)

Manche Wifi Wetterstationen nutzen die WeatherSense Cloud.

Beispielsweise diese Wifi Wetterstation von Ideoon (Pearl):

![Screenshot](https://github.com/ltspicer/WeatherSense/blob/main/wetterstation.png)



Dieses Python3 Script liest die Daten vom WeatherSense Server und sendet diese per MQTT (mosquitto) an ein Smarthome System.

Bedingung ist, dass ein MQTT Broker (Server) auf diesem Smarthome System läuft.

Das Script ist nach zBsp /home/pi zu kopieren.

Die Rechte auf 754 setzen ( chmod 754 weathersense.py )

Crontab erstellen ( crontab -e ):

*/10 * * * * /home/pi/weathersense.py # Pfad ggf anpassen!

Weitere Instruktionen sind im Script-Kopf zufinden. Da werden auch die notwendigen Daten wie Logins, IP Adresse, Passwörter usw. eingetragen.

Hier können auch die json Dateien devData.json und forecast.json angefordert werden.



## Changelog


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


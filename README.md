## Daten vom WeatherSense Server auslesen und per MQTT versenden

![Screenshot](https://github.com/ltspicer/WeatherSense/blob/main/weathersense.png)

![Screenshot](https://github.com/ltspicer/WeatherSense/blob/main/wetterstation.png)
Beispiel diese Wifi Wetterstation von Ideoon (Pearl)


Dieses Python3 Script liest die Daten vom WeatherSense Server und sendet diese per MQTT (mosquitto) an ein Smarthome System.

Bedingung ist, dass ein MQTT Broker (Server) auf diesem Smarthome System läuft.

Das Script ist nach zBsp /home/pi zu kopieren.

Die Rechte auf 754 setzen ( chmod 754 weathersense.py )

Crontab erstellen ( crontab -e ):

*/5 * * * * /home/pi/weathersense.py # Pfad ggf anpassen!

Weitere Instruktionen sind im Script-Kopf zufinden. Da werden auch die notwendigen Daten wie Logins, IP Adresse, Passwörter usw. eingetragen.

Hier können auch die json Dateien devData.json und forecast.json angefordert werden.

Wenn nur die erste Zeile übermittelt wird (kann vorkommen, wenn zBsp das weathersense.py Script auf dem gleichen Host wie das Smarthome System läuft), dann DELAY im Scriptkopf auf True setzen.



## Changelog

### V1.0 (2025-06-28)

- Erstes Release


------------------------
------------------------


This Python3 script reads the data from the WeatherSense server and sends it via MQTT (mosquitto) to a smart home system.

The prerequisite is that an MQTT broker (server) is running on this smart home system.

The script must be copied to, for example, /home/pi.

Set the permissions to 754 (chmod 754 weathersense.py).

Create crontab (crontab -e):

*/5 * * * * /home/pi/weathersense.py # Adjust the path if necessary!

Further instructions can be found in the script header. The necessary data such as logins, IP address, passwords, etc. are also entered there.

The json files devData.json and forecast.json can also be requested here.

If only the first line is transmitted (this can happen if, for example, the weathersense.py script is running on the same host as the smart home system), set DELAY to True in the script header.


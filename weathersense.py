#!/usr/bin/python3

###################################################################################################
#################################             V1.0               ##################################
#############################  WeatherSense-Daten per MQTT versenden  #############################
#################################   (C) 2025 Daniel Luginbühl    ##################################
###################################################################################################

####################################### WICHTIGE INFOS ############################################
################     Im Smarthome System ist ein MQTT Broker zu installieren      #################
################ ---------------------------------------------------------------- #################
################          Falls Raspberry: Alles als User PI ausführen!           #################
################ ---------------------------------------------------------------- #################
################ weathersense.py Script auf Rechte 754 setzen mit:                #################
################ chmod 754 weathersense.py                                        #################
################ Dieses Script per Cronjob 5 Minuten ausführen:                   #################
################ crontab -e                                                       #################
################ */5 * * * * /home/pi/weathersense.py     # Pfad ggf anpassen!    #################
################ ---------------------------------------------------------------- #################
################ Vorgängig zu installieren (auf Host, wo dieses Script läuft):    #################
################    pip3 install requests                                         #################
################    pip3 install paho-mqtt                                        #################
################    pip3 install typing-extensions                                #################
###################################################################################################

""" Deine Eintragungen ab hier:"""

###################################################################################################
################################### Hier Einträge anpassen! #######################################

USERNAME = "uuuuu@gmail.com"    # Deine Email Adresse bei WeatherSense
PASSWORD = "ppppppppp"          # Dein Passwort bei WeatherSense
DEVICE_ID = 1                   # Falls mehrere WeatherSense Geräte, hier ID eintragen (2,3,4, ...)
CELSIUS = True                  # °C oder °F

BROKER_ADDRESS = "192.168.1.50" # MQTT Broker IP (da wo der MQTT Broker läuft)
MQTT_USER = "xxxxxx"            # MQTT User      (im MQTT Broker definiert)
MQTT_PASS = "yyyyyy"            # MQTT Passwort  (im MQTT Broker definiert)
MQTT_PORT = 1883                # MQTT Port      (default: 1883)

#----------------------------- Kann normalerweise belassen werden: -------------------------------#

MQTT_ACTIVE = True              # Auf False, wenn nichts MQTT published werden soll

CREATE_JSON = True              # True = erstelle devData.json und forecast.json
JSON_PATH = ""                  # Pfad für die Json Datei. Standardpfad ist bei Script.
                                # sonst zBsp.: JSON_PATH = "/home/pi/"

DELAY = False                   # Auf True setzen, wenn der MQTT Broker nur die 1. Zeile empfängt
DEBUG = False                   # True = Debug Infos auf die Konsole.

###################################################################################################
###################################################################################################

#--------------------------------- Ab hier nichts mehr verändern! --------------------------------#

import time
import json
import random
import requests
import hashlib
import paho.mqtt.client as mqtt
import urllib3

# Zufällige Zeitverzögerung 0 bis 59 Sekunden. Wichtig, damit der WeatherSense Server
# nicht immer zur gleichen Zeit bombardiert wird!!
verzoegerung = random.randint(0,59)
if DEBUG:
    verzoegerung = 0
print("Datenabfrage startet in", verzoegerung, "Sekunden")
time.sleep(verzoegerung)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
MD5_KEY = "emax@pwd123"
LOGIN_URL = "https://47.52.149.125/V1.0/account/login"

def print_all_keys(d, prefix=""):
    if isinstance(d, dict):
        for k, v in d.items():
            print_all_keys(v, prefix + k + "/")
    elif isinstance(d, list):
        for i, item in enumerate(d):
            print_all_keys(item, prefix + str(i) + "/")
    else:
        print(f"{prefix}: {d}")

# Funktion zum senden per MQTT
def send_mqtt(client, topic, wert):
    """Send MQTT"""
    payload = "" if wert is None else str(wert)
    client.publish(f"WeatherSense/{DEVICE_ID}/{topic}", payload, qos=0, retain=True)

# Hilfsfunktion zum Suchen des Werts anhand von type und channel
def find_value(sensor_list, typ, channel):
    for sensor in sensor_list:
        if sensor.get("type") == typ and sensor.get("channel") == channel:
            return sensor.get("curVal")
    return None

# Funktion zur Erzeugung des MD5-Hashes
def hash_password(pw: str, key: str) -> str:
    combined = pw + key
    return hashlib.md5(combined.encode("utf-8")).hexdigest().upper()

# Login-Funktion
def login():
    hashed_pw = hash_password(PASSWORD, MD5_KEY)

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "okhttp/3.14.9"
    }

    payload = {
        "email": USERNAME,
        "pwd": hashed_pw
    }

    try:
        response = requests.post(LOGIN_URL, headers=headers, json=payload, verify=False)
        if DEBUG:
            print("Status code:", response.status_code)
            print("Response:", response.text)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 0 and "content" in data:
                token = data["content"].get("token")
                if DEBUG:
                    print("✅ Login erfolgreich. Token:", token)
                return token
            else:
                print("❌ Login fehlgeschlagen:", data.get("message"))
        else:
            print("❌ Serverfehler.")
    except Exception as e:
        print("🚫 Fehler beim Login:", str(e))

    return

def clear_old_forecasts(client, max_days=6):
    for i in range(max_days):
        for key in ["day", "date", "high", "low", "text"]:
            send_mqtt(client, f"forecast/{i}/{key}", "")

def send_forecasts(client, forecasts):
    for i, forecast in enumerate(forecasts):
        send_mqtt(client, f"forecast/{i}/day", forecast.get("day"))
        send_mqtt(client, f"forecast/{i}/date", forecast.get("date"))

        if CELSIUS:
            temp_high = "{:.1f}".format((forecast.get("high") - 32) / 1.8)
            temp_low = "{:.1f}".format((forecast.get("low") - 32) / 1.8)
        else:
            temp_high = str(forecast.get("high"))
            temp_low = str(forecast.get("low"))

        send_mqtt(client, f"forecast/{i}/high", temp_high)
        send_mqtt(client, f"forecast/{i}/low", temp_low)
        send_mqtt(client, f"forecast/{i}/text", forecast.get("text"))

def devData(token):
    """WeatherSense Daten holen"""

    url = "https://emaxlife.net/V1.0/weather/devData/getRealtime"
    headers = {
        "emaxtoken": token,
        "Content-Type": "application/json"
    }
    try:
        reply = requests.get(url, headers=headers, verify=False, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei Anfrage: {e}")
        return "error"

    if reply.status_code == 200:
        try:
            data = reply.json()
            if DEBUG:
                print("Daten wurden empfangen")
            return data
        except Exception as e:
            print(f"Fehler beim JSON-Decodieren: {e}")
            return "error"
    else:
        print(f"devData > Status Code: {reply.status_code}")
        return "error"

def foreCast(token):
    """Berechnete zukünftige Oelstände holen"""
    if DEBUG:
        print("getForecast data...")
    url = "https://emaxlife.net/V1.0/weather/netData/getForecast"
    headers = {
        "emaxtoken": token,
        "Content-Type": "application/json"
    }
    try:
        reply = requests.get(url, headers=headers, verify=False, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei Anfrage: {e}")
        return "error"

    if reply.status_code == 200:
        try:
            data = reply.json()
            if DEBUG:
                print("Daten wurden empfangen")
            return data
        except Exception as e:
            print(f"Fehler beim JSON-Decodieren: {e}")
            return "error"
    else:
        print(f"devData > Status Code: {reply.status_code}")
        return "error"

def main():
    """Hauptroutine"""

    if DEBUG:
        print()
    if MQTT_ACTIVE:
        try:
            client = mqtt.Client("WeatherSense")
            if DEBUG:
                print("paho-mqtt version < 2.0")
        except ValueError:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "WeatherSense")
            if DEBUG:
                print("paho-mqtt version >= 2.0")

    if DEBUG:
        print()

    if MQTT_ACTIVE:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
        try:
            client.connect(BROKER_ADDRESS, port=MQTT_PORT)
        except OSError as error:
            print("Verbindung zum MQTT-Broker fehlgeschlagen")
            print("Connection to MQTT broker failed")
            print(error)

    token = login()

    if not token:
        print("No token. Abort")
        return

    daten = devData(token)
    if daten == "error":
        print("Fehler. Keine devData Daten empfangen.")
        if MQTT_ACTIVE:
            client.disconnect()
        return

    if CREATE_JSON:
        json_object = json.dumps(daten, indent=4)
        with open(JSON_PATH + "devData.json","w", encoding="utf-8") as datei:
            datei.write(json_object)

    if DEBUG:
        print()
        print("devData JSON:")
        print("=============")
        print()
        #print(daten)
        print_all_keys(daten)
        print()

    if MQTT_ACTIVE:
        content = daten.get("content", {})
        sensor_data = content.get("sensorDatas", [])
        error_code = daten.get("error")

        if error_code is not None:
            send_mqtt(client, "error", error_code)

        dev_time = content.get("devTime")
        if dev_time:
            send_mqtt(client, "devtime", dev_time)

        upd_time = content.get("updateTime")
        if upd_time:
            send_mqtt(client, "updateTime", upd_time)

        device_mac = content.get("deviceMac")
        if device_mac:
            send_mqtt(client, "deviceMac", device_mac)

        dev_timezone = content.get("devTimezone")
        if dev_timezone is not None:
            send_mqtt(client, "devTimezone", dev_timezone)

        wireless_status = content.get("wirelessStatus")
        if wireless_status is not None:
            send_mqtt(client, "wirelessStatus", wireless_status)

        power_status = content.get("powerStatus")
        if power_status is not None:
            send_mqtt(client, "powerStatus", power_status)

        weather_status = content.get("weatherStatus")
        if weather_status is not None:
            send_mqtt(client, "weatherStatus", weather_status)

        # MQTT-Daten vorbereiten
        luftdruck = content.get("atmos")
        temp_innen = find_value(sensor_data, 1, 0)
        feuchte_innen = find_value(sensor_data, 2, 0)
        temp_aussen = find_value(sensor_data, 1, 2)
        feuchte_aussen = find_value(sensor_data, 2, 2)

        if CELSIUS:
            if temp_innen is not None:
                temp_innen = "{:.1f}".format((temp_innen - 32) / 1.8)
            if temp_aussen is not None:
                temp_aussen = "{:.1f}".format((temp_aussen - 32) / 1.8)

        # Senden
        if luftdruck is not None:
            send_mqtt(client, "luftdruck", luftdruck)
        if temp_innen is not None:
            send_mqtt(client, "temp_innen", temp_innen)
        if feuchte_innen is not None:
            send_mqtt(client, "feuchte_innen", feuchte_innen)
        if temp_aussen is not None:
            send_mqtt(client, "temp_aussen", temp_aussen)
        if feuchte_aussen is not None:
            send_mqtt(client, "feuchte_aussen", feuchte_aussen)

        if DELAY:
            time.sleep(0.05)

    forecast = foreCast(token)

    if forecast == "error":
        print("Fehler. Keine forecast Daten empfangen.")
        return

    if CREATE_JSON:
        json_object = json.dumps(forecast, indent=4)
        with open(JSON_PATH + "forecast.json","w", encoding="utf-8") as datei:
            datei.write(json_object)

    if DEBUG:
        print()
        print("forecast JSON:")
        print("==============")
        print()
        #print(daten)
        print_all_keys(forecast)
        print()

    if MQTT_ACTIVE:
        forecasts = forecast.get("content", {}).get("forecast", {}).get("forecasts", [])
        # zuerst alte Daten löschen
        clear_old_forecasts(client, max_days=6)
        time.sleep(2)

        # neue senden
        send_forecasts(client, forecasts)

        if DELAY:
            time.sleep(0.05)
        client.disconnect()

if __name__ == "__main__":
    main()

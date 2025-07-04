#!/usr/bin/python3

###################################################################################################
#################################             V1.2               ##################################
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
import base64

# Zufällige Zeitverzögerung 0 bis 59 Sekunden. Wichtig, damit der WeatherSense Server
# nicht immer zur gleichen Zeit bombardiert wird!!
verzoegerung = random.randint(0,59)
if DEBUG:
    verzoegerung = 0
print("Datenabfrage startet in", verzoegerung, "Sekunden")
time.sleep(verzoegerung)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
def hash_password(pw: str) -> str:
    key = base64.b64decode("ZW1heEBwd2QxMjM=").decode("utf-8")
    combined = pw + key
    return hashlib.md5(combined.encode("utf-8")).hexdigest().upper()

# Login-Funktion
def login():
    hashed_pw = hash_password(PASSWORD)

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
    if DEBUG:
        print("getRealtime data...")
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
    """Forecast holen"""
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
        print_all_keys(daten)
        print()

    if MQTT_ACTIVE:
        content = daten.get("content", {})
        sensor_data = content.get("sensorDatas", [])
        error_code = daten.get("error")

        skip_combinations = {"1_0", "1_2", "2_0", "2_2"}
        content_dev_data = {}

        if error_code is not None:
            send_mqtt(client, "devData/error", error_code)

        if content.get("devTime"):
            send_mqtt(client, "devData/devtime", content["devTime"])
        if content.get("updateTime"):
            send_mqtt(client, "devData/updateTime", content["updateTime"])
        if content.get("deviceMac"):
            send_mqtt(client, "devData/deviceMac", content["deviceMac"])
        if content.get("devTimezone") is not None:
            send_mqtt(client, "devData/devTimezone", content["devTimezone"])
        if content.get("wirelessStatus") is not None:
            send_mqtt(client, "devData/wirelessStatus", content["wirelessStatus"])
        if content.get("powerStatus") is not None:
            send_mqtt(client, "devData/powerStatus", content["powerStatus"])
        if content.get("weatherStatus") is not None:
            send_mqtt(client, "devData/weatherStatus", content["weatherStatus"])

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

        # MQTT senden
        if luftdruck is not None:
            send_mqtt(client, "devData/atmospheric_pressure", luftdruck)
        if temp_innen is not None:
            send_mqtt(client, "devData/indoor_temp", temp_innen)
        if feuchte_innen is not None:
            send_mqtt(client, "devData/indoor_humidity", feuchte_innen)
        if temp_aussen is not None:
            send_mqtt(client, "devData/outdoor_temp", temp_aussen)
        if feuchte_aussen is not None:
            send_mqtt(client, "devData/outdoor_humidity", feuchte_aussen)

        # Werte in content_dev_data speichern
        content_dev_data.update({
            "atmospheric_pressure": luftdruck,
            "indoor_temp": temp_innen,
            "indoor_humidity": feuchte_innen,
            "outdoor_temp": temp_aussen,
            "outdoor_humidity": feuchte_aussen,
        })

        # Zusätzliche Sensoren
        for s in sensor_data:
            type_ = s.get("type")
            channel = s.get("channel")
            cur_val = s.get("curVal")
            high_val = s.get("hihgVal")  # Schreibfehler im Key beibehalten
            low_val = s.get("lowVal")

            key = f"{type_}_{channel}"
            if key in skip_combinations:
                continue

            base = f"devData/sensor_{key}"

            if cur_val is not None and cur_val != 65535:
                send_mqtt(client, f"{base}/current", cur_val)
                content_dev_data[f"sensor_{key}_current"] = cur_val
            if high_val is not None and high_val != 65535:
                send_mqtt(client, f"{base}/high", high_val)
                content_dev_data[f"sensor_{key}_high"] = high_val
            if low_val is not None and low_val != 65535:
                send_mqtt(client, f"{base}/low", low_val)
                content_dev_data[f"sensor_{key}_low"] = low_val

            # Weitere verschachtelte Schlüssel prüfen
            for k, v in s.items():
                if k in {"type", "channel", "curVal", "hihgVal", "lowVal"}:
                    continue
                if isinstance(v, dict):
                    if not v:
                        # leeres Objekt
                        send_mqtt(client, f"{base}/{k}", "n/a")
                        content_dev_data[f"sensor_{key}_{k}"] = "n/a"
                    else:
                        for sub_k, sub_v in v.items():
                            if sub_v is not None:
                                topic = f"{base}/{k}/{sub_k}"
                                send_mqtt(client, topic, sub_v)
                                content_dev_data[f"sensor_{key}_{k}_{sub_k}"] = sub_v
                elif v is not None:
                    content_dev_data[f"sensor_{key}_{k}"] = v

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

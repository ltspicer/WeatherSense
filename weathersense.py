#!/usr/bin/python3

###################################################################################################
#################################             V3.0               ##################################
#############################  WeatherSense-Daten per MQTT versenden  #############################
#################################   (C) 2026 Daniel Luginbühl    ##################################
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
################ */10 * * * * /home/pi/weathersense.py     # Pfad ggf anpassen!   #################
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
RAIN_UNIT_MM = True             # Niederschlag True = mm, False = inch
ALTITUDE_MASL = 980             # Meter über Meer

BROKER_ADDRESS = "192.168.1.50" # MQTT Broker IP (da wo der MQTT Broker läuft)
MQTT_USER = "xxxxxx"            # MQTT User      (im MQTT Broker definiert)
MQTT_PASS = "yyyyyy"            # MQTT Passwort  (im MQTT Broker definiert)
MQTT_PORT = 1883                # MQTT Port      (default: 1883)

#----------------------------- Kann normalerweise belassen werden: -------------------------------#

MQTT_ACTIVE = True              # Auf False, wenn nichts MQTT published werden soll

CREATE_JSON = True              # True = erstelle devData.json und forecast.json
JSON_PATH = ""                  # Pfad für die Json Datei. Standardpfad ist bei Script.
                                # sonst zBsp.: JSON_PATH = "/home/pi/"

IGNORE_POWER_STATUS = False     # Manche Geräte senden 0, obschon der powerStatus OK ist
                                # In diesem Fall kann dies hier mit "True" ignoriert werden.

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

LOGIN_URL = "https://emaxlife.net/V1.0/account/login"

def is_invalid(v):
    return v in (None, 65535, 255)


def apply_pressure_correction(value, altitude_masl):
    """Barometrische Höhenkorrektur"""
    if value is None:
        return None
    try:
        return int(round(value * pow(1 - (0.0065 * altitude_masl) / 288.15, -5.255), 0))
    except Exception:
        return value


def send_json_recursive(client, base, obj, RAIN_UNIT_MM, ALTITUDE_MASL):
    """Alle JSON‑DPs einzeln senden (rekursiv)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_base = f"{base}/{k}"
            send_json_recursive(client, new_base, v, RAIN_UNIT_MM, ALTITUDE_MASL)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_base = f"{base}/{i}"
            send_json_recursive(client, new_base, item, RAIN_UNIT_MM, ALTITUDE_MASL)

    else:
        if is_invalid(obj):
            return

        val = obj

        end_topic = base.split("/")[-1].lower()

        # --- Light → /1000, aber UV NICHT ---
        if "light" in end_topic and "ultraviolet" not in end_topic:
            if isinstance(val, (int, float)):
                val = val / 1000

        # --- Rain → mm/inch + 1 Nachkommastelle ---
        if "rain" in end_topic and isinstance(val, (int, float)):
            val = mm_inch_berechnen(val, RAIN_UNIT_MM)
            val = round(val, 1)

        # --- Luftdruck korrigieren ---
        if "atmos" in base.lower() and isinstance(val, (int, float)):
            val = apply_pressure_correction(val, ALTITUDE_MASL)

        send_mqtt(client, base, val)

def print_all_keys(d, prefix=""):
    if isinstance(d, dict):
        for k, v in d.items():
            print_all_keys(v, prefix + k + "/")
    elif isinstance(d, list):
        for i, item in enumerate(d):
            print_all_keys(item, prefix + str(i) + "/")
    else:
        print(f"{prefix}: {d}")

def is_success(data):
    try:
        if not data["status"] == 0:
            print("status:", data["status"])
            return False
        if not data["error"] == 0:
            print("error:", data["error"])
            return False
        if not data["message"] == "success":
            print("message:", data["message"])
            return False
        if data["content"].get("powerStatus") == 0:
            if IGNORE_POWER_STATUS:
                if DEBUG:
                    print("content/powerStatus:", data["content"].get("powerStatus"), " → Must normally be greater than 0")
            else:
                print("content/powerStatus:", data["content"].get("powerStatus"), "→ Power supply OK?")
                return False
        return True
    except KeyError:
        return False

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
            send_mqtt(client, f"forecast/day_{i}/{key}", "")

def send_forecasts(client, forecasts):
    for i, forecast in enumerate(forecasts):
        send_mqtt(client, f"forecast/day_{i}/day", forecast.get("day"))
        send_mqtt(client, f"forecast/day_{i}/date", forecast.get("date"))

        if CELSIUS:
            temp_high = "{:.1f}".format((forecast.get("high") - 32) / 1.8)
            temp_low = "{:.1f}".format((forecast.get("low") - 32) / 1.8)
        else:
            temp_high = str(forecast.get("high"))
            temp_low = str(forecast.get("low"))

        send_mqtt(client, f"forecast/day_{i}/high", temp_high)
        send_mqtt(client, f"forecast/day_{i}/low", temp_low)
        send_mqtt(client, f"forecast/day_{i}/text", forecast.get("text"))

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

def c_f_berechnen(temp, prefix):
    """°F nach °C umwandeln, falls notwendig"""

    if CELSIUS and prefix == "-Temp":
        if temp is not None:
            temp = "{:.1f}".format((temp - 32) / 1.8)
    return temp    

def mm_inch_berechnen(wert, RAIN_UNIT_MM):
        """inch nach mm umwandeln, falls notwendig"""

        if (RAIN_UNIT_MM):
            wert = wert * 25.4
        return wert

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
            send_mqtt(client, "AllStatesOk", False)
            time.sleep(0.1)
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

    status = is_success(daten)

    if MQTT_ACTIVE:
        # --- 1. Top-Level devData ---
        for key, value in daten.items():
            if key == "content":
                continue
            if not is_invalid(value):
                send_mqtt(client, f"devData/{key}", value)

        # --- 2. content.* ---
        content = daten.get("content", {})
        for key, value in content.items():
            if key == "sensorDatas":
                continue

            if key.lower() == "atmos" and isinstance(value, (int, float)):
                value = apply_pressure_correction(value, ALTITUDE_MASL)

            if not is_invalid(value):
                send_mqtt(client, f"devData/{key}", value)

            # --- 3. sensorDatas ---
            sensor_data = content.get("sensorDatas", [])

            for s in sensor_data:
                type_ = s.get("type")
                channel = s.get("channel")

                cur_val = s.get("curVal")
                high_val = s.get("hihgVal")
                low_val = s.get("lowVal")

                prefix = ""
                if type_ == 1:
                    prefix = "-Temp"
                elif type_ == 2:
                    prefix = "-Hum"
                elif type_ == 7:
                    prefix = "-Atmos"

                key = f"Channel{channel}-Type{type_}{prefix}"
                base = f"devData/{key}"

                # --- 3a. Einzelwerte ---
                if not is_invalid(cur_val):
                    val = cur_val

                    # Atmos-Korrektur
                    if type_ == 7 and isinstance(val, (int, float)):
                        val = apply_pressure_correction(val, ALTITUDE_MASL)
                        val = int(round(val, 0))  # 0 Nachkommastellen

                    else:
                        val = c_f_berechnen(val, prefix)

                    send_mqtt(client, f"{base}/current", val)

                if not is_invalid(high_val):
                    val = high_val

                    if type_ == 7 and isinstance(val, (int, float)):
                        val = apply_pressure_correction(val, ALTITUDE_MASL)
                        val = int(round(val, 0))
                    else:
                        val = c_f_berechnen(val, prefix)

                    send_mqtt(client, f"{base}/high", val)

                if not is_invalid(low_val):
                    val = low_val

                    if type_ == 7 and isinstance(val, (int, float)):
                        val = apply_pressure_correction(val, ALTITUDE_MASL)
                        val = int(round(val, 0))
                    else:
                        val = c_f_berechnen(val, prefix)

                    send_mqtt(client, f"{base}/low", val)

                # --- 3b. dev*-Objekte rekursiv senden ---
                for k, v in s.items():
                    if not k.startswith("dev"):
                        continue
                    if v in (None, {}):
                        continue

                    # Einzelwert (kein dict)
                    if not isinstance(v, dict):

                        val = v
                        end_topic = k.lower()

                        # Light
                        if "light" in end_topic and "ultraviolet" not in end_topic:
                            val = val / 1000

                        # Rain
                        if "rain" in end_topic:
                            val = mm_inch_berechnen(val, RAIN_UNIT_MM)
                            val = round(val, 1)

                        # Atmos
                        if "atmos" in base.lower() and isinstance(val, (int, float)):
                            val = apply_pressure_correction(val, ALTITUDE_MASL)
                            val = int(round(val, 0))

                        send_mqtt(client, f"{base}/{k}", val)
                        continue

                    # dict → rekursiv
                    send_json_recursive(
                        client,
                        f"{base}/{k}",
                        v,
                        RAIN_UNIT_MM,
                        ALTITUDE_MASL
                    )

        time.sleep(0.1)

    forecast = foreCast(token)

    if forecast == "error":
        print("Fehler. Keine forecast Daten empfangen.")
        if MQTT_ACTIVE:
            send_mqtt(client, "AllStatesOk", False)
            client.disconnect()
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

        if status:
            status = is_success(forecast)

        time.sleep(0.1)
        send_mqtt(client, "AllStatesOk", status)
        client.disconnect()

    if DEBUG:
        print(f"AllStatesOk: {status}")

if __name__ == "__main__":
    main()

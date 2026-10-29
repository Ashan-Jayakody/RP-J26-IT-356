import paho.mqtt.client as mqtt
import json
import time
from collections import deque

# =====================================================
# CONFIGURATION (ඔබේ අගයන් මෙතන දාන්න)
# =====================================================
MQTT_BROKER = "192.168.1.4"     # ඔබේ ලැප්ටොප් එකේ IP එක
MQTT_PORT = 1883
MQTT_TOPIC = "flood/v1/stations/S01/telemetry"
MQTT_USERNAME = "flood_station"
MQTT_PASSWORD = "YOUR_MQTT_PASSWORD"  # ඔබේ MQTT password එක මෙතන දාන්න

# =====================================================
# ROR PARAMETERS
# =====================================================
ROR_WINDOW_SECONDS = 30
STABLE_THRESHOLD_CM_MIN = 0.1

# =====================================================
# HISTORY
# =====================================================
water_level_history = deque()

def calculate_ror(current_level):
    now = time.time()
    water_level_history.append((now, current_level))
    
    # Remove old samples
    while water_level_history and now - water_level_history[0][0] > ROR_WINDOW_SECONDS:
        water_level_history.popleft()
        
    if len(water_level_history) < 2:
        return 0.0, 0.0, "WAITING", 0.0
        
    oldest_time, oldest_level = water_level_history[0]
    newest_time, newest_level = water_level_history[-1]
    
    elapsed_seconds = newest_time - oldest_time
    if elapsed_seconds < 27:
        return 0.0, 0.0, "WAITING", elapsed_seconds
        
    elapsed_minutes = elapsed_seconds / 60.0
    level_change = newest_level - oldest_level
    ror = level_change / elapsed_minutes
    
    if ror > STABLE_THRESHOLD_CM_MIN:
        trend = "RISING"
    elif ror < -STABLE_THRESHOLD_CM_MIN:
        trend = "FALLING"
    else:
        trend = "STABLE"
        
    return round(ror, 2), round(level_change, 2), trend, round(elapsed_seconds, 1)

# =====================================================
# MQTT CALLBACKS
# =====================================================
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        print("\n" + "="*50)
        print("================ SENSOR DATA ================")
        print(f"Station:       {data.get('station_id', 'N/A')}")
        print(f"Packet:        {data.get('packet', 'N/A')}")
        print(f"Water Level:   {data.get('water_level_cm', 0)} cm")
        print(f"Distance:      {data.get('distance_cm', 0)} cm")
        print(f"Rain Raw:      {data.get('rain_raw', 0)}")
        print(f"Rain Status:   {data.get('rain_status', 'N/A')}")
        print(f"Flow Rate:     {data.get('flow_rate_l_min', 0)} L/min")
        print(f"Total Flow:    {data.get('flow_total_l', 0)} L")
        print("-" * 50)
        
        # RoR Calculation
        water_level = float(data.get('water_level_cm', 0.0))
        ror, change, trend, window = calculate_ror(water_level)
        
        print("RATE OF RISE ANALYSIS")
        print("-" * 50)
        print(f"Window:        {window} seconds")
        print(f"Level Change:  {'+' if change >= 0 else ''}{change} cm")
        print(f"Rate of Rise:  {'+' if ror >= 0 else ''}{ror} cm/min")
        print(f"Trend:         {trend}")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error parsing message: {e}")

# =====================================================
# MQTT SETUP
# =====================================================
client = mqtt.Client()
client.username_pw_set("flood_station","Flood2026")
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
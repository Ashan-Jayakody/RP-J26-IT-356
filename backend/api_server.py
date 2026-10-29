import json
import time
import logging
from collections import deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
import uvicorn

# =====================================================
# LOGGING CONFIGURATION
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURATION
# =====================================================
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
MQTT_TOPIC = "flood/v1/stations/S01/telemetry"

MQTT_USERNAME = "flood_station"
MQTT_PASSWORD = "Flood2026"

# =====================================================
# RoR PARAMETERS
# =====================================================
ROR_WINDOW_SECONDS = 30
MIN_ROR_WINDOW_SECONDS = 27
STABLE_THRESHOLD_CM_MIN = 0.1

# =====================================================
# GLOBAL STATE VARIABLES
# =====================================================
latest_sensor_data = {
    "station_id": "S01",
    "packet": 0,
    "water_level_cm": 0.0,
    "distance_cm": 0.0,
    "max_level_cm": 0.0,
    "level_pct": 0,
    "rain_raw": 0,
    "rain_status": "UNKNOWN",
    "flow_pulses": 0,
    "flow_rate_l_min": 0.0,
    "flow_total_l": 0.0,
    "last_updated": "--"
}

latest_ror_data = {
    "rate_of_rise_cm_min": 0.0,
    "level_change_cm": 0.0,
    "trend": "WAITING",
    "window_seconds": 0.0
}

latest_alert = {
    "severity": "SAFE",
    "title": "NORMAL",
    "message": "Conditions are normal. No flood risk detected."
}

water_level_history = deque()

# =====================================================
# FASTAPI INITIALIZATION
# =====================================================
app = FastAPI(title="Flood Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# API ENDPOINTS
# =====================================================
@app.get("/api/latest")
def get_latest_data():
    """Return the latest sensor readings and RoR together."""
    return {
        "sensor_data": latest_sensor_data.copy(),
        "rate_of_rise": latest_ror_data.copy(),
        "alert": latest_alert.copy()
    }


@app.get("/api/sensor")
def get_sensor_data():
    """Return sensor readings and RoR in one flat JSON response."""
    result = latest_sensor_data.copy()
    result.update(latest_ror_data)
    result["alert_severity"] = latest_alert["severity"]
    result["alert_title"] = latest_alert["title"]
    result["alert_message"] = latest_alert["message"]
    return result


@app.get("/api/alert")
def get_current_alert():
    """Return the current alert state."""
    return latest_alert.copy()


@app.get("/api/health")
def health_check():
    """Check whether the API is running."""
    return {"status": "online"}


# =====================================================
# RoR CALCULATION
# =====================================================
def calculate_ror(current_level):
    """Calculate the water-level change rate in cm/min."""
    now = time.monotonic()
    water_level_history.append((now, current_level))

    # Keep samples inside the configured time window.
    while (
        water_level_history
        and now - water_level_history[0][0] > ROR_WINDOW_SECONDS
    ):
        water_level_history.popleft()

    if len(water_level_history) < 2:
        return 0.0, 0.0, "WAITING", 0.0

    oldest_time, oldest_level = water_level_history[0]
    newest_time, newest_level = water_level_history[-1]

    elapsed_seconds = newest_time - oldest_time

    if elapsed_seconds < MIN_ROR_WINDOW_SECONDS:
        return 0.0, 0.0, "WAITING", round(elapsed_seconds, 1)

    elapsed_minutes = elapsed_seconds / 60.0
    level_change = newest_level - oldest_level
    ror = level_change / elapsed_minutes

    if ror > STABLE_THRESHOLD_CM_MIN:
        trend = "RISING"
    elif ror < -STABLE_THRESHOLD_CM_MIN:
        trend = "FALLING"
    else:
        trend = "STABLE"

    return (
        round(ror, 2),
        round(level_change, 2),
        trend,
        round(elapsed_seconds, 1)
    )


# =====================================================
# ALERT ANALYSIS
# =====================================================
def analyze_alert(water_level, ror, rain_status):
    """Determine alert severity using water level, RoR and rain status."""

    if water_level > 18.0 or ror > 0.5:
        return {
            "severity": "CRITICAL",
            "title": "EMERGENCY FLOOD WARNING",
            "message": (
                f"Critical water level: {water_level:.2f} cm. "
                "Follow official emergency instructions."
            )
        }

    elif water_level > 10.0 or rain_status == "WET":
        return {
            "severity": "WARNING",
            "title": "FLOOD WATCH",
            "message": (
                f"Water level is {water_level:.2f} cm. "
                "Monitor the situation closely."
            )
        }

    return {
        "severity": "SAFE",
        "title": "STATUS NORMAL",
        "message": (
            f"Conditions are within configured alert thresholds. "
            f"Water level: {water_level:.2f} cm."
        )
    }


# =====================================================
# MQTT CALLBACKS
# =====================================================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker successfully.")
        result, mid = client.subscribe(MQTT_TOPIC)

        if result == mqtt.MQTT_ERR_SUCCESS:
            logger.info("Subscribed to topic: %s", MQTT_TOPIC)
        else:
            logger.error("Failed to subscribe to MQTT topic.")

    else:
        logger.error(
            "Failed to connect to MQTT Broker. Return code: %s", rc
        )


def on_message(client, userdata, msg):
    global latest_sensor_data, latest_ror_data, latest_alert

    try:
        data = json.loads(msg.payload.decode("utf-8"))

        # Ignore messages that are not valid JSON objects.
        if not isinstance(data, dict):
            logger.error("Received JSON payload is not an object.")
            return

        # Parse water level safely.
        water_level = float(data.get("water_level_cm", 0.0))
        rain_status = str(data.get("rain_status", "UNKNOWN")).upper()

        # Update latest sensor readings.
        latest_sensor_data.update({
            "station_id": data.get("station_id", "S01"),
            "packet": data.get("packet", 0),
            "water_level_cm": water_level,
            "distance_cm": data.get("distance_cm", 0.0),
            "max_level_cm": data.get("max_level_cm", 0.0),
            "level_pct": data.get("level_pct", 0),
            "rain_raw": data.get("rain_raw", 0),
            "rain_status": rain_status,
            "flow_pulses": data.get("flow_pulses", 0),
            "flow_rate_l_min": data.get("flow_rate_l_min", 0.0),
            "flow_total_l": data.get("flow_total_l", 0.0),
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        })

        # Calculate RoR from received water-level readings.
        ror, change, trend, window = calculate_ror(water_level)

        latest_ror_data.update({
            "rate_of_rise_cm_min": ror,
            "level_change_cm": change,
            "trend": trend,
            "window_seconds": window
        })

        # Update alert information.
        latest_alert = analyze_alert(
            water_level,
            ror,
            rain_status
        )

        # Display all readings and RoR together.
        logger.info(
            "\n"
            "================ SENSOR + RoR OUTPUT ================\n"
            f"Station ID:       {latest_sensor_data['station_id']}\n"
            f"Packet:           {latest_sensor_data['packet']}\n"
            f"Water Level:      {water_level:.2f} cm\n"
            f"Distance:         {latest_sensor_data['distance_cm']} cm\n"
            f"Maximum Level:    {latest_sensor_data['max_level_cm']} cm\n"
            f"Level Percentage: {latest_sensor_data['level_pct']}%\n"
            f"Rain Raw:         {latest_sensor_data['rain_raw']}\n"
            f"Rain Status:      {rain_status}\n"
            f"Flow Pulses:      {latest_sensor_data['flow_pulses']}\n"
            f"Flow Rate:        {latest_sensor_data['flow_rate_l_min']} L/min\n"
            f"Total Flow:       {latest_sensor_data['flow_total_l']} L\n"
            "-----------------------------------------------------\n"
            f"Level Change:     {change:+.2f} cm\n"
            f"Rate of Rise:     {ror:+.2f} cm/min\n"
            f"Trend:            {trend}\n"
            f"RoR Window:       {window:.1f} seconds\n"
            "-----------------------------------------------------\n"
            f"Alert Severity:   {latest_alert['severity']}\n"
            f"Alert Title:      {latest_alert['title']}\n"
            f"Last Updated:     {latest_sensor_data['last_updated']}\n"
            "====================================================="
        )

    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error("Failed to decode incoming JSON payload.")

    except (TypeError, ValueError) as e:
        logger.error("Invalid sensor value in MQTT payload: %s", e)

    except Exception:
        logger.exception("Error processing MQTT message.")


# =====================================================
# MQTT SETUP
# =====================================================
def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    logger.info(
        "Connecting to MQTT Broker at %s:%s...",
        MQTT_BROKER,
        MQTT_PORT
    )

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    return client


# =====================================================
# MAIN EXECUTION
# =====================================================
if __name__ == "__main__":
    mqtt_client = start_mqtt()

    logger.info("Starting FastAPI Server on port 8000...")

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
# Component 1: Flood Monitoring And AI Weather Intelligence

## 1. Introduction

Component 1 focuses on real-time environmental sensing, wireless telemetry, and backend intelligence for flood detection. It uses an ESP32-based sensor station to measure water levels, rainfall/wetness, and pipe flow rates. 

The system processes sensor data at the edge, packages it as a JSON payload, and transmits it via a dual-path communication method: Long-Range (LoRa) radio and Wi-Fi/MQTT. A Python FastAPI backend ingests this data, calculates the Rate of Rise (RoR) of the water level, and generates real-time Alert States that are served to the visualization dashboard.

## 2. Technologies Used

- ESP32-WROOM-32 Microcontroller (Arduino IDE / C++)
- JSN-SR04T Waterproof Ultrasonic Sensor
- LM393 Resistive Rain/Wetness Sensor
- YF-S201 Hall-effect Flow Sensor
- SX1278 LoRa Module (433 MHz)
- Wi-Fi and MQTT (Mosquitto Local Broker & AWS IoT Core)
- Python 3.11
- FastAPI and Uvicorn
- paho-mqtt
- ArduinoJson / NVS Preferences Library

## 3. Main Features

### 3.1 Edge Sensing and Auto-Calibration

The system reads three primary sensors connected to the ESP32. To ensure accuracy across different physical deployments, an **Auto-Calibration** mechanism is implemented using the ESP32's non-volatile storage (NVS/Preferences).

On the first boot, the system measures the "empty bucket" distance (sensor-to-bottom). This value is saved to memory, eliminating the need to hardcode the calibration constant in the firmware. The water level is calculated as:

```cpp
waterLevel = sensorToBottomCm - measuredDistance;
```

### 3.2 Sensor Filtering and Inverted Rain Logic

To prevent false alerts caused by sensor noise, digital filtering is applied:
- **Ultrasonic Filtering:** A moving average filter suppresses intermittent ultrasonic timeout spikes.
- **Inverted Rain Logic:** The LM393 module used in this setup outputs a lower ADC value when wet and a higher value when dry. The firmware classifies the wetness status as:
  - `WET`: `rain_raw < 3100`
  - `LIGHT`: `3100 ≤ rain_raw < 3800`
  - `DRY`: `rain_raw ≥ 3800`

### 3.3 Flow Rate Calculation via Interrupts

The YF-S201 flow sensor generates fast pulses. To prevent missing counts, a hardware interrupt is attached to GPIO 27.

```cpp
void IRAM_ATTR flowPulseISR() {
  flowPulseCount++;
}
```

The system calculates the total volume in litres based on the calibrated constant of `323.0` pulses per litre. The interval flow rate is calculated based on the elapsed time between telemetry cycles.

### 3.4 Dual-Path Telemetry

The ESP32 transmits the telemetry JSON via two independent paths simultaneously:
1. **LoRa (433 MHz):** Transmits to a secondary ESP32 receiver for long-range redundancy.
2. **Wi-Fi/MQTT:** Publishes to a local Mosquitto broker (for low-latency dashboard integration) and AWS IoT Core (for cloud persistence).

The JSON payload follows a standardized structure:
```json
{
  "station_id": "S01",
  "packet": 18,
  "water_level_cm": 19.5,
  "distance_cm": 20.4,
  "rain_raw": 4095,
  "rain_status": "DRY",
  "flow_rate_l_min": 0.00,
  "flow_total_l": 2.89
}
```

### 3.5 Rate of Rise (RoR) Intelligence

The Python backend subscribes to the MQTT stream and calculates the Rate of Rise using a sliding time window (configured to 30 seconds for prototyping). It determines how fast the water level is changing.

```python
elapsed_minutes = elapsed_seconds / 60.0
level_change = current_level - oldest_level
ror = level_change / elapsed_minutes
```

The trend is classified as:
- `RISING`: RoR > 0.1 cm/min
- `FALLING`: RoR < -0.1 cm/min
- `STABLE`: Otherwise

### 3.6 Automated Alert Engine

The backend continuously evaluates the current sensor state and assigns a severity level:
- **CRITICAL:** Water Level > 18 cm OR RoR > 0.5 cm/min
- **WARNING:** Water Level > 10 cm OR Rain Status = WET
- **SAFE:** All other conditions

This alert state is exposed via a REST API to the dashboard.

## 4. API Endpoints

The backend provides the following API endpoints (built with FastAPI):

| Endpoint | Description |
|---|---|
| `GET /api/latest` | Retrieves the full sensor data payload along with the calculated RoR. |
| `GET /api/sensor` | Returns a flattened JSON payload compatible with the external dashboard. |
| `GET /api/alert` | Returns the current Alert State (severity, title, message). |
| `GET /api/health` | Health check endpoint to verify backend status. |

## 5. Data Handling

The system uses the `paho-mqtt` client to subscribe to the topic `flood/v1/stations/S01/telemetry`.

Data is processed in the `on_message` callback. Water level history is maintained in a Python `deque` for the RoR calculation. The backend maintains a global state (`latest_sensor_data`, `latest_ror_data`, `latest_alert`) which is served directly to the API endpoints, ensuring low-latency responses.

CORS (Cross-Origin Resource Sharing) middleware is enabled to allow the dashboard (running on a different laptop in the same LAN) to fetch data without browser security blocks.

## 6. System Workflow

1. ESP32 #1 reads water level, rain status, and flow pulses.
2. The data is packaged into a JSON payload.
3. The payload is transmitted via LoRa (to ESP32 #2) and Wi-Fi/MQTT (to the Mosquitto broker).
4. The Python backend receives the MQTT message and updates the global state.
5. The backend calculates the Rate of Rise (RoR) and determines the Alert State.
6. The dashboard fetches data from `/api/sensor` and `/api/alert` to update the UI.

## 7. Current Limitations

- The rain sensor is a wetness proxy, not a calibrated millimeter rain gauge.
- The flow sensor measures water passing through a specific pipe setup, not open-channel river discharge.
- The 30-second RoR window is a prototype demonstration value and is sensitive to minor sensor noise.
- AWS IoT Core connectivity requires NTP time synchronization and valid certificates, which may occasionally fail in unstable network conditions (the system falls back gracefully to local MQTT).
- The 915 MHz antennas currently in use are mismatched for the 433 MHz radio module and are only suitable for short-range testing.

## 8. Future Improvements

- Replace the 30-second RoR window with a longer window (e.g., 5 minutes) and implement median filtering.
- Perform formal field calibration for all sensors across multiple known depths and flow rates.
- Replace the 915 MHz antennas with proper 433 MHz antennas and conduct range testing.
- Integrate AWS DynamoDB for long-term data persistence and historical analysis.
- Add email/SMS notifications triggered by CRITICAL alert states.
- Expand the system to support multiple stations (S01, S02, S03) with unique MQTT topics.

## 9. Conclusion

Component 1 establishes a robust end-to-end pipeline for environmental sensing, wireless communication, and real-time flood intelligence. By combining an ESP32 sensor station, dual-path telemetry, and a Python-based Rate of Rise engine, it provides a reliable foundation for the broader flood forecasting and GIS visualization system.

Further field testing and calibration are required to transition the prototype into a deployment-ready solution.
```


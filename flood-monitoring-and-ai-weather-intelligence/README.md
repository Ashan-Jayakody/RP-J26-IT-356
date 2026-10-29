# Component 1: Flood Monitoring and AI Weather  Intelligence

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

# Flood Monitoring & Intelligence Node

## Overview
The **Flood Monitoring & Intelligence Node** is the foundational edge-computing and data-acquisition component of the flood forecasting system. 

This component is responsible for real-time environmental data acquisition using physical sensors, robust wireless telemetry, and local intelligence generation. It integrates an ESP32-based sensor station that measures water level, rainfall/wetness, and pipe flow. The data is processed on the edge, structured as JSON, and transmitted via a **dual-path communication** method (LoRa and Wi-Fi/MQTT). 

The data is then ingested by a Python backend which calculates the **Rate of Rise (RoR)** to detect sudden water level increases and exposes real-time alert states to the visualization dashboard via a REST API.

---

## Key Objectives
- **Multi-Sensor Edge Acquisition:** Continuously monitor water level (JSN-SR04T), rainfall/wetness (LM393), and water flow (YF-S201) using an ESP32 microcontroller.
- **Robust Wireless Telemetry:** Transmit structured JSON telemetry using point-to-point LoRa (433 MHz) for long-range redundancy and Wi-Fi/MQTT for low-latency local integration.
- **Edge Data Quality & Calibration:** Implement auto-calibration for the ultrasonic sensor (using ESP32 NVS/Preferences) and apply digital filtering to eliminate sensor noise and false triggers.
- **Temporal Intelligence (Rate of Rise):** Process incoming data in the Python backend to calculate the speed of water level changes, providing early warnings before critical thresholds are breached.

---

## Architecture & Data Flow
```text
[JSN-SR04T / LM393 / YF-S201 Sensors]
                 │
                 ▼
       [ESP32 #1 (Sensor Node)] ──► [ESP32 #2 (LoRa Receiver)]
                 │
                 ├─► LoRa (433 MHz)
                 │
                 └─► Wi-Fi / MQTT (Dual: AWS IoT & Local Mosquitto)
                                  │
                                  ▼
                     [Python Backend & RoR Engine]
                                  │
                                  ▼
                     [FastAPI Server (REST Endpoints)]
                                  │
                                  ▼
                    [HTML/JS Emergency Dashboard]

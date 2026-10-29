# Flood Monitoring & Intelligence System
### Multi-Point Water Level, Rainfall & Flow Forecasting for the Kelani River Basin

---

## 1. Overview

This project is an **integrated IoT-based flood monitoring and forecasting system** designed for the Kelani River basin. It combines real-time edge-sensing hardware, dual-path wireless telemetry, a Python intelligence backend, a machine-learning-driven forecasting engine, and a GIS-based visual dashboard.

The system is composed of **three tightly integrated components**:

| Component | Purpose | Owner |
| :--- | :--- | :--- |
| **Component 1** | Edge Sensing Node & Backend Intelligence (Rate of Rise) | Hardware / Backend |
| **Component 2** | Interactive Emergency Dashboard (HTML/JS) | Frontend |
| **Component 3** | Flow-Rate Forecasting & GIS Risk Mapping | ML / GIS |

---

## 2. System Architecture

```text
┌───────────────────────────────────────────────────────────────────┐
│                     PHYSICAL ENVIRONMENT                          │
│  [JSN-SR04T]  [LM393]  [YF-S201]                                  │
│  (Water Level) (Rain)   (Flow)                                    │
└──────────────────┬────────────────────────────────────────────────┘
                   │
                   ▼
        ┌───────────────────────┐
        │    ESP32 #1 (S01)     │ ◄── Auto-Calibration + Filtering
        │   Sensor Station      │
        └──────────┬────────────┘
                   │
        ┌──────────┴───────────┐
        ▼                      ▼
   [LoRa 433MHz]         [Wi-Fi/MQTT]
        │                 (AWS + Local)
        ▼                      │
   ┌──────────┐                │
   │ ESP32 #2 │                ▼
   │ Receiver │      ┌─────────────────────────┐
   └──────────┘      │  Python Intelligence    │
                     │  Backend (FastAPI)      │
                     │  • Rate of Rise Engine  │
                     │  • Alert State Manager  │
                     │  • ML Forecast Engine   │
                     │  • GIS Risk Mapper      │
                     └──────────┬──────────────┘
                                │
                                ▼
                     ┌─────────────────────────┐
                     │  Emergency Dashboard    │
                     │  (HTML/JS/Leaflet/Chart)│
                     └─────────────────────────┘

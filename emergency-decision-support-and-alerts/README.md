# 🌊 KelaniFlood: Emergency Decision Support & Alert Dissemination



## 📖 Overview

The **Emergency Decision Support and Alert Dissemination** component acts as the critical "last-mile" bridge between predictive flood models (Components 1, 2, and 3) and actionable guidance for civil protection. 

It ingests flood-risk information and the user's real-time GPS location to generate location-based alerts, recommend safe shelters, and facilitate emergency help requests between affected citizens and responders.

---

## 🚀 Key Implemented Functions (PP1 Prototype)

### 1. Location-Based Flood Alert Engine (`src/alert_engine.py`)
- **Geo-Spatial Analysis:** Evaluates the user's GPS coordinates against flood risk polygons using `Shapely`.
- **Accurate Distance:** Converts Latitude/Longitude to UTM Zone 44N (meters) using `PyProj` for precise distance calculations.
- **Severity Classification:** Generates standard alert levels based on proximity and risk:
  - 🔴 **CRITICAL** (Inside a High-Risk Zone)
  - 🟠 **WARNING** (Near a High-Risk Zone)
  - 🟢 **SAFE** (Outside all risk zones)

### 2. Shelter & Safe Route Recommendation (`src/shelter_recommender.py`)
- **Smart Filtering:** Automatically skips shelters that are full (`Capacity <= Occupied`) or located inside active flood zones.
- **Nearest Shelter Logic:** Ranks available shelters by distance and Estimated Time of Arrival (ETA).
- **Path Risk Assessment:** Checks if the direct path to the shelter crosses a flood zone and warns the user accordingly.
- **Interactive Map:** Visualizes the user's location and the recommended shelter using Leaflet.js.

### 3. Emergency Help Request & Responder Dashboard
- **Help Seekers:** Can submit requests with GPS location, urgency level (High/Medium/Low), and specific needs (Rescue, Food, Medicine, etc.).
- **Responder View:** A dedicated dashboard where authorities can filter incoming requests by urgency, view details, and accept requests for dispatch.

---

## 🛠️ Technology Stack (Implemented)

| Layer | Technologies Used |
| :--- | :--- |
| **Backend Logic** | Python 3.11, FastAPI, Pydantic |
| **Geo-Spatial Processing** | Shapely, PyProj |
| **Frontend & UI** | HTML5, CSS3, Vanilla JavaScript |
| **Mapping & GIS** | Leaflet.js, OpenStreetMap (OSM) |
| **Data Formats** | JSON, GeoJSON |
| **Testing** | Pytest (11 Unit Tests) |

---

## 📂 Project Structure

```text
floodguard-kelani/
│
├── src/
│   ├── __init__.py
│   ├── alert_engine.py          # Function 1: Alert Logic
│   ├── shelter_recommender.py   # Function 2: Shelter Logic
│   └── api.py                   # FastAPI Endpoints
│
├── data/
│   ├── flood_risk_zones.json    # Mock GeoJSON Flood Zones
│   └── shelter_locations.json   # Mock Shelter Data
│
├── tests/
│   ├── test_alert_engine.py     # 5 Tests
│   ├── test_api.py              # 3 Tests
│   └── test_shelter_recommender.py # 3 Tests
│
├── web/
│   └── index.html               # Web Dashboard (Leaflet + UI)
│
├── requirements.txt
└── README.md



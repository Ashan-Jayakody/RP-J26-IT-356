# Emergency Decision Support and Alerts

## Overview
The **Emergency Decision Support and Alerts** component bridges predictive modeling with actionable civil protection and disaster response. It continuously evaluates flood hazard levels, calculates localized vulnerability indices, generates multi-tiered public and official alerts, and offers intelligent spatial decision support for evacuation routing, shelter activation, and emergency resource staging.

---

## Key Objectives
- **Dynamic Flood Risk Indexing**: Synthesize forecasted water levels, precipitation anomalies, soil saturation, and local terrain vulnerability into standardized multi-tier risk scores (Normal, Advisory, Watch, Warning, Severe Emergency).
- **Geo-Targeted Alert Dissemination**: Dispatch automated, localized alert notifications to disaster management authorities, first responders, and community members via SMS gateways, push notifications, email, and webhooks.
- **Evacuation Routing & Road Inundation Analysis**: Intersect predicted flood extents with road network graphs (OSM) to assess network cut-offs and compute safe, accessible evacuation corridors.
- **Situational Awareness Dashboard**: Provide an interactive GIS-enabled situational control panel for emergency management personnel, displaying real-time sensor telemetries, danger zones, and logistical resource allocations.

---

## Architecture & Alerting Workflow
```
[Streamflow & Weather Predictions] ──┐
[Demographic & Infrastructure GIS] ──┼─► [Risk Engine & Decision Core] ──► [Multi-Channel Notification Gateway]
[Dam Release Downstream Alerts]    ──┘     (Severity Scoring & Routing)        (SMS / Push / Webhooks / Dashboards)
```

---

## Directory Structure
```text
emergency-decision-support-and-alerts/
├── data/                  # Population rasters, critical infrastructure, road networks
├── src/
│   ├── risk_assessment/   # Hazard scoring algorithms and multi-factor vulnerability indexers
│   ├── evacuation/        # Graph-based routing, network cut-off simulations, shelter allocation
│   ├── notification/      # SMS gateways (Twilio/local telco), Push notification handlers, email service
│   ├── services/          # Real-time event broker, background task consumers
│   └── api/               # REST/WebSocket endpoints feeding frontend dashboard
├── dashboard/             # Web-based situational awareness interface (React / MapLibre / Leaflet)
├── tests/                 # Unit tests for threshold evaluations and notification dispatches
├── requirements.txt       # Backend dependencies
└── README.md              # Component documentation
```

---

## Technology Stack
- **Backend & Logic**: Python 3.10+, FastAPI, Celery, Redis, SQLAlchemy / PostgreSQL (PostGIS)
- **GIS & Network Analysis**: OSMnx, NetworkX, GeoPandas, Shapely
- **Frontend / Visualization**: React / TypeScript, MapLibre GL / Leaflet, Tailwind CSS
- **Messaging & Notifications**: Twilio API, Firebase Cloud Messaging (FCM), WebSocket protocols

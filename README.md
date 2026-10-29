# RP-J26-IT-356: AI-Driven Flood Forecasting & Disaster Decision Support System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

## Project Overview
This research project delivers an end-to-end, integrated framework for flood prediction, meteorological intelligence, hydraulic simulation, and automated emergency decision support. By synthesizing multi-source satellite and IoT sensor feeds with physics-informed artificial intelligence models, the platform equips hydrologists, dam operators, and disaster relief authorities with proactive early warning capabilities.

---

## Core Research Components

The system is organized into four modular, interconnected research components:

| Component | Directory | Focus Area |
| :--- | :--- | :--- |
| **Component 1** | [`flood-monitoring-and-ai-weather-intelligence/`](./flood-monitoring-and-ai-weather-intelligence/) | Real-time weather observation ingestion, radar/satellite nowcasting, and extreme precipitation AI models. |
| **Component 2** | [`flow-rate-based-flood-forecasting/`](./flow-rate-based-flood-forecasting/) | Catchment runoff modeling, streamflow stage/discharge predictions, and river network hydrological simulations. |
| **Component 3** | [`emergency-decision-support-and-alerts/`](./emergency-decision-support-and-alerts/) | Multi-factor flood risk indexing, automated multi-channel emergency alerts, and evacuation corridor optimization. |
| **Component 4** | [`reservoir-release-downstream-impact/`](./reservoir-release-downstream-impact/) | Reservoir storage mass-balance, controlled spillway release optimization, and downstream hydrodynamic inundation mapping. |

---

## Integrated Architecture & Data Pipeline

```
[Satellite, Radar & IoT Sensors]
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 1. Flood Monitoring & AI Weather Intelligence          │
│    (Precipitation Nowcasting & Weather Telemetry)      │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
               ▼                          │
┌──────────────────────────────────────┐  │
│ 2. Flow Rate Based Flood Forecasting │  │
│    (Streamflow & Discharge Forecast) │  │
└──────────────┬───────────────────────┘  │
               │                          │
               ▼                          ▼
┌────────────────────────────────────────────────────────┐
│ 4. Reservoir Release Downstream Impact                 │
│    (Storage Optimization & Wave Inundation Routing)    │
└──────────────┬─────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────┐
│ 3. Emergency Decision Support & Alerts                 │
│    (Risk Indexing, Public Alerts & Evacuation DSS)     │
└────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```text
RP-J26-IT-356/
├── emergency-decision-support-and-alerts/          # Component 3: Risk assessment, alerts, and evacuation routing
├── flood-monitoring-and-ai-weather-intelligence/  # Component 1: Meteorological ingestion and AI nowcasting
├── flow-rate-based-flood-forecasting/              # Component 2: Hydrologic and streamflow discharge models
├── reservoir-release-downstream-impact/            # Component 4: Dam operations and hydraulic routing
└── README.md                                       # Main project overview and architectural documentation
```

---

## Component Details & Documentation
For in-depth documentation, dataset instructions, and module-specific setups, refer to the individual component guides:
- [Flood Monitoring & AI Weather Intelligence Guide](./flood-monitoring-and-ai-weather-intelligence/README.md)
- [Flow Rate Based Flood Forecasting Guide](./flow-rate-based-flood-forecasting/README.md)
- [Emergency Decision Support & Alerts Guide](./emergency-decision-support-and-alerts/README.md)
- [Reservoir Release Downstream Impact Guide](./reservoir-release-downstream-impact/README.md)

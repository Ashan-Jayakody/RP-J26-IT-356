# Flow Rate Based Flood Forecasting

## Overview
The **Flow Rate Based Flood Forecasting** component is responsible for modeling river hydraulics, basin discharge dynamics, and water surface elevations across hydrological networks. By combining physics-informed hydrologic principles (rainfall-runoff processes, channel routing) with temporal machine learning models (LSTM, GRU, Temporal Convolutional Networks, Graph Neural Networks), this module predicts future river discharge and water levels at critical gauge stations with extended lead times.

---

## Key Objectives
- **Multi-Horizon Streamflow Prediction**: Forecast river discharge (\(m^3/s\)) and stage height (\(m\)) at critical river gauge locations across multiple forecast horizons (6, 12, 24, and 48 hours).
- **Hybrid Hydrological Modeling**: Bridge classical hydrological modeling approaches (e.g., HEC-HMS, conceptual unit hydrographs) with deep recurrent sequence models to effectively capture non-linear catchment retention and baseflow dynamics.
- **Dynamic Stage-Discharge Calibration**: Account for hysteresis, riverbed morphology variations, and backwater effects through adaptive rating curve formulations and continuous sensor recalibration.
- **Peak Crest & Hydrograph Characterization**: Estimate peak discharge magnitude, time-to-peak (lag time), and hydrograph volume to assess downstream overflow probabilities.

---

## Architecture & Modeling Pipeline
```
[Precipitation Ingestion & Forecasts] ──┐
[Upstream River Level & Flow Sensors]  ──┼─► [Catchment Hydrology Engine] ──► [Streamflow Forecast Models] ──► [River Discharge & Stage API]
[Soil Moisture & Evapotranspiration]   ──┘     (Soil Runoff / Infiltration)       (LSTM / GRU / Spatio-Temporal)     (Fed to Decision Support & Dams)
```

---

## Directory Structure
```text
flow-rate-based-flood-forecasting/
├── data/                  # Gauge time-series data, rating curves, catchment shapefiles
├── notebooks/             # Model training, hyperparameter tuning, validation notebooks
├── src/
│   ├── calibration/       # Sensor calibration and stage-discharge curve modeling
│   ├── features/          # Hydrological lag features, rolling statistics, baseflow separation
│   ├── models/            # Recurrent models (LSTM, BiLSTM, GRU), GNNs, baseline statistical models
│   ├── pipeline/          # End-to-end streamflow training and inference orchestrator
│   └── evaluation/        # Hydrological performance metrics (NSE, KGE, RMSE, PBIAS)
├── tests/                 # Unit tests for hydrological calculations and model inference
├── requirements.txt       # Python dependencies
└── README.md              # Component documentation
```

---

## Technology Stack
- **Languages & Frameworks**: Python 3.10+, PyTorch / PyTorch Geometric
- **Hydrological & Scientific Libraries**: Hydroeval, Scipy, NumPy, Pandas, SymPy
- **Data Engineering**: Dask, Polars, Statsmodels, Scikit-learn
- **Evaluation Standards**: Nash-Sutcliffe Efficiency (NSE), Kling-Gupta Efficiency (KGE), Percent Bias (PBIAS)

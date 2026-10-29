# Component 3: Flow Rate-Based Flood Forecasting and GIS Risk Mapping

## 1. Introduction

Component 3 focuses on flow rate-based flood forecasting and GIS risk mapping for the Kelani River basin. It uses water-level readings, rainfall information, estimated flow rates, and a trained machine learning model to generate flood-risk forecasts.

The component provides a web interface to display forecast results, water-level trends, flow-rate information, and geographical risk areas.

## 2. Technologies Used

- Python
- FastAPI
- Scikit-learn
- Joblib
- JavaScript
- Chart.js
- Leaflet.js
- OpenStreetMap
- HTML and CSS
- JSON

## 3. Main Features

### 3.1 Flood Forecasting

The system generates a five-day flood-risk forecast using a trained Logistic Regression model.

The model is loaded from `flood_model_web.joblib`, which contains the trained model, scaler, and feature information.

The prediction is performed using:

```python
prob = float(model.predict_proba(scaler.transform(X_live))[:, 1][0])
```

The scaler transforms the input features before the model calculates the flood probability.

### 3.2 Input Features

The forecasting model uses the following features:

- Current water level
- Daily water-level change
- Current rainfall
- Three-day accumulated rainfall
- Seven-day accumulated rainfall
- Estimated flow rate
- Flow-rate change

These features are prepared before being passed to the trained model.

### 3.3 Flow Rate Estimation

The system estimates flow rate using a power-law relationship between water level and flow rate.

The formula is:

\[
Q = a \times (H-H_0)^b
\]

Where:

- `Q` is the estimated flow rate.
- `H` is the measured water level.
- `H₀` is the reference water level.
- `a` and `b` are station-specific parameters.

If the water level is less than or equal to the reference level, the estimated flow rate is set to zero.

The estimates are used as part of the forecasting process.

### 3.4 Flood Risk Classification

The system classifies flood risk into three levels:

- **LOW:** The water level is below the defined warning thresholds, and the predicted flood probability is below the high-risk threshold.
- **MEDIUM:** The water level reaches at least 80% of the defined alert level but remains below the alert threshold, with a low predicted probability.
- **HIGH:** The predicted flood probability is at least 0.5, or the water level reaches or exceeds the defined alert threshold.

The configured alert levels are:

- Hanwella: 7.0 metres
- Glencourse: 15.0 metres

These thresholds are used by the prototype's risk-classification logic.

### 3.5 Five-Day Forecast

The API generates forecasts for the next five days. The forecast response includes predicted risk levels, flood probabilities, water levels, and flow-rate information.

The current prototype projects future water levels using a fixed daily increase of 5% and assumes 15 mm of rainfall for the forecast period. These are simplified assumptions rather than forecasts from a live weather service.

### 3.6 Web Dashboard

The frontend displays the forecasting results through a web interface.

The dashboard includes:

- Current flood-risk level
- Daily flood probabilities
- Water-level information for Hanwella and Glencourse
- S01 sensor water-level information
- Estimated flow-rate information
- A five-day forecast table
- Water-level trend charts

Chart.js is used to display the water-level trends.

### 3.7 GIS Risk Mapping

Leaflet.js and OpenStreetMap are used to display geographical risk information on an interactive map.

The map displays risk indicators for the following areas:

- Hanwella
- Kaduwela
- Kolonnawa
- Biyagama
- Kelaniya
- Wattala

The areas are displayed using different colours according to their assigned risk levels.

The current implementation uses predefined area groups to assign risk levels. Therefore, the map represents prototype risk visualization and does not independently predict flooding for each geographical area.

## 4. API Endpoints

The component provides the following API endpoints:

| Endpoint | Description |
|---|---|
| `GET /api/forecast/timeline` | Retrieves the stored forecast timeline. |
| `GET /api/forecast/live` | Generates and returns the five-day flood-risk forecast. |
| `GET /api/forecast/sensor-status` | Returns sensor readings and effective station data. |
| `GET /api/forecast/gis` | Returns geographical areas and their assigned risk levels. |

## 5. Data Handling

The system uses available sensor readings when they are provided through the shared application state.

For stations without live readings, predefined fallback values are used to prepare the forecasting inputs.

The current implementation maps the S01 sensor reading into the forecasting process. Other station values may use configured fallback data.

Rainfall status values are converted into numerical rainfall estimates before the features are prepared.

## 6. System Workflow

1. Obtain available sensor readings and rainfall information.
2. Prepare current water-level, rainfall, and flow-rate features.
3. Apply the trained model and calculate flood probability.
4. Classify the flood risk as LOW, MEDIUM, or HIGH.
5. Generate the five-day forecast response.
6. Display forecast information and water-level trends on the dashboard.
7. Retrieve geographical risk information and display it on the GIS map.

## 7. Current Limitations

- Live readings are not available for every forecasting station.
- Fallback values are used when station readings are unavailable.
- Future water levels and rainfall are generated using simplified assumptions.
- Flow-rate estimates depend on the configured station parameters.
- GIS risk levels are assigned using predefined area groups rather than separate predictions for each area.
- The forecast should be validated against real flood events and additional test data before operational use.
- Live weather forecasts and verified reservoir-release data are not currently integrated into this forecasting workflow.

## 8. Future Improvements

- Integrate live readings from additional river monitoring stations.
- Use real weather forecasts to improve future rainfall inputs.
- Calibrate flow-rate estimation parameters using verified hydrological data.
- Evaluate model performance using additional historical flood events.
- Improve GIS mapping using validated flood-risk boundaries and location-specific data.
- Integrate verified reservoir-release information when a reliable data source becomes available.

## 9. Conclusion

Component 3 combines a trained Logistic Regression model, water-level and flow-rate features, a five-day forecast API, and GIS-based risk visualization. It provides a prototype for presenting flood-risk information in an accessible web interface.

Further testing, data validation, and integration with reliable real-time data sources are required to improve the accuracy and practical reliability of the system.

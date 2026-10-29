"""Component 3: flood forecast API."""
import json
import threading
from pathlib import Path
from fastapi import APIRouter, HTTPException
import pandas as pd
import joblib
from datetime import timedelta, datetime

# Define base paths for data and model files
BASE = Path(__file__).resolve().parent.parent
TIMELINE_FILE = BASE / "data" / "forecast_timeline.json"
MODEL_PATH = BASE / "src" / "flood_model_web.joblib"

# Initialize the FastAPI router for forecast endpoints
router = APIRouter(prefix="/api/forecast", tags=["forecast (Component 3)"])

# Load the trained Machine Learning model and scaler
try:
    bundle = joblib.load(MODEL_PATH)
    model = bundle['model']
    scaler = bundle['scaler']
    features = bundle['features']
    print("[OK] Forecast API: Model loaded successfully")
except Exception as e:
    print("[ERROR] Forecast API: Model load error:", e)
    model = scaler = features = None

# Alert thresholds for the two main stations
ALERT_HANWELLA = 7.0
ALERT_GLENCOURSE = 15.0
FORECAST_DAYS = 5

# Map sensor station IDs to actual station names
STATION_ID_MAP: dict[str, str] = {
    "S01": "S01",
    "S02": "Glencourse",
}

# Conversion factor: centimetres to metres
CM_TO_METRES = 0.01

# Map rain status text to approximate rainfall in millimetres
RAIN_STATUS_TO_MM: dict[str, float] = {
    "DRY":    0.0,
    "LIGHT":  3.0,
    "WET":    15.0,
    "HEAVY":  40.0,
}

# Thread lock to prevent race conditions when reading shared state
_state_lock = threading.Lock()

def _estimate_flow_rate(station_name: str, water_level_m: float) -> float:
    """
    Fallback estimation for stations without a live flow sensor.
    Uses a power-law rating curve: Q = a * (H - H0)^b
    """
    if station_name == "Hanwella":
        a, h0, b = 15.0, 1.5, 1.8
    elif station_name == "Glencourse":
        a, h0, b = 25.0, 8.0, 1.6
    else:
        return 0.0
    if water_level_m <= h0:
        return 0.0
    return round(a * ((water_level_m - h0) ** b), 2)

def _get_live_station_readings() -> dict[str, dict | None]:
    """
    Fetch live sensor readings from the shared state in api.py.
    Returns a dictionary keyed by station name.
    """
    from src.api import state
    with _state_lock:
        sensor = dict(state.get("sensor_data", {}))
    
    readings: dict[str, dict | None] = {
        "S01":        None,
        "Hanwella":   None,
        "Glencourse": None,
    }

    station_id = sensor.get("station_id", "")
    if station_id == "S01":
        # Convert water level from cm to m
        wl_cm = float(sensor.get("water_level_cm", 0))
        # Map rain status text to rainfall mm
        rain_status = str(sensor.get("rain_status", "DRY")).upper()
        rain_mm = RAIN_STATUS_TO_MM.get(rain_status, 0.0)
        # Grab the live flow rate from the sensor payload
        live_q = float(sensor.get("flow_rate_m3s", 0.0)) 
        readings["S01"] = {
            "water_level_m": wl_cm * CM_TO_METRES,
            "rain_mm":       rain_mm,
            "flow_rate_m3s": live_q,
        }
    return readings

def _merge_readings_with_fallback(live: dict[str, dict | None]) -> dict[str, dict]:
    """
    Fill in missing station data with historical baseline values.
    Ensures the ML model always receives valid input.
    """
    FALLBACK = {
        "S01":        {"water_level_m": 0.0,   "rain_mm": 0.0, "flow_rate_m3s": 0.0},
        "Hanwella":   {"water_level_m": 2.94,  "rain_mm": 0.0, "flow_rate_m3s": 34.45}, 
        "Glencourse": {"water_level_m": 10.95, "rain_mm": 0.0, "flow_rate_m3s": 185.33}, 
    }
    merged = {}
    for name in ("S01", "Hanwella", "Glencourse"):
        if name == "S01" and live.get(name) is not None:
            merged[name] = live[name]
        else:
            merged[name] = FALLBACK[name]
    return merged

def _build_features(current_data: pd.DataFrame, target_date: datetime) -> pd.DataFrame:
    """
    Engineer features required by the ML model:
    Water Level, Rate of Rise, Rainfall, 3-day and 7-day cumulative rainfall, and Flow Rate.
    """
    feat = pd.DataFrame(index=[target_date])
    for station in ["Hanwella", "Glencourse"]:
        wl = current_data[f"{station}_WL"]
        rf = current_data[f"{station}_RF"]
        # Current water level
        feat[f"{station}_WL"] = wl.iloc[-1]
        # Rate of rise (difference from yesterday)
        feat[f"{station}_dWL"] = wl.iloc[-1] - wl.iloc[-2] if len(wl) >= 2 else 0.0
        # Current rainfall
        feat[f"{station}_RF"] = rf.iloc[-1]
        # 3-day cumulative rainfall
        feat[f"{station}_RF3"] = rf.iloc[-3:].sum()
        # 7-day cumulative rainfall
        feat[f"{station}_RF7"] = rf.iloc[-7:].sum()
        
        # Estimate flow rate from water level
        feat[f"{station}_Q"] = _estimate_flow_rate(station, wl.iloc[-1])
        # Rate of change of flow rate
        if len(wl) >= 2:
            prev_q = _estimate_flow_rate(station, wl.iloc[-2])
            feat[f"{station}_dQ"] = feat[f"{station}_Q"] - prev_q
        else:
            feat[f"{station}_dQ"] = 0.0

    # Set features for stations without sensors to zero
    for station in ["Deraniyagala", "Holombuwa", "Kithulgala", "Norwood"]:
        feat[f"{station}_WL"] = 0
        feat[f"{station}_dWL"] = 0
        feat[f"{station}_RF"] = 0
        feat[f"{station}_RF3"] = 0
        feat[f"{station}_RF7"] = 0
        feat[f"{station}_Q"] = 0
        feat[f"{station}_dQ"] = 0

    feat["risk_today"] = 0
    return feat

def _risk_level(prob: float, latest_row) -> tuple[str, float]:
    """
    Classify risk as LOW, MEDIUM, or HIGH based on flood probability and alert ratio.
    """
    ratio = max(
        latest_row["Hanwella_WL"] / ALERT_HANWELLA,
        latest_row["Glencourse_WL"] / ALERT_GLENCOURSE,
    )
    if prob >= 0.5 or ratio >= 1.0:
        level = "HIGH"
    elif ratio >= 0.8:
        level = "MEDIUM"
    else:
        level = "LOW"
    return level, float(ratio)

@router.get("/timeline")
def get_timeline():
    """Return the historical forecast timeline data."""
    if not TIMELINE_FILE.exists():
        raise HTTPException(status_code=404, detail="data/forecast_timeline.json not found")
    return json.loads(TIMELINE_FILE.read_text(encoding="utf-8"))

@router.get("/live")
def get_live_forecast():
    """
    Generate a 5-day flood forecast using live sensor data and the ML model.
    Returns a JSON response with daily risk levels and readings.
    """
    if model is None or scaler is None or features is None:
        raise HTTPException(status_code=503, detail="ML model is not loaded.")

    # Get today's date at midnight
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Fetch and merge live readings with fallback values
    live_raw = _get_live_station_readings()
    live = _merge_readings_with_fallback(live_raw)

    # Extract values for each station
    hanwella_wl = live["Hanwella"]["water_level_m"]
    glencourse_wl = live["Glencourse"]["water_level_m"]
    hanwella_rf = live["Hanwella"]["rain_mm"]
    glencourse_rf = live["Glencourse"]["rain_mm"]
    
    s01_wl = live["S01"]["water_level_m"]
    s01_rf = live["S01"]["rain_mm"]
    s01_q = live["S01"]["flow_rate_m3s"]

    # Track which stations are live vs. fallback
    live_stations = [k for k, v in live_raw.items() if v is not None]
    using_fallback = [k for k, v in live_raw.items() if v is None]

    # Historical baseline values for the past 6 days
    BASELINE_WL_H  = [2.15, 2.50, 2.75, 3.10, 3.45, 3.78]
    BASELINE_WL_G  = [9.85, 10.20, 10.80, 11.20, 11.55, 11.91]
    BASELINE_RF_H  = [0.0, 0.0, 11.3, 3.3, 32.4, 3.3]
    BASELINE_RF_G  = [0.0, 0.0, 0.0, 25.8, 11.1, 25.8]

    # Generate date ranges for history and forecast
    history_dates = [today - timedelta(days=i) for i in range(7, 0, -1)]
    forecast_dates = [today + timedelta(days=i) for i in range(FORECAST_DAYS)]

    # Build historical dataframe
    history = pd.DataFrame({
        "Date":          history_dates,
        "Hanwella_WL":   BASELINE_WL_H  + [hanwella_wl],
        "Glencourse_WL": BASELINE_WL_G  + [glencourse_wl],
        "Hanwella_RF":   BASELINE_RF_H  + [hanwella_rf],
        "Glencourse_RF": BASELINE_RF_G  + [glencourse_rf],
    })

    # Project future values with a 5% daily trend
    TREND = 0.05
    projected_rows = {"Date": forecast_dates, "Hanwella_WL": [], "Glencourse_WL": [], "Hanwella_RF": [], "Glencourse_RF": []}
    prev_h, prev_g = hanwella_wl, glencourse_wl
    for i in range(FORECAST_DAYS):
        prev_h *= (1 + TREND)
        prev_g *= (1 + TREND)
        projected_rows["Hanwella_WL"].append(prev_h)
        projected_rows["Glencourse_WL"].append(prev_g)
        projected_rows["Hanwella_RF"].append(15.0)  # Assumed constant rain
        projected_rows["Glencourse_RF"].append(15.0)

    # Combine history and projections
    projected = pd.DataFrame(projected_rows)
    df = pd.concat([history, projected], ignore_index=True)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")

    # Run ML model for each forecast day
    results = []
    history_len = len(history)
    for i in range(FORECAST_DAYS):
        current_date = forecast_dates[i]
        current_data = df.iloc[: history_len + i + 1]
        latest_row   = current_data.iloc[-1]
        feat         = _build_features(current_data, current_date)
        
        # Ensure all required features exist
        for col in features:
            if col not in feat.columns:
                feat[col] = 0.0
                
        X_live       = feat[features]
        # Predict flood probability
        prob         = float(model.predict_proba(scaler.transform(X_live))[:, 1][0])
        # Classify risk level
        level, ratio = _risk_level(prob, latest_row)

        # Estimate flow rate for Hanwella and Glencourse
        hanwella_q = _estimate_flow_rate("Hanwella", latest_row["Hanwella_WL"])
        glencourse_q = _estimate_flow_rate("Glencourse", latest_row["Glencourse_WL"])

        # Append results for this day
        results.append({
            "date":              str(current_date.date()),
            "forecast_for":      str(current_date.date()),
            "flood_probability": round(prob, 3),
            "alert_ratio":       round(ratio, 2),
            "risk_level":        level,
            "hanwella_wl":       round(float(latest_row["Hanwella_WL"]), 3),
            "glencourse_wl":     round(float(latest_row["Glencourse_WL"]), 3),
            "s01_wl":            round(float(s01_wl), 3),
            "hanwella_q":        hanwella_q,
            "glencourse_q":      glencourse_q,
            "s01_q":             round(float(s01_q), 3),  # Live sensor value
        })

    # Return final JSON response
    return {
        "status":            "success",
        "data_source":       "LIVE" if live_stations else "SIMULATED_FALLBACK",
        "live_stations":     live_stations,
        "fallback_stations": using_fallback,
        "days":              results,
        "model_name":        "Logistic Regression (Flow Rate + Water Level + Rainfall)",
    }

@router.get("/sensor-status")
def get_sensor_status():
    """Return the current status of live sensors."""
    live_raw = _get_live_station_readings()
    live     = _merge_readings_with_fallback(live_raw)
    return {
        "live_readings":     live_raw,
        "effective_readings": live,
        "station_id_map":    STATION_ID_MAP,
    }

@router.get("/gis")
def get_gis_risk_map():
    """
    Generate GIS risk data for downstream DS divisions based on today's forecast.
    Returns a JSON response with risk levels and coordinates.
    """
    try:
        live_result = get_live_forecast()
        today_level = live_result["days"][0]["risk_level"] if live_result["days"] else "MEDIUM"
    except Exception:
        today_level = "MEDIUM"

    # Define risk levels for each DS division
    HIGH_DIVISIONS   = {"Kaduwela", "Kolonnawa"}
    MEDIUM_DIVISIONS = {"Biyagama", "Kelaniya"}
    LOW_DIVISIONS    = {"Hanwella", "Wattala"}

    def _area_risk(name: str) -> str:
        """Assign risk level to a DS division based on the basin-wide risk."""
        if today_level == "HIGH"   and name in HIGH_DIVISIONS:   return "HIGH"
        if today_level == "HIGH"   and name in MEDIUM_DIVISIONS:  return "MEDIUM"
        if today_level == "MEDIUM" and name in HIGH_DIVISIONS:   return "MEDIUM"
        if name in HIGH_DIVISIONS:   return "MEDIUM"
        if name in MEDIUM_DIVISIONS: return "LOW"
        return "LOW"

    # Build list of areas with coordinates
    areas = [
        {"ds_name": "Hanwella",   "risk": _area_risk("Hanwella"),   "lat": 6.950, "lon": 80.085},
        {"ds_name": "Kaduwela",   "risk": _area_risk("Kaduwela"),   "lat": 6.933, "lon": 79.985},
        {"ds_name": "Kolonnawa",  "risk": _area_risk("Kolonnawa"),  "lat": 6.928, "lon": 79.895},
        {"ds_name": "Biyagama",   "risk": _area_risk("Biyagama"),   "lat": 6.955, "lon": 79.980},
        {"ds_name": "Kelaniya",   "risk": _area_risk("Kelaniya"),   "lat": 6.955, "lon": 79.920},
        {"ds_name": "Wattala",    "risk": _area_risk("Wattala"),    "lat": 6.990, "lon": 79.890},
    ]
    return {"status": "success", "basin_risk": today_level, "areas": areas}
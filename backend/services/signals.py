from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from backend.db.influx import get_influx_client
from backend.config import settings

APP_TZ = ZoneInfo(settings.app_timezone)

SIGNALS_CONFIG = {
    "tank_pressure": {
        "field": "CU.ORI.MesValTankPressPourcent",
        "label": "Niveau Reservoir (%)",
        "unit": "%",
        "agg": "MEAN",
        "thresholds": {"low": 94, "critical": 90},
    },
    "soc_batt1": {
        "field": "BBMS1.MBMU.ORI.SOC",
        "label": "SOC Batterie 1 (%)",
        "unit": "%",
        "agg": "MEAN",
    },
    "soc_batt2": {
        "field": "BBMS2.MBMU.ORI.SOC",
        "label": "SOC Batterie 2 (%)",
        "unit": "%",
        "agg": "MEAN",
    },
    "plant_run_mode": {
        "field": "Gen_OLI_PlantRunMode",
        "label": "Mode de regulation",
        "unit": "",
        "agg": "LAST",
    },
    "ev_power": {
        "field": "Gen_ORI_EVPMes",
        "label": "Puissance EV (kW)",
        "unit": "kW",
        "agg": "MEAN",
    },
    "soc_state": {
        "field": "SocMgt_OLI_SocMgtState",
        "label": "Etat SOC Management",
        "unit": "",
        "agg": "LAST",
    },
    "aux_power": {
        "field": "Gen_ORI_Paux",
        "label": "Puissance Auxiliaire (kW)",
        "unit": "kW",
        "agg": "MEAN",
    },
    "temp_water": {
        "field": "CU.ORI.MesValTempColdwaterIn",
        "label": "Temperature Eau Entree (°C)",
        "unit": "°C",
        "agg": "MEAN",
        "thresholds": {"warning": 28, "critical": 30},
    },
    "grid_power": {
        "field": "Gen_R_ResPMes",
        "label": "Puissance Reseau (kW)",
        "unit": "kW",
        "agg": "MEAN",
    },
}


def get_config() -> dict:
    return {
        "signals": {
            k: {"label": v["label"], "unit": v["unit"], "thresholds": v.get("thresholds")}
            for k, v in SIGNALS_CONFIG.items()
        }
    }


def get_signals_data(project: str, date_str: str, signal_keys: list[str]) -> dict:
    d = datetime.fromisoformat(date_str).date()
    start = datetime.combine(d, dtime(0, 0), tzinfo=APP_TZ)
    end = start + timedelta(days=1)
    start_utc = start.astimezone(ZoneInfo("UTC"))
    end_utc = end.astimezone(ZoneInfo("UTC"))

    # Build query
    selects = []
    for key in signal_keys:
        cfg = SIGNALS_CONFIG.get(key)
        if not cfg:
            continue
        agg = cfg["agg"]
        field = cfg["field"]
        selects.append(f'{agg}("{field}") AS "{field}"')

    if not selects:
        return {"timeseries": [], "statistics": {}, "alarms": []}

    q = f"""
      SELECT {", ".join(selects)}
      FROM "elto1sec_box"
      WHERE "project" = '{project}'
        AND time >= '{start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        AND time  < '{end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
      GROUP BY time(1m) ORDER BY time ASC
    """
    client = get_influx_client()
    res = client.query(q)
    pts = list(res.get_points()) if res else []

    if not pts:
        return {"timeseries": [], "statistics": {}, "alarms": []}

    df = pd.DataFrame(pts)
    t_utc = pd.to_datetime(df["time"], utc=True)
    df["time"] = t_utc.dt.tz_convert(APP_TZ).dt.tz_localize(None)

    # Build timeseries
    timeseries = []
    for _, row in df.iterrows():
        point = {"time": row["time"].strftime("%Y-%m-%d %H:%M")}
        for key in signal_keys:
            cfg = SIGNALS_CONFIG.get(key)
            if not cfg:
                continue
            field = cfg["field"]
            v = row.get(field)
            if pd.notna(v):
                point[key] = round(float(v), 2)
            else:
                point[key] = None
        timeseries.append(point)

    # Statistics
    statistics = {}
    for key in signal_keys:
        cfg = SIGNALS_CONFIG.get(key)
        if not cfg:
            continue
        field = cfg["field"]
        if field in df.columns:
            s = pd.to_numeric(df[field], errors="coerce").dropna()
            if not s.empty:
                use_abs = key in ("ev_power", "aux_power", "grid_power")
                vals = s.abs() if use_abs else s
                statistics[key] = {
                    "mean": round(float(vals.mean()), 2),
                    "min": round(float(vals.min()), 2),
                    "max": round(float(vals.max()), 2),
                }

    # Alarms
    alarms = _check_alarms(df, signal_keys)

    return {"timeseries": timeseries, "statistics": statistics, "alarms": alarms}


def _check_alarms(df: pd.DataFrame, signal_keys: list[str]) -> list[dict]:
    alarms = []

    # Water level < 94%
    if "tank_pressure" in signal_keys:
        field = SIGNALS_CONFIG["tank_pressure"]["field"]
        if field in df.columns:
            s = pd.to_numeric(df[field], errors="coerce")
            below = s < 94
            if below.any():
                min_val = float(s[below].min())
                min_idx = s[below].idxmin()
                min_time = df.loc[min_idx, "time"].strftime("%H:%M")
                alarms.append({
                    "type": "warning",
                    "message": f"Niveau d'eau bas: min {min_val:.1f}% a {min_time}",
                })

    # SOC imbalance > 8%
    if "soc_batt1" in signal_keys and "soc_batt2" in signal_keys:
        f1 = SIGNALS_CONFIG["soc_batt1"]["field"]
        f2 = SIGNALS_CONFIG["soc_batt2"]["field"]
        if f1 in df.columns and f2 in df.columns:
            s1 = pd.to_numeric(df[f1], errors="coerce")
            s2 = pd.to_numeric(df[f2], errors="coerce")
            diff = (s1 - s2).abs()
            above = diff > 8
            if above.any():
                max_diff = float(diff[above].max())
                max_idx = diff[above].idxmax()
                max_time = df.loc[max_idx, "time"].strftime("%H:%M")
                alarms.append({
                    "type": "warning",
                    "message": f"Desequilibre batteries: max {max_diff:.1f}% a {max_time}",
                })

    # Temperature > 28°C
    if "temp_water" in signal_keys:
        field = SIGNALS_CONFIG["temp_water"]["field"]
        if field in df.columns:
            s = pd.to_numeric(df[field], errors="coerce")
            above = s > 28
            if above.any():
                max_val = float(s[above].max())
                max_idx = s[above].idxmax()
                max_time = df.loc[max_idx, "time"].strftime("%H:%M")
                alarms.append({
                    "type": "error",
                    "message": f"Temperature elevee: max {max_val:.1f}°C a {max_time}",
                })

    return alarms

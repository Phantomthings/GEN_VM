from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo

from backend.db.mysql import get_connection
from backend.db.influx import get_influx_client
from backend.config import settings

TBL_ENERGY = "ui_energy_metrics"
TBL_SOC = "ui_soc"
APP_TZ = ZoneInfo(settings.app_timezone)


def _utc_window(date_str: str):
    d = datetime.fromisoformat(date_str).date()
    start = datetime.combine(d, dtime(0, 0), tzinfo=APP_TZ)
    end = start + timedelta(days=1)
    return start.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC"))


def get_dates(project: str) -> list[str]:
    conn = get_connection()
    try:
        d1 = pd.read_sql(
            f"SELECT DISTINCT `date` FROM {TBL_ENERGY} WHERE project=%s ORDER BY `date` ASC",
            conn, params=(project,),
        )
        if not d1.empty:
            return [str(pd.to_datetime(d).date()) for d in d1["date"]]
        d2 = pd.read_sql(
            f"SELECT DISTINCT `date` FROM {TBL_SOC} WHERE project=%s ORDER BY `date` ASC",
            conn, params=(project,),
        )
        return [str(pd.to_datetime(d).date()) for d in d2["date"]] if not d2.empty else []
    finally:
        conn.close()


def get_energy_data(project: str, date_str: str) -> dict:
    # KPI from MySQL
    conn = get_connection()
    try:
        df_kpi = pd.read_sql(
            f"""SELECT max_pdc_kw, max_ev_kw, energy_ev_kwh,
                       energy_charge_kwh, energy_decharge_kwh, energy_aux_kwh
                FROM {TBL_ENERGY} WHERE project=%s AND `date`=%s LIMIT 1""",
            conn, params=(project, date_str),
        )
    finally:
        conn.close()

    kpi = {}
    if not df_kpi.empty:
        row = df_kpi.iloc[0]
        for col in df_kpi.columns:
            v = row[col]
            kpi[col] = round(float(v), 2) if pd.notna(v) else 0.0

    # Minute data from InfluxDB
    minute_chart = _load_minute_influx(project, date_str)

    return {"kpi": kpi, "minute_chart": minute_chart}


def _load_minute_influx(project: str, date_str: str) -> list[dict]:
    start_utc, end_utc = _utc_window(date_str)
    q = f"""
      SELECT MEAN("Gen_R_ResPMes")        AS "Gen_R_ResPMes",
             MEAN("Gen_ORI_EVPMes")       AS "Gen_ORI_EVPMes",
             LAST("Gen_OLI_PlantRunMode") AS "Gen_OLI_PlantRunMode"
      FROM "elto1sec_box"
      WHERE "project" = '{project}'
        AND time >= '{start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        AND time  < '{end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
      GROUP BY time(1m)
      ORDER BY time ASC
    """
    client = get_influx_client()
    res = client.query(q)
    pts = list(res.get_points()) if res else []
    if not pts:
        return []

    df = pd.DataFrame(pts)
    if df.empty:
        return []

    t_utc = pd.to_datetime(df["time"], utc=True)
    df["time"] = t_utc.dt.tz_convert(APP_TZ).dt.tz_localize(None)

    for c in ["Gen_R_ResPMes", "Gen_ORI_EVPMes", "Gen_OLI_PlantRunMode"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.rename(columns={
        "Gen_R_ResPMes": "res_kw",
        "Gen_ORI_EVPMes": "ev_kw",
        "Gen_OLI_PlantRunMode": "mode",
    })
    df["mode"] = df["mode"].ffill().bfill()

    result = []
    for _, r in df.iterrows():
        result.append({
            "time": r["time"].strftime("%Y-%m-%d %H:%M:%S"),
            "res_kw": round(float(r["res_kw"]), 2) if pd.notna(r["res_kw"]) else None,
            "ev_kw": round(float(r["ev_kw"]), 2) if pd.notna(r["ev_kw"]) else None,
            "mode": int(r["mode"]) if pd.notna(r["mode"]) else None,
        })
    return result

from __future__ import annotations

import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
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


def _compute_plant_is_limited(p_lim: pd.Series, p_ev: pd.Series, thr_kw: float = 5.0) -> pd.Series:
    diff = p_lim.abs() - p_ev.abs()
    is_limited = diff < thr_kw
    mask_nan = p_lim.isna() | p_ev.isna()
    return is_limited.where(~mask_nan, np.nan)


def _compute_is_limited(p_lim: pd.Series, p_ev: pd.Series, thr_kw: float = 5.0) -> pd.Series:
    diff = p_lim - p_ev
    is_limited = diff < thr_kw
    mask_nan = p_lim.isna() | p_ev.isna()
    return is_limited.where(~mask_nan, np.nan)


def _limited_summary(series: pd.Series) -> dict:
    valid = series.dropna()
    n_total = len(series)
    n_valid = len(valid)
    minutes_limited = int(valid.sum()) if not valid.empty else 0
    pct_limited = round(100.0 * minutes_limited / n_valid, 1) if n_valid > 0 else 0.0
    return {"minutes_limited": minutes_limited, "pct_limited": pct_limited, "n_valid": n_valid, "n_total": n_total}


def _load_box_data(project: str, date_str: str) -> pd.DataFrame:
    start_utc, end_utc = _utc_window(date_str)
    meas = settings.influx_measurement
    q = f"""
      SELECT MEAN("PDC_ORI_Lim_DC") AS "PDC_ORI_Lim_DC",
             MEAN("Gen_ORI_EVPMes") AS "Gen_ORI_EVPMes",
             LAST("SocMgt_OBI_SocLow") AS "SocMgt_OBI_SocLow",
             MEAN("Gen_ORI_SOC") AS "Gen_ORI_SOC"
      FROM "{meas}"
      WHERE "project" = '{project}'
        AND time >= '{start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        AND time  < '{end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
      GROUP BY time(1m)
      ORDER BY time ASC
    """
    client = get_influx_client("box")
    res = client.query(q)
    pts = list(res.get_points()) if res else []
    if not pts:
        return pd.DataFrame()

    df = pd.DataFrame(pts)
    t_utc = pd.to_datetime(df["time"], utc=True)
    df["time"] = t_utc.dt.tz_convert(APP_TZ).dt.tz_localize(None)
    for c in ["PDC_ORI_Lim_DC", "Gen_ORI_EVPMes", "SocMgt_OBI_SocLow", "Gen_ORI_SOC"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _load_borne_data(project: str, date_str: str) -> pd.DataFrame:
    start_utc, end_utc = _utc_window(date_str)
    meas = settings.influx_borne_measurement
    fields = []
    for i in range(1, 7):
        fields.append(f'MEAN("PDCx_R_PLim[{i}]") AS "PDCx_R_PLim_{i}"')
        fields.append(f'MEAN("EVI_P{i}.ILI.EVSE_OutPower") AS "EVI_P{i}_EVSE_OutPower"')
    fields_str = ", ".join(fields)

    q = f"""
      SELECT {fields_str}
      FROM "{meas}"
      WHERE "project" = '{project}'
        AND time >= '{start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        AND time  < '{end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
      GROUP BY time(1m)
      ORDER BY time ASC
    """
    client = get_influx_client("borne")
    res = client.query(q)
    pts = list(res.get_points()) if res else []
    if not pts:
        return pd.DataFrame()

    df = pd.DataFrame(pts)
    t_utc = pd.to_datetime(df["time"], utc=True)
    df["time"] = t_utc.dt.tz_convert(APP_TZ).dt.tz_localize(None)
    for i in range(1, 7):
        for col in [f"PDCx_R_PLim_{i}", f"EVI_P{i}_EVSE_OutPower"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def get_power_limitation_data(project: str, date_str: str) -> dict:
    with ThreadPoolExecutor(max_workers=2) as executor:
        fut_box = executor.submit(_load_box_data, project, date_str)
        fut_borne = executor.submit(_load_borne_data, project, date_str)
        df_box = fut_box.result()
        df_borne = fut_borne.result()

    # --- BOX section ---
    box_kpi = {}
    box_chart = []

    if not df_box.empty:
        pdc = df_box["PDC_ORI_Lim_DC"] if "PDC_ORI_Lim_DC" in df_box.columns else pd.Series(dtype=float)
        ev = df_box["Gen_ORI_EVPMes"] if "Gen_ORI_EVPMes" in df_box.columns else pd.Series(dtype=float)

        if not pdc.empty and not ev.empty:
            plant_limited = _compute_plant_is_limited(pdc, ev)
            df_box["plant_is_limited"] = plant_limited
            box_kpi = _limited_summary(plant_limited)

        for _, r in df_box.iterrows():
            pt: dict = {"time": r["time"].strftime("%Y-%m-%d %H:%M:%S")}
            for col, key in [
                ("PDC_ORI_Lim_DC", "pdc_lim_dc"),
                ("Gen_ORI_EVPMes", "ev_power"),
                ("SocMgt_OBI_SocLow", "soc_low"),
                ("Gen_ORI_SOC", "soc"),
            ]:
                v = r.get(col)
                pt[key] = round(float(v), 3) if pd.notna(v) else None
            v_lim = r.get("plant_is_limited")
            pt["plant_is_limited"] = int(v_lim) if pd.notna(v_lim) else None
            box_chart.append(pt)

    # --- BORNE section ---
    # Merge PDC_ORI_Lim_DC into borne for weight calculation
    if not df_box.empty and not df_borne.empty and "PDC_ORI_Lim_DC" in df_box.columns:
        df_merge = df_box[["time", "PDC_ORI_Lim_DC"]].copy()
        df_borne = df_borne.merge(df_merge, on="time", how="left")
        if "PDC_ORI_Lim_DC" in df_borne.columns:
            df_borne["PDC_ORI_Lim_DC"] = pd.to_numeric(df_borne["PDC_ORI_Lim_DC"], errors="coerce")

    plugs: dict = {}
    for i in range(1, 7):
        pdc_col = f"PDCx_R_PLim_{i}"
        evse_col = f"EVI_P{i}_EVSE_OutPower"

        plug_kpi = {}
        plug_chart = []

        if not df_borne.empty and pdc_col in df_borne.columns and evse_col in df_borne.columns:
            p_lim = df_borne[pdc_col]
            p_ev = df_borne[evse_col]
            is_limited = _compute_is_limited(p_lim, p_ev)
            df_borne[f"plug{i}_is_limited"] = is_limited
            plug_kpi = _limited_summary(is_limited)

            # Weight = PDCx_R_PLim[i] / PDC_ORI_Lim_DC (global), capped at [0, 1]
            if "PDC_ORI_Lim_DC" in df_borne.columns:
                global_lim = df_borne["PDC_ORI_Lim_DC"].abs()
                weight = (p_lim.abs() / global_lim.replace(0, np.nan)).clip(0, 1)
                df_borne[f"weight_{i}"] = weight

            for _, r in df_borne.iterrows():
                pt = {"time": r["time"].strftime("%Y-%m-%d %H:%M:%S")}
                for col, key in [(pdc_col, "pdc_r_plim"), (evse_col, "evse_out_power")]:
                    v = r.get(col)
                    pt[key] = round(float(v), 3) if pd.notna(v) else None
                v_lim = r.get(f"plug{i}_is_limited")
                pt["is_limited"] = int(v_lim) if pd.notna(v_lim) else None
                v_w = r.get(f"weight_{i}")
                pt["weight"] = round(float(v_w), 4) if pd.notna(v_w) else None
                plug_chart.append(pt)

        plugs[f"P{i}"] = {"kpi": plug_kpi, "chart": plug_chart}

    return {"box_kpi": box_kpi, "box_chart": box_chart, "plugs": plugs}

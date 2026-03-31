from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, date, time as dtime, timedelta
from zoneinfo import ZoneInfo

from backend.db.mysql import get_connection
from backend.db.influx import get_influx_client
from backend.config import settings

TABLE_ENERGY = "ui_soc_energy_day"
TABLE_RESUME = "ui_soc_resume_soc"
TABLE_HIST_SOC = "ui_soc_hist_soc"
TABLE_HIST_MODE = "ui_soc_hist_mode"

APP_TZ = ZoneInfo(settings.app_timezone)


def _utc_window(date_str: str):
    d = datetime.fromisoformat(date_str).date()
    start = datetime.combine(d, dtime(0, 0), tzinfo=APP_TZ)
    end = start + timedelta(days=1)
    return start.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC"))


def _soc_clean(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").astype(float)
    s = s.where(s.between(0, 100))

    low = s.le(4)
    gid = (low != low.shift(fill_value=False)).cumsum().where(low)
    if gid.notna().any():
        run_len = gid.groupby(gid).transform("size")
        s = s.mask(run_len.lt(4) & low)

    w = 7
    med = s.rolling(w, center=True, min_periods=1).median()
    abs_dev = (s - med).abs()
    mad = abs_dev.rolling(w, center=True, min_periods=1).median()
    thr = 3.0 * 1.4826 * mad
    s = s.mask(abs_dev.gt(thr))

    d = s.diff()
    pos5 = d.clip(lower=0).rolling(5, min_periods=1).sum()
    neg5 = (-d.clip(upper=0)).rolling(5, min_periods=1).sum()
    jump = pos5.ge(30) | neg5.ge(30)
    jump = jump | jump.shift(1, fill_value=False) | jump.shift(-1, fill_value=False)
    s = s.mask(jump)

    s = s.interpolate(limit=10, limit_direction="both").ffill().bfill()
    return s.clip(0, 100)


def get_dates(project: str) -> list[str]:
    sql = f"SELECT DISTINCT `date` FROM {TABLE_ENERGY} WHERE project=%s ORDER BY `date` ASC"
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=(project,))
    finally:
        conn.close()

    dates = [str(pd.to_datetime(d).date()) for d in df["date"]] if not df.empty else []
    today_local = datetime.now(APP_TZ).date().isoformat()
    if today_local not in dates:
        dates.append(today_local)
    return dates


ENERGIE_NOMINALE_CONSTRUCTEUR = 745.6  # kWh


def get_soc_data(project: str, date_str: str) -> dict:
    soc_chart = _load_soc_chart(project, date_str)
    energy, resume, hist_soc, hist_mode, batt_temp = _load_day(project, date_str)

    # KPI: delta SOC mode 4
    delta_soc_cum = 0.0
    if hist_mode:
        for row in hist_mode:
            mode = row.get("mode")
            ds = row.get("delta_soc")
            if mode == 4 and ds is not None and ds < 0:
                delta_soc_cum += abs(ds)

    discharge_kwh = None
    if energy:
        discharge_kwh = energy.get("energie_decharge_kwh")

    # SOH + analyse énergétique théorique vs réelle
    soh_jour = _load_soh(project, date_str)
    energie_nominale_theorique = None
    energie_theorique_dechargee = None
    ratio_energie = None
    ecart_kwh = None
    ecart_pct = None
    if soh_jour is not None:
        energie_nominale_theorique = round(ENERGIE_NOMINALE_CONSTRUCTEUR * (soh_jour / 100.0), 2)
        if delta_soc_cum > 0:
            energie_theorique_dechargee = round((delta_soc_cum / 100.0) * energie_nominale_theorique, 2)
            if energie_theorique_dechargee and discharge_kwh:
                ratio_energie = round((discharge_kwh / energie_theorique_dechargee) * 100.0, 1)
                ecart_kwh = round(discharge_kwh - energie_theorique_dechargee, 2)
                ecart_pct = round((ecart_kwh / energie_theorique_dechargee) * 100.0, 1)

    return {
        "soc_chart": soc_chart,
        "kpi": {
            "delta_soc_cum": round(delta_soc_cum, 2),
            "discharge_kwh": round(discharge_kwh, 2) if discharge_kwh is not None else None,
        },
        "energie_analysis": {
            "energie_nominale_constructeur": ENERGIE_NOMINALE_CONSTRUCTEUR,
            "soh_jour": round(soh_jour, 2) if soh_jour is not None else None,
            "energie_nominale_theorique": energie_nominale_theorique,
            "energie_theorique_dechargee": energie_theorique_dechargee,
            "energie_reelle": round(discharge_kwh, 2) if discharge_kwh is not None else None,
            "ratio_energie": ratio_energie,
            "ecart_kwh": ecart_kwh,
            "ecart_pct": ecart_pct,
        },
        "resume": resume,
        "runs": [r for r in hist_soc if r.get("soc_state") == 2],
        "batt_temp": {
            "min_c": energy.get("batt_temp_min_c") if energy else None,
            "min_time": energy.get("batt_temp_min_time") if energy else None,
            "max_c": energy.get("batt_temp_max_c") if energy else None,
            "max_time": energy.get("batt_temp_max_time") if energy else None,
            "avg_c": energy.get("batt_temp_avg_c") if energy else None,
        },
        "hist_soc": hist_soc,
    }


def _load_soc_chart(project: str, date_str: str) -> list[dict]:
    start_utc, end_utc = _utc_window(date_str)
    q = f"""
      SELECT MEAN("Gen_ORI_SOC") AS "Gen_ORI_SOC"
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
        return []

    df = pd.DataFrame(pts)
    if df.empty or "Gen_ORI_SOC" not in df.columns:
        return []

    t_utc = pd.to_datetime(df["time"], utc=True)
    df["time"] = t_utc.dt.tz_convert(APP_TZ).dt.tz_localize(None)
    df["soc"] = _soc_clean(df["Gen_ORI_SOC"])

    valid = df["Gen_ORI_SOC"].notna()
    if valid.any():
        first_idx = valid.idxmax()
        last_idx = valid[::-1].idxmax()
        df.loc[:first_idx - 1, "soc"] = np.nan
        df.loc[last_idx + 1:, "soc"] = np.nan

    result = []
    for _, r in df.iterrows():
        v = r["soc"]
        if pd.notna(v):
            result.append({
                "time": r["time"].strftime("%Y-%m-%d %H:%M"),
                "soc": round(float(v), 2),
            })
    return result


def _load_soh(project: str, date_str: str) -> float | None:
    """Charge BBMS1/BBMS2 SOH depuis Influx et retourne la moyenne journalière."""
    start_utc, end_utc = _utc_window(date_str)
    meas = settings.influx_measurement
    q = f"""
      SELECT MEAN("BBMS1.MBMU.ORI.SOH") AS "BBMS1_SOH",
             MEAN("BBMS2.MBMU.ORI.SOH") AS "BBMS2_SOH"
      FROM "{meas}"
      WHERE "project" = '{project}'
        AND time >= '{start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        AND time  < '{end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}'
      GROUP BY time(1m) ORDER BY time ASC
    """
    client = get_influx_client()
    res = client.query(q)
    pts = list(res.get_points()) if res else []
    if not pts:
        return None

    df = pd.DataFrame(pts)
    for col in ["BBMS1_SOH", "BBMS2_SOH"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "BBMS1_SOH" in df.columns and "BBMS2_SOH" in df.columns:
        df["Gen_ORI_SOH"] = df[["BBMS1_SOH", "BBMS2_SOH"]].mean(axis=1)
    elif "BBMS1_SOH" in df.columns:
        df["Gen_ORI_SOH"] = df["BBMS1_SOH"]
    elif "BBMS2_SOH" in df.columns:
        df["Gen_ORI_SOH"] = df["BBMS2_SOH"]
    else:
        return None

    valid = df["Gen_ORI_SOH"].dropna()
    return float(valid.mean()) if not valid.empty else None


def _load_day(project: str, date_str: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Energy
        cursor.execute(
            f"""SELECT energie_decharge_kwh,
                       batt_temp_min_c, batt_temp_min_time,
                       batt_temp_max_c, batt_temp_max_time,
                       batt_temp_avg_c
                FROM {TABLE_ENERGY}
                WHERE project=%s AND `date`=%s LIMIT 1""",
            (project, date_str),
        )
        row = cursor.fetchone()
        cols = [d[0] for d in cursor.description]
        energy = dict(zip(cols, row)) if row else {}
        for k in energy:
            v = energy[k]
            if v is not None and hasattr(v, "__float__"):
                energy[k] = float(v)
            elif hasattr(v, "strftime"):
                energy[k] = str(v)

        # Resume
        cursor.execute(
            f"SELECT soc_state, minutes, pourcentage FROM {TABLE_RESUME} WHERE project=%s AND `date`=%s",
            (project, date_str),
        )
        resume_rows = cursor.fetchall()
        resume_cols = [d[0] for d in cursor.description]
        order = [2, 1, 3, 4]
        labels = {1: "RUN+EV (1)", 2: "RUN (2)", 3: "Stand-by (3)", 4: "Enable (4)"}
        resume_raw = []
        for r in resume_rows:
            rd = dict(zip(resume_cols, r))
            state = int(rd["soc_state"]) if rd["soc_state"] is not None else 0
            if state == 0:
                continue
            resume_raw.append({
                "soc_state": state,
                "label": labels.get(state, str(state)),
                "minutes": float(rd["minutes"]) if rd["minutes"] is not None else 0,
                "pourcentage": float(rd["pourcentage"]) if rd["pourcentage"] is not None else 0,
            })
        resume = sorted(resume_raw, key=lambda x: order.index(x["soc_state"]) if x["soc_state"] in order else 999)

        # Hist SOC
        cursor.execute(
            f"""SELECT start_time, end_time, soc_state,
                       ROUND(delta_time_min, 2)+0 AS delta_time_min,
                       ROUND(energie_pdc_kwh, 2)+0 AS energie_pdc_kwh,
                       ROUND(energie_ev_kwh, 2)+0 AS energie_ev_kwh,
                       ROUND(soc_debut, 2)+0 AS soc_debut,
                       ROUND(soc_fin, 2)+0 AS soc_fin,
                       ROUND(delta_soc, 2)+0 AS delta_soc
                FROM {TABLE_HIST_SOC}
                WHERE project=%s AND `date`=%s AND (soc_state IS NULL OR soc_state <> 0)
                ORDER BY start_time""",
            (project, date_str),
        )
        hist_rows = cursor.fetchall()
        hist_cols = [d[0] for d in cursor.description]
        hist_soc = []
        for r in hist_rows:
            rd = dict(zip(hist_cols, r))
            for k in rd:
                if hasattr(rd[k], "strftime"):
                    rd[k] = str(rd[k])
                elif rd[k] is not None and hasattr(rd[k], "__float__"):
                    rd[k] = float(rd[k])
            if rd.get("soc_state") is not None:
                rd["soc_state"] = int(rd["soc_state"])
            hist_soc.append(rd)

        # Hist Mode
        cursor.execute(
            f"SELECT `mode`, delta_soc FROM {TABLE_HIST_MODE} WHERE project=%s AND `date`=%s",
            (project, date_str),
        )
        mode_rows = cursor.fetchall()
        mode_cols = [d[0] for d in cursor.description]
        hist_mode = []
        for r in mode_rows:
            rd = dict(zip(mode_cols, r))
            if rd.get("mode") is not None:
                rd["mode"] = int(rd["mode"])
            if rd.get("delta_soc") is not None:
                rd["delta_soc"] = float(rd["delta_soc"])
            hist_mode.append(rd)

    finally:
        cursor.close()
        conn.close()

    return energy, resume, hist_soc, hist_mode, None

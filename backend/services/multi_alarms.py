from __future__ import annotations

import pandas as pd
from backend.db.mysql import get_connection
from backend.services.sites import label_site


def get_dates(sites: list[str]) -> list[str]:
    placeholders = ",".join(["%s"] * len(sites))
    sql = f"SELECT DISTINCT `date` FROM ui_alarm_daily WHERE project IN ({placeholders}) ORDER BY `date` ASC"
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=tuple(sites))
    finally:
        conn.close()
    return [str(pd.to_datetime(d).date()) for d in df["date"]] if not df.empty else []


def get_alarm_data(sites: list[str], dates: list[str]) -> dict:
    placeholders_sites = ",".join(["%s"] * len(sites))
    placeholders_dates = ",".join(["%s"] * len(dates))
    sql = f"""
    SELECT project, `date`,
           soc_bas_detected, soc_diff_batt_gt_8pct, soc_diff_time,
           soc_mgt_missing_night, soc_5h10,
           water_level_low, water_level_time, water_level_value,
           energy_ev_low, temp_batt_over_28, temp_batt_time
    FROM ui_alarm_daily
    WHERE project IN ({placeholders_sites}) AND `date` IN ({placeholders_dates})
    ORDER BY `date` DESC, project
    """
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=(*sites, *dates))
    finally:
        conn.close()

    if df.empty:
        return {"rows": []}

    def _bool(val):
        if val is None or pd.isna(val):
            return None
        return bool(val)

    rows = []
    for _, r in df.iterrows():
        rows.append({
            "date": pd.Timestamp(r["date"]).strftime("%d/%m/%Y"),
            "site": label_site(r["project"]),
            "soc_bas": _bool(r.get("soc_bas_detected")),
            "soc_diff_gt_8": _bool(r.get("soc_diff_batt_gt_8pct")),
            "soc_diff_time": str(r["soc_diff_time"]) if pd.notna(r.get("soc_diff_time")) else None,
            "soc_mgt_missing": _bool(r.get("soc_mgt_missing_night")),
            "soc_5h10": round(float(r["soc_5h10"]), 1) if pd.notna(r.get("soc_5h10")) else None,
            "water_level_low": _bool(r.get("water_level_low")),
            "water_level_time": str(r["water_level_time"]) if pd.notna(r.get("water_level_time")) else None,
            "water_level_value": round(float(r["water_level_value"]), 1) if pd.notna(r.get("water_level_value")) else None,
            "energy_ev_low": _bool(r.get("energy_ev_low")),
            "temp_over_28": _bool(r.get("temp_batt_over_28")),
            "temp_time": str(r["temp_batt_time"]) if pd.notna(r.get("temp_batt_time")) else None,
        })

    return {"rows": rows}

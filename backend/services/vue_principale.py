import pandas as pd
from datetime import date, timedelta

from backend.db.mysql import get_connection
from backend.services.sites import PROJECTS, label_site

TABLE = "ui_alarm_daily"
TABLE_SOC = "ui_alarm_soc_morning"


def get_soc_morning() -> dict:
    aujourdhui = date.today()
    placeholders = ",".join(["%s"] * len(PROJECTS))
    sql = f"""
    SELECT project, `date`, soc_5h10, soc_below_85
    FROM {TABLE_SOC}
    WHERE project IN ({placeholders}) AND `date` = %s
    """
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=(*PROJECTS, aujourdhui))
    finally:
        conn.close()

    if df.empty:
        return {"date": str(aujourdhui), "rows": []}

    rows = []
    for _, r in df.iterrows():
        soc_val = r["soc_5h10"]
        rows.append({
            "date": pd.Timestamp(r["date"]).strftime("%d/%m/%Y"),
            "site": label_site(r["project"]),
            "soc_below_85": bool(r["soc_below_85"]) if pd.notna(r["soc_below_85"]) else None,
            "soc_5h10": round(float(soc_val), 1) if pd.notna(soc_val) else None,
        })

    return {"date": str(aujourdhui), "rows": rows}


def get_alerts_j1() -> dict:
    hier = (date.today() - timedelta(days=1))
    placeholders = ",".join(["%s"] * len(PROJECTS))
    sql = f"""
    SELECT
        project, `date`,
        soc_mgt_missing_night,
        soc_diff_batt_gt_8pct,
        soc_diff_time,
        water_level_low,
        energy_ev_low,
        temp_batt_over_28,
        temp_batt_time,
        soc_5h10
    FROM {TABLE}
    WHERE project IN ({placeholders}) AND `date` = %s
    """
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=(*PROJECTS, hier))
    finally:
        conn.close()

    if df.empty:
        return {"date": str(hier), "summary": {}, "rows": []}

    alert_cols = [
        "soc_mgt_missing_night",
        "soc_diff_batt_gt_8pct",
        "temp_batt_over_28",
        "water_level_low",
        "energy_ev_low",
    ]

    soc_mgmt_anomalie = bool(df["soc_mgt_missing_night"].fillna(False).any())
    critique_anomalie = bool(df[alert_cols].fillna(False).any(axis=1).any())

    rows = []
    for _, r in df.iterrows():
        def _bool(val):
            if val is None or pd.isna(val):
                return None
            return bool(val)

        soc_val = r["soc_5h10"]
        rows.append({
            "date": pd.Timestamp(r["date"]).strftime("%d/%m/%Y"),
            "site": label_site(r["project"]),
            "soc_below_85": (soc_val is not None and pd.notna(soc_val) and float(soc_val) < 85),
            "soc_diff_gt_8": _bool(r["soc_diff_batt_gt_8pct"]),
            "temp_over_28": _bool(r["temp_batt_over_28"]),
            "water_level_low": _bool(r["water_level_low"]),
            "energy_ev_low": _bool(r["energy_ev_low"]),
        })

    return {
        "date": str(hier),
        "summary": {
            "soc_mgmt_ok": not soc_mgmt_anomalie,
            "critiques_ok": not critique_anomalie,
        },
        "rows": rows,
    }

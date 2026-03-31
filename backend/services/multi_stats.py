from __future__ import annotations

import pandas as pd
import numpy as np
from backend.db.mysql import get_connection
from backend.services.sites import label_site


def get_dates(sites: list[str]) -> list[str]:
    placeholders = ",".join(["%s"] * len(sites))
    sql = f"SELECT DISTINCT `date` FROM ui_ev_power_daily WHERE project IN ({placeholders}) ORDER BY `date` ASC"
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=tuple(sites))
    finally:
        conn.close()
    return [str(pd.to_datetime(d).date()) for d in df["date"]] if not df.empty else []


def get_stats_data(sites: list[str], start_date: str, end_date: str) -> dict:
    placeholders = ",".join(["%s"] * len(sites))
    params = (*sites, start_date, end_date)
    conn = get_connection()
    try:
        dfp = pd.read_sql(
            f"""SELECT project,
                       SUM(COALESCE(total_ev_kwh, 0))    AS total_ev_kwh,
                       MAX(pmax_ev_kw)                   AS pmax_ev_kw,
                       AVG(pmoy_ev_kw)                   AS pmoy_ev_kw,
                       SUM(COALESCE(charge_batt_hr, 0))  AS charge_batt_hr,
                       SUM(COALESCE(charge_grid_hr, 0))  AS charge_grid_hr,
                       SUM(COALESCE(charge_total_hr, 0)) AS charge_total_hr,
                       COUNT(*)                          AS days_with_data
                FROM ui_ev_power_daily
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                GROUP BY project ORDER BY project""",
            conn, params=params,
        )
        dfc = pd.read_sql(
            f"""SELECT project,
                       SUM(cycles_total) AS cycles_total,
                       COUNT(*)          AS days_with_data
                FROM ui_cycles_daily
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                GROUP BY project""",
            conn, params=params,
        )
    finally:
        conn.close()

    if dfp.empty:
        return {"global_kpi": {}, "per_site": [], "charts": {}}

    dfp["avg_energy_per_day"] = np.where(
        dfp["days_with_data"] > 0,
        (dfp["total_ev_kwh"] / dfp["days_with_data"]).round(2),
        np.nan,
    )
    dfp["Site"] = dfp["project"].apply(label_site)

    def _f(v, d=2): return round(float(v), d) if pd.notna(v) else 0.0
    def _fn(v, d=2): return round(float(v), d) if pd.notna(v) else None

    per_site = []
    for _, r in dfp.iterrows():
        cyc = dfc[dfc["project"] == r["project"]]
        cycles_total = _f(cyc["cycles_total"].iloc[0]) if not cyc.empty and pd.notna(cyc["cycles_total"].iloc[0]) else 0.0
        days_cyc = int(cyc["days_with_data"].iloc[0]) if not cyc.empty else max(int(r["days_with_data"]), 1)
        per_site.append({
            "site": r["Site"],
            "total_ev_kwh": _f(r["total_ev_kwh"]),
            "avg_energy_per_day": _fn(r["avg_energy_per_day"]),
            "pmoy_ev_kw": _fn(r["pmoy_ev_kw"]),
            "pmax_ev_kw": _f(r["pmax_ev_kw"]),
            "charge_total_hr": _f(r["charge_total_hr"]),
            "charge_batt_hr": _f(r["charge_batt_hr"]),
            "charge_grid_hr": _f(r["charge_grid_hr"]),
            "days_with_data": int(r["days_with_data"]),
            "cycles_total": cycles_total,
            "cycles_per_day": round(cycles_total / days_cyc, 3) if days_cyc > 0 else 0.0,
        })

    global_kpi: dict = {}
    if per_site:
        tot_ev = sum(s["total_ev_kwh"] for s in per_site)
        tot_h = sum(s["charge_total_hr"] for s in per_site)
        global_kpi["total_ev_kwh"] = round(tot_ev, 2)
        global_kpi["total_charge_hours"] = round(tot_h, 2)
        global_kpi["global_avg_power"] = round(tot_ev / tot_h, 2) if tot_h > 0 else None
        top_p = max(per_site, key=lambda s: s["pmax_ev_kw"] or 0)
        global_kpi["max_ev_kw"] = top_p["pmax_ev_kw"]
        global_kpi["max_ev_site"] = top_p["site"]
        top_e = max(per_site, key=lambda s: s["total_ev_kwh"] or 0)
        global_kpi["top_energy_site"] = top_e["site"]
        global_kpi["top_energy_kwh"] = top_e["total_ev_kwh"]
        top_c = max(per_site, key=lambda s: s["cycles_per_day"] or 0)
        global_kpi["top_cycles_site"] = top_c["site"]
        global_kpi["top_cycles_per_day"] = top_c["cycles_per_day"]

    return {
        "global_kpi": global_kpi,
        "per_site": per_site,
        "charts": {
            "cycles_by_site": [{"site": s["site"], "value": s["cycles_total"]} for s in per_site],
            "energy_by_site": [{"site": s["site"], "value": s["total_ev_kwh"]} for s in per_site],
        },
    }

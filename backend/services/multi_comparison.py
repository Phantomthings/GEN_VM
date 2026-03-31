from __future__ import annotations

import pandas as pd
from backend.db.mysql import get_connection
from backend.services.sites import label_site


def get_dates(sites: list[str]) -> list[str]:
    conn = get_connection()
    try:
        sets = []
        for proj in sites:
            df = pd.read_sql(
                "SELECT DISTINCT `date` FROM ui_comparaison WHERE project=%s ORDER BY `date` ASC",
                conn, params=(proj,),
            )
            sets.append(set(str(pd.to_datetime(d).date()) for d in df["date"]) if not df.empty else set())
    finally:
        conn.close()

    if not sets:
        return []
    common = sets[0]
    for s in sets[1:]:
        common &= s
    return sorted(common)


def get_comparison_data(sites: list[str], date_str: str) -> dict:
    placeholders = ",".join(["%s"] * len(sites))
    sql = f"""
    SELECT project,
           pm_off_pct, pm_standby_pct, pm_ac_pct,
           pm_battery_pct          AS pm_batt_pct,
           soc_off_pct             AS soc_disable_pct,
           soc_run_ev_pct          AS soc_run1_pct,
           soc_run_pct             AS soc_run2_pct,
           soc_standby_pct, soc_enable_pct,
           run_avg_start_minute,
           run_avg_soc_start       AS run_avg_soc_start_pct,
           run_avg_duration_min,
           transitions_34_count,
           energy_ev_kwh, energy_aux_kwh,
           energy_pdc_charge_kwh   AS energy_charge_kwh,
           energy_pdc_discharge_kwh AS energy_decharge_kwh,
           ev_peak_kw              AS max_ev_kw,
           ev_peak_time
    FROM ui_comparaison
    WHERE project IN ({placeholders}) AND `date`=%s
    """
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=(*sites, date_str))
    finally:
        conn.close()

    if df.empty:
        return {"rows": []}

    rows = []
    for _, r in df.iterrows():
        row = {"site": label_site(r["project"])}
        for c in df.columns:
            if c == "project":
                continue
            v = r[c]
            if hasattr(v, "strftime"):
                row[c] = str(v)
            elif pd.notna(v):
                row[c] = round(float(v), 2) if isinstance(v, (float, int)) else str(v)
            else:
                row[c] = None
        # Format run start time
        if row.get("run_avg_start_minute") is not None:
            m = int(row["run_avg_start_minute"])
            h, mn = divmod(m, 60)
            row["run_avg_start_time"] = f"{h:02d}:{mn:02d}"
        rows.append(row)

    return {"rows": rows}

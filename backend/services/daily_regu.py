from __future__ import annotations

import pandas as pd
from backend.db.mysql import get_connection

TBL_RESUME = "ui_reg_resume_mode"
TBL_HIST = "ui_soc_hist_mode"
TBL_HEATMAP = "ui_reg_heatmap_mode4"
TBL_BREAKDOWN = "ui_reg_mode4_breakdown"
TBL_TRANSITIONS = "ui_reg_transitions"
TBL_TRX_DAILY = "ui_reg_transitions_daily"
TBL_METRICS = "ui_reg_metrics"

MODE_LABELS = {1: "OFF (1)", 2: "Stand-by (2)", 3: "AC (3)", 4: "Batterie (4)"}


def get_dates(project: str) -> list[str]:
    sql = f"SELECT DISTINCT `date` FROM ui_reg_hist_mode WHERE project=%s ORDER BY `date` ASC"
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=(project,))
    finally:
        conn.close()
    return [str(pd.to_datetime(d).date()) for d in df["date"]] if not df.empty else []


def get_regu_data(project: str, date_str: str) -> dict:
    conn = get_connection()
    try:
        df_resume = pd.read_sql(
            f"SELECT mode, minutes, pct FROM {TBL_RESUME} WHERE project=%s AND `date`=%s",
            conn, params=(project, date_str),
        )
        df_metrics = pd.read_sql(
            f"SELECT energy_ev_kwh FROM {TBL_METRICS} WHERE project=%s AND `date`=%s LIMIT 1",
            conn, params=(project, date_str),
        )
        df_hist = pd.read_sql(
            f"""SELECT start_time, end_time, mode, delta_time_min,
                       energie_pdc_kwh, energie_ev_kwh, soc_debut, soc_fin, delta_soc
                FROM {TBL_HIST} WHERE project=%s AND `date`=%s ORDER BY start_time""",
            conn, params=(project, date_str),
        )
        df_heat = pd.read_sql(
            f"SELECT hour, pct FROM {TBL_HEATMAP} WHERE project=%s AND `date`=%s ORDER BY hour",
            conn, params=(project, date_str),
        )
        df_break = pd.read_sql(
            f"SELECT cat, minutes, pct FROM {TBL_BREAKDOWN} WHERE project=%s AND `date`=%s",
            conn, params=(project, date_str),
        )
        df_trx = pd.read_sql(
            f"""SELECT start_mode3_time, start_mode4_time, duration_min, temp_c
                FROM {TBL_TRANSITIONS} WHERE project=%s AND `date`=%s ORDER BY start_mode3_time""",
            conn, params=(project, date_str),
        )
        df_trx_daily = pd.read_sql(
            f"SELECT n_transitions, avg_duration_min, avg_temp_c FROM {TBL_TRX_DAILY} WHERE project=%s AND `date`=%s LIMIT 1",
            conn, params=(project, date_str),
        )
    finally:
        conn.close()

    # Resume
    resume = []
    for _, r in df_resume.iterrows():
        m = int(r["mode"]) if pd.notna(r["mode"]) else 0
        resume.append({
            "mode": m,
            "label": MODE_LABELS.get(m, str(m)),
            "minutes": round(float(r["minutes"]), 2) if pd.notna(r["minutes"]) else 0,
            "pct": round(float(r["pct"]), 2) if pd.notna(r["pct"]) else 0,
        })

    # Hist (timeline)
    hist = []
    for _, r in df_hist.iterrows():
        row = {}
        for c in df_hist.columns:
            v = r[c]
            if hasattr(v, "strftime"):
                row[c] = str(v)
            elif pd.notna(v):
                row[c] = float(v) if isinstance(v, (float, int)) else str(v)
            else:
                row[c] = None
        if row.get("mode") is not None:
            row["mode"] = int(row["mode"])
        hist.append(row)

    # Heatmap
    heatmap = []
    for _, r in df_heat.iterrows():
        heatmap.append({
            "hour": int(r["hour"]),
            "pct": round(float(r["pct"]), 2) if pd.notna(r["pct"]) else 0,
        })

    # Breakdown
    cat_labels = {"run2": "Auto-charge depuis le reseau", "ev0": "Charge EV depuis batteries", "autres": "Autres etats"}
    breakdown = []
    for _, r in df_break.iterrows():
        breakdown.append({
            "cat": r["cat"],
            "label": cat_labels.get(r["cat"], r["cat"]),
            "minutes": round(float(r["minutes"]), 2) if pd.notna(r["minutes"]) else 0,
            "pct": round(float(r["pct"]), 2) if pd.notna(r["pct"]) else 0,
        })

    # Transitions
    transitions = []
    for _, r in df_trx.iterrows():
        transitions.append({
            "start_mode3_time": str(r["start_mode3_time"]) if pd.notna(r["start_mode3_time"]) else None,
            "start_mode4_time": str(r["start_mode4_time"]) if pd.notna(r["start_mode4_time"]) else None,
            "duration_min": round(float(r["duration_min"]), 2) if pd.notna(r["duration_min"]) else None,
            "temp_c": round(float(r["temp_c"]), 2) if pd.notna(r["temp_c"]) else None,
        })

    # Transition daily KPIs
    trx_daily = {}
    if not df_trx_daily.empty:
        rd = df_trx_daily.iloc[0]
        trx_daily = {
            "n_transitions": int(rd["n_transitions"]) if pd.notna(rd.get("n_transitions")) else 0,
            "avg_duration_min": round(float(rd["avg_duration_min"]), 2) if pd.notna(rd.get("avg_duration_min")) else None,
            "avg_temp_c": round(float(rd["avg_temp_c"]), 2) if pd.notna(rd.get("avg_temp_c")) else None,
        }

    # Metrics
    energy_ev_mode3 = None
    if not df_metrics.empty and "energy_ev_kwh" in df_metrics.columns:
        v = df_metrics["energy_ev_kwh"].iloc[0]
        if pd.notna(v):
            energy_ev_mode3 = round(float(v), 2)

    return {
        "resume": resume,
        "hist": hist,
        "heatmap": heatmap,
        "breakdown": breakdown,
        "transitions": transitions,
        "trx_daily": trx_daily,
        "energy_ev_mode3": energy_ev_mode3,
    }

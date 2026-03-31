from __future__ import annotations

import pandas as pd
import numpy as np
from backend.db.mysql import get_connection
from backend.services.sites import label_site


def get_dates(sites: list[str]) -> list[str]:
    placeholders = ",".join(["%s"] * len(sites))
    sql = f"SELECT DISTINCT `date` FROM ui_interval_daily WHERE project IN ({placeholders}) ORDER BY `date` ASC"
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=tuple(sites))
    finally:
        conn.close()
    return [str(pd.to_datetime(d).date()) for d in df["date"]] if not df.empty else []


def get_interval_data(sites: list[str], start_date: str, end_date: str) -> dict:
    conn = get_connection()
    try:
        placeholders = ",".join(["%s"] * len(sites))
        params = (*sites, start_date, end_date)

        # Main interval daily table
        df = pd.read_sql(
            f"""SELECT project, `date`, minutes_run, soc_start_pct,
                       energy_ev_kwh, energy_decharge_kwh, ev_peak_kw,
                       pm_ac_pct, pm_battery_pct
                FROM ui_interval_daily
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                ORDER BY `date`, project""",
            conn, params=params,
        )

        # Transitions (weighted averages like Streamlit)
        df_trx = pd.read_sql(
            f"""SELECT project,
                       COALESCE(SUM(n_transitions), 0)  AS total_transitions,
                       COUNT(*)                          AS jours,
                       SUM(CASE WHEN avg_duration_min IS NOT NULL THEN n_transitions * avg_duration_min ELSE 0 END) AS sum_duration,
                       SUM(CASE WHEN avg_duration_min IS NOT NULL THEN n_transitions ELSE 0 END)                    AS weight_duration,
                       SUM(CASE WHEN avg_temp_c IS NOT NULL THEN n_transitions * avg_temp_c ELSE 0 END)             AS sum_temp,
                       SUM(CASE WHEN avg_temp_c IS NOT NULL THEN n_transitions ELSE 0 END)                          AS weight_temp
                FROM ui_reg_transitions_daily
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                GROUP BY project""",
            conn, params=params,
        )

        # Heatmap mode 4 per site
        df_heat = pd.read_sql(
            f"""SELECT project, `hour`, ROUND(AVG(pct), 2) AS avg_pct
                FROM ui_reg_heatmap_mode4
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                GROUP BY project, `hour` ORDER BY project, `hour`""",
            conn, params=params,
        )

        # Reg mode dominant per hour — load raw segments and distribute across all spanned hours
        df_reg_dom_raw = pd.read_sql(
            f"""SELECT project, start_time, mode, delta_time_min
                FROM ui_reg_hist_mode
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                  AND mode IN (1,2,3,4)
                ORDER BY project, start_time""",
            conn, params=params,
        )

        # SOC dominant per hour — load raw segments and distribute across all spanned hours
        df_soc_dom_raw = pd.read_sql(
            f"""SELECT project, start_time, soc_state, delta_time_min
                FROM ui_hist_soc
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                  AND soc_state BETWEEN 0 AND 4
                ORDER BY project, start_time""",
            conn, params=params,
        )

        # Status centrale — modes
        df_modes = pd.read_sql(
            f"""SELECT project, `date`, mode, SUM(delta_time_min) AS minutes
                FROM ui_reg_hist_mode
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                  AND mode IN (1,2,3,4)
                GROUP BY project, `date`, mode""",
            conn, params=params,
        )

        # Status centrale — breakdown
        df_break = pd.read_sql(
            f"""SELECT project, `date`, cat, SUM(minutes) AS minutes
                FROM ui_reg_mode4_breakdown
                WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                  AND cat IN ('ev0','run2')
                GROUP BY project, `date`, cat""",
            conn, params=params,
        )

        # Detailed stats with min/max dates (matching Streamlit's _load_stats)
        stats_rows: dict[str, list] = {}
        for metric in ["minutes_run", "soc_start_pct", "energy_ev_kwh", "ev_peak_kw"]:
            df_s = pd.read_sql(
                f"""SELECT
                      t.project,
                      a.min_value  AS min_val,
                      a.min_date,
                      a.max_value  AS max_val,
                      a.max_date,
                      ROUND(AVG(t.{metric}), 2)   AS moyenne,
                      ROUND(STD(t.{metric}), 2)   AS ecart_type,
                      COUNT(t.{metric})            AS jours
                    FROM ui_interval_daily t
                    JOIN (
                      SELECT project,
                             MIN({metric}) AS min_value,
                             SUBSTRING_INDEX(GROUP_CONCAT(`date` ORDER BY {metric} ASC, `date` ASC SEPARATOR ','), ',', 1) AS min_date,
                             MAX({metric}) AS max_value,
                             SUBSTRING_INDEX(GROUP_CONCAT(`date` ORDER BY {metric} DESC, `date` DESC SEPARATOR ','), ',', 1) AS max_date
                      FROM ui_interval_daily
                      WHERE project IN ({placeholders}) AND `date` BETWEEN %s AND %s
                        AND {metric} IS NOT NULL
                      GROUP BY project
                    ) a ON a.project = t.project
                    WHERE t.project IN ({placeholders}) AND t.`date` BETWEEN %s AND %s
                      AND t.{metric} IS NOT NULL
                    GROUP BY t.project, a.min_value, a.min_date, a.max_value, a.max_date
                    ORDER BY t.project""",
                conn, params=(*sites, start_date, end_date, *sites, start_date, end_date),
            )
            rows_list = []
            for _, r in df_s.iterrows():
                rows_list.append({
                    "site": label_site(r["project"]),
                    "Min": round(float(r["min_val"]), 2) if pd.notna(r["min_val"]) else None,
                    "Date Min": str(r["min_date"]) if pd.notna(r["min_date"]) else None,
                    "Max": round(float(r["max_val"]), 2) if pd.notna(r["max_val"]) else None,
                    "Date Max": str(r["max_date"]) if pd.notna(r["max_date"]) else None,
                    "Moyenne": round(float(r["moyenne"]), 2) if pd.notna(r["moyenne"]) else None,
                    "Ecart-type": round(float(r["ecart_type"]), 2) if pd.notna(r["ecart_type"]) else None,
                    "Jours": int(r["jours"]) if pd.notna(r["jours"]) else 0,
                })
            stats_rows[metric] = rows_list

    finally:
        conn.close()

    # ── Batteries pivot tables ─────────────────────────────────────────────────
    batteries: dict[str, dict] = {}
    timeseries: list[dict] = []

    if not df.empty:
        df["site"] = df["project"].apply(label_site)
        df["date_str"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        for metric in ["minutes_run", "soc_start_pct"]:
            if metric in df.columns:
                pivot = df.pivot_table(index="date_str", columns="site", values=metric, aggfunc="first")
                batteries[metric] = {
                    "pivot": pivot.reset_index().fillna("").to_dict("records"),
                    "stats": stats_rows.get(metric, []),
                }

        # Raw timeseries for line/box charts (per site per date)
        for _, r in df.iterrows():
            timeseries.append({
                "site": r["site"],
                "date": r["date_str"],
                "minutes_run": round(float(r["minutes_run"]), 2) if pd.notna(r.get("minutes_run")) else None,
                "soc_start_pct": round(float(r["soc_start_pct"]), 2) if pd.notna(r.get("soc_start_pct")) else None,
                "energy_ev_kwh": round(float(r["energy_ev_kwh"]), 2) if pd.notna(r.get("energy_ev_kwh")) else None,
                "ev_peak_kw": round(float(r["ev_peak_kw"]), 2) if pd.notna(r.get("ev_peak_kw")) else None,
            })

    # ── Energies section ───────────────────────────────────────────────────────
    energies: dict[str, dict] = {}
    top3_ev: list[dict] = []

    if not df.empty:
        for metric in ["energy_ev_kwh", "ev_peak_kw"]:
            if metric in df.columns:
                pivot = df.pivot_table(index="date_str", columns="site", values=metric, aggfunc="first")
                energies[metric] = {
                    "pivot": pivot.reset_index().fillna("").to_dict("records"),
                    "stats": stats_rows.get(metric, []),
                }

        # Top 3 days by EV energy per site, then global rank across the whole table
        if "energy_ev_kwh" in df.columns:
            ev_df = df[["site", "date_str", "energy_ev_kwh"]].copy()
            ev_df["energy_ev_kwh"] = pd.to_numeric(ev_df["energy_ev_kwh"], errors="coerce")
            ev_df = ev_df.dropna(subset=["energy_ev_kwh"])
            ev_df = ev_df.sort_values(["site", "energy_ev_kwh", "date_str"], ascending=[True, False, True])
            top3_df = ev_df.groupby("site").head(3).copy()
            # Sort the combined table by energy descending to assign global rank
            top3_df = top3_df.sort_values("energy_ev_kwh", ascending=False).reset_index(drop=True)
            top3_df["rang_global"] = top3_df.index + 1
            for _, r in top3_df.iterrows():
                top3_ev.append({
                    "Site": r["site"],
                    "Rang": int(r["rang_global"]),
                    "Date": r["date_str"],
                    "Énergie EV (kWh)": round(float(r["energy_ev_kwh"]), 2),
                })
            # Keep sorted by global rank (already the case)

    # ── Transitions (weighted like Streamlit) ──────────────────────────────────
    transitions = []
    for _, r in df_trx.iterrows():
        total = float(r["total_transitions"]) if pd.notna(r["total_transitions"]) else 0
        jours = float(r["jours"]) if pd.notna(r["jours"]) else 0
        wd = float(r["weight_duration"]) if pd.notna(r["weight_duration"]) else 0
        sd = float(r["sum_duration"]) if pd.notna(r["sum_duration"]) else 0
        wt = float(r["weight_temp"]) if pd.notna(r["weight_temp"]) else 0
        st_ = float(r["sum_temp"]) if pd.notna(r["sum_temp"]) else 0
        transitions.append({
            "Site": label_site(r["project"]),
            "Total transitions (3→4)": int(total),
            "Moyenne/jour": round(total / jours, 2) if jours > 0 else None,
            "Durée moyenne 3→4 (min)": round(sd / wd, 2) if wd > 0 else None,
            "Température moyenne 3→4 (°C)": round(st_ / wt, 2) if wt > 0 else None,
            "Jours": int(jours),
        })

    # ── Heatmap mode 4 per site ────────────────────────────────────────────────
    heatmap_per_site: dict[str, list] = {}
    if not df_heat.empty:
        df_heat["site"] = df_heat["project"].apply(label_site)
        for site in sorted(df_heat["site"].unique()):
            sub = df_heat[df_heat["site"] == site][["hour", "avg_pct"]].copy()
            heatmap_per_site[site] = [
                {"hour": int(r["hour"]), "avg_pct": round(float(r["avg_pct"]), 2) if pd.notna(r["avg_pct"]) else 0}
                for _, r in sub.iterrows()
            ]

    # ── Status centrale ────────────────────────────────────────────────────────
    status_overall: list[dict] = []
    status_daily: list[dict] = []

    if not df_modes.empty:
        df_modes["minutes"] = pd.to_numeric(df_modes["minutes"], errors="coerce").fillna(0.0)
        df_modes["mode"] = pd.to_numeric(df_modes["mode"], errors="coerce").astype("Int64")

        pv_modes = df_modes.pivot_table(
            index=["project", "date"], columns="mode", values="minutes", aggfunc="sum", fill_value=0.0
        )
        for col in [1, 2, 3, 4]:
            if col not in pv_modes.columns:
                pv_modes[col] = 0.0
        pv_modes = pv_modes[[1, 2, 3, 4]].rename(columns={
            1: "minutes_off", 2: "minutes_standby", 3: "minutes_ac", 4: "minutes_batt"
        })
        pv_modes["minutes_total"] = pv_modes.sum(axis=1)

        if df_break.empty:
            pv_break = pd.DataFrame(0.0, index=pv_modes.index, columns=["ev0", "run2"])
        else:
            df_break["minutes"] = pd.to_numeric(df_break["minutes"], errors="coerce").fillna(0.0)
            pv_break = df_break.pivot_table(
                index=["project", "date"], columns="cat", values="minutes", aggfunc="sum", fill_value=0.0
            )
            for col in ["ev0", "run2"]:
                if col not in pv_break.columns:
                    pv_break[col] = 0.0
            pv_break = pv_break[["ev0", "run2"]]

        per_day = pv_modes.join(pv_break, how="left").fillna(0.0).reset_index()
        total_cols = ["minutes_off", "minutes_standby", "minutes_ac", "minutes_batt"]
        per_day["minutes_total"] = per_day["minutes_total"].where(
            per_day["minutes_total"] > 0, per_day[total_cols].sum(axis=1)
        )

        def _pct(num, den):
            n = pd.to_numeric(num, errors="coerce")
            d = pd.to_numeric(den, errors="coerce")
            return pd.Series(np.where(d > 0, (n / d) * 100.0, np.nan))

        per_day["pct_off"] = _pct(per_day["minutes_off"], per_day["minutes_total"])
        per_day["pct_ac"] = _pct(per_day["minutes_ac"], per_day["minutes_total"])
        per_day["pct_batt_ev"] = _pct(per_day["ev0"], per_day["minutes_total"])
        per_day["pct_batt_grid"] = _pct(per_day["run2"], per_day["minutes_total"])

        agg = per_day.groupby("project", as_index=False).agg({
            "minutes_total": "sum", "minutes_off": "sum", "minutes_ac": "sum",
            "ev0": "sum", "run2": "sum",
        })
        agg["pct_off"] = _pct(agg["minutes_off"], agg["minutes_total"])
        agg["pct_ac"] = _pct(agg["minutes_ac"], agg["minutes_total"])
        agg["pct_batt_ev"] = _pct(agg["ev0"], agg["minutes_total"])
        agg["pct_batt_grid"] = _pct(agg["run2"], agg["minutes_total"])
        agg["hours_off"] = agg["minutes_off"] / 60.0
        agg["hours_ac"] = agg["minutes_ac"] / 60.0
        agg["hours_batt_ev"] = agg["ev0"] / 60.0
        agg["hours_batt_grid"] = agg["run2"] / 60.0

        def _r(v):
            return round(float(v), 2) if pd.notna(v) else None

        for _, r in agg.sort_values("project").iterrows():
            status_overall.append({
                "Site": label_site(r["project"]),
                "% OFF": _r(r["pct_off"]),
                "Heures OFF": _r(r["hours_off"]),
                "% AC": _r(r["pct_ac"]),
                "Heures AC": _r(r["hours_ac"]),
                "% BATT recharge EV": _r(r["pct_batt_ev"]),
                "Heures BATT recharge EV": _r(r["hours_batt_ev"]),
                "% BATT recharge réseau": _r(r["pct_batt_grid"]),
                "Heures BATT recharge réseau": _r(r["hours_batt_grid"]),
            })

        daily_avg = (
            per_day.groupby("project")[["pct_off", "pct_ac", "pct_batt_ev", "pct_batt_grid"]]
            .mean().reset_index()
        )
        for _, r in daily_avg.sort_values("project").iterrows():
            status_daily.append({
                "Site": label_site(r["project"]),
                "% OFF": _r(r["pct_off"]),
                "% AC": _r(r["pct_ac"]),
                "% BATT recharge EV": _r(r["pct_batt_ev"]),
                "% BATT recharge réseau": _r(r["pct_batt_grid"]),
            })

    # ── Box plot distribution minutes_run ─────────────────────────────────────
    boxplot_minutes_run: list[dict] = []
    if timeseries:
        ts_df = pd.DataFrame(timeseries)
        ts_df["minutes_run"] = pd.to_numeric(ts_df["minutes_run"], errors="coerce")
        for site in sorted(ts_df["site"].unique()):
            vals = ts_df[ts_df["site"] == site]["minutes_run"].dropna()
            if len(vals) >= 2:
                boxplot_minutes_run.append({
                    "site": site,
                    "min": round(float(vals.min()), 2),
                    "q1": round(float(vals.quantile(0.25)), 2),
                    "median": round(float(vals.median()), 2),
                    "q3": round(float(vals.quantile(0.75)), 2),
                    "max": round(float(vals.max()), 2),
                })

    # ── Helper: distribute segment duration across all hours it spans ──────────
    def _expand_hours(df_raw: pd.DataFrame, state_col: str) -> pd.DataFrame:
        """
        Given a DataFrame with columns [project, start_time, <state_col>, delta_time_min],
        distribute each segment's duration across all calendar hours it covers.
        Returns a DataFrame with [project, hour, <state_col>, total_min].
        """
        rows = []
        for _, row in df_raw.iterrows():
            try:
                start = pd.to_datetime(row["start_time"])
                dur = float(row["delta_time_min"] or 0)
                if dur <= 0:
                    continue
                end = start + pd.Timedelta(minutes=dur)
                state = row[state_col]
                cur = start
                while cur < end:
                    next_h = (cur + pd.Timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                    next_h = min(next_h, end)
                    mins = (next_h - cur).total_seconds() / 60.0
                    rows.append({"project": row["project"], "hour": cur.hour, state_col: state, "total_min": mins})
                    cur = next_h
            except Exception:
                continue
        if not rows:
            return pd.DataFrame(columns=["project", "hour", state_col, "total_min"])
        return pd.DataFrame(rows)

    # ── Reg mode dominant per hour ─────────────────────────────────────────────
    reg_dominant_hourly: dict[str, list] = {}
    if not df_reg_dom_raw.empty:
        df_reg_dom = _expand_hours(df_reg_dom_raw, "mode")
        df_reg_dom["site"] = df_reg_dom["project"].apply(label_site)
        df_reg_dom["mode"] = pd.to_numeric(df_reg_dom["mode"], errors="coerce").astype("Int64")
        df_reg_dom["total_min"] = pd.to_numeric(df_reg_dom["total_min"], errors="coerce").fillna(0)
        agg_reg = df_reg_dom.groupby(["site", "hour", "mode"], as_index=False)["total_min"].sum()
        for site in sorted(agg_reg["site"].unique()):
            sub = agg_reg[agg_reg["site"] == site]
            site_hours = []
            for h in range(24):
                h_data = sub[sub["hour"] == h]
                if h_data.empty:
                    site_hours.append({"hour": h, "dominant_mode": None, "dominant_pct": None})
                    continue
                tot = h_data["total_min"].sum()
                best = h_data.loc[h_data["total_min"].idxmax()]
                dominant = int(best["mode"]) if pd.notna(best["mode"]) else None
                pct = round(float(best["total_min"]) / tot * 100, 1) if tot > 0 else None
                site_hours.append({"hour": h, "dominant_mode": dominant, "dominant_pct": pct})
            reg_dominant_hourly[site] = site_hours

    # ── SOC dominant per hour ──────────────────────────────────────────────────
    soc_dominant_hourly: dict[str, list] = {}
    if not df_soc_dom_raw.empty:
        df_soc_dom = _expand_hours(df_soc_dom_raw, "soc_state")
        df_soc_dom["site"] = df_soc_dom["project"].apply(label_site)
        df_soc_dom["soc_state"] = pd.to_numeric(df_soc_dom["soc_state"], errors="coerce").astype("Int64")
        df_soc_dom["total_min"] = pd.to_numeric(df_soc_dom["total_min"], errors="coerce").fillna(0)
        agg_soc = df_soc_dom.groupby(["site", "hour", "soc_state"], as_index=False)["total_min"].sum()
        for site in sorted(agg_soc["site"].unique()):
            sub = agg_soc[agg_soc["site"] == site]
            site_hours = []
            for h in range(24):
                h_data = sub[sub["hour"] == h]
                if h_data.empty:
                    site_hours.append({"hour": h, "dominant_state": None, "dominant_pct": None})
                    continue
                tot = h_data["total_min"].sum()
                best = h_data.loc[h_data["total_min"].idxmax()]
                dominant = int(best["soc_state"]) if pd.notna(best["soc_state"]) else None
                pct = round(float(best["total_min"]) / tot * 100, 1) if tot > 0 else None
                site_hours.append({"hour": h, "dominant_state": dominant, "dominant_pct": pct})
            soc_dominant_hourly[site] = site_hours

    return {
        "batteries": batteries,
        "timeseries": timeseries,
        "energies": energies,
        "top3_ev": top3_ev,
        "transitions": transitions,
        "heatmap_per_site": heatmap_per_site,
        "status_overall": status_overall,
        "status_daily": status_daily,
        "boxplot_minutes_run": boxplot_minutes_run,
        "reg_dominant_hourly": reg_dominant_hourly,
        "soc_dominant_hourly": soc_dominant_hourly,
    }

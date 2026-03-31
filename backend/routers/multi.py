from fastapi import APIRouter, Query

from backend.services.multi_comparison import (
    get_dates as cmp_dates,
    get_comparison_data,
)
from backend.services.multi_interval import (
    get_dates as interval_dates,
    get_interval_data,
)
from backend.services.multi_stats import (
    get_dates as stats_dates,
    get_stats_data,
)

router = APIRouter(tags=["multi"])


# --- Comparison ---
@router.get("/comparison/dates")
def comparison_available_dates(sites: str = Query(...)):
    return {"dates": cmp_dates(sites.split(","))}


@router.get("/comparison/data")
def comparison_data(sites: str = Query(...), date: str = Query(...)):
    return get_comparison_data(sites.split(","), date)


# --- Interval ---
@router.get("/interval/dates")
def interval_available_dates(sites: str = Query(...)):
    return {"dates": interval_dates(sites.split(","))}


@router.get("/interval/data")
def interval_data(
    sites: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    return get_interval_data(sites.split(","), start_date, end_date)


# --- Stats ---
@router.get("/stats/dates")
def stats_available_dates(sites: str = Query(...)):
    return {"dates": stats_dates(sites.split(","))}


@router.get("/stats/data")
def stats_data(
    sites: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    return get_stats_data(sites.split(","), start_date, end_date)

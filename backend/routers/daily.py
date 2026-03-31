from fastapi import APIRouter, Query

from backend.services.daily_soc import get_dates as soc_dates, get_soc_data
from backend.services.daily_regu import get_dates as regu_dates, get_regu_data
from backend.services.daily_energy import get_dates as energy_dates, get_energy_data
from backend.services.daily_power_limitation import (
    get_dates as power_lim_dates,
    get_power_limitation_data,
)

router = APIRouter(tags=["daily"])


# --- SOC ---
@router.get("/soc/dates")
def soc_available_dates(project: str = Query(...)):
    return {"dates": soc_dates(project)}


@router.get("/soc/data")
def soc_day_data(project: str = Query(...), date: str = Query(...)):
    return get_soc_data(project, date)


# --- Regulation ---
@router.get("/regu/dates")
def regu_available_dates(project: str = Query(...)):
    return {"dates": regu_dates(project)}


@router.get("/regu/data")
def regu_day_data(project: str = Query(...), date: str = Query(...)):
    return get_regu_data(project, date)


# --- Energy ---
@router.get("/energy/dates")
def energy_available_dates(project: str = Query(...)):
    return {"dates": energy_dates(project)}


@router.get("/energy/data")
def energy_day_data(project: str = Query(...), date: str = Query(...)):
    return get_energy_data(project, date)


# --- Power Limitation ---
@router.get("/power-limitation/dates")
def power_lim_available_dates(project: str = Query(...)):
    return {"dates": power_lim_dates(project)}


@router.get("/power-limitation/data")
def power_lim_day_data(project: str = Query(...), date: str = Query(...)):
    return get_power_limitation_data(project, date)

from fastapi import APIRouter, Query

from backend.services.multi_alarms import get_dates, get_alarm_data

router = APIRouter(tags=["alarms"])


@router.get("/dates")
def alarm_available_dates(sites: str = Query(...)):
    return {"dates": get_dates(sites.split(","))}


@router.get("/data")
def alarm_data(sites: str = Query(...), dates: str = Query(...)):
    return get_alarm_data(sites.split(","), dates.split(","))

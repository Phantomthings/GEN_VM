from fastapi import APIRouter, Query

from backend.services.signals import get_config, get_signals_data

router = APIRouter(tags=["signals"])


@router.get("/config")
def signals_config():
    return get_config()


@router.get("/data")
def signals_data(
    project: str = Query(...),
    date: str = Query(...),
    signals: str = Query(...),
):
    return get_signals_data(project, date, signals.split(","))

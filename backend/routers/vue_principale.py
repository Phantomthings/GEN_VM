from fastapi import APIRouter

from backend.services.vue_principale import get_alerts_j1, get_soc_morning

router = APIRouter(tags=["dashboard"])


@router.get("/alerts-j1")
def alerts_j1():
    return get_alerts_j1()


@router.get("/soc-morning")
def soc_morning():
    return get_soc_morning()

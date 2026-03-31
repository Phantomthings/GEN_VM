from fastapi import APIRouter

from backend.services.sites import get_projects, PROJECTS, MAPPING_SITES

router = APIRouter(tags=["projects"])


@router.get("/projects")
def list_projects():
    return {
        "projects": get_projects(),
        "sites": MAPPING_SITES,
    }

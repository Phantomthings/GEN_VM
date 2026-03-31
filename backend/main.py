from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import projects, vue_principale, daily, multi, alarms, signals

app = FastAPI(title="GEN_VM Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(vue_principale.router, prefix="/api/dashboard")
app.include_router(daily.router, prefix="/api/daily")
app.include_router(multi.router, prefix="/api/multi")
app.include_router(alarms.router, prefix="/api/alarms")
app.include_router(signals.router, prefix="/api/signals")

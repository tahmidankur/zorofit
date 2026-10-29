from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health

app = FastAPI(title="Zoro")

# The frontend runs on its own origin and sends X-Device-Id, which needs an explicit allow.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["X-Device-Id", "Content-Type"],
)

app.include_router(health.router)

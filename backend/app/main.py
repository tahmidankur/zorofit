from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  registers tables on Base.metadata
from app.config import settings
from app.db import Base, engine
from app.food_data import prepare_food_db
from app.routers import chat, foods, health, meals, profile, proposals, today


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    prepare_food_db()
    yield


app = FastAPI(title="Lift & Fuel", lifespan=lifespan)

# The frontend runs on its own origin and sends X-Device-Id, which needs an explicit allow.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["X-Device-Id", "X-Timezone", "Content-Type"],
)

app.include_router(health.router)
app.include_router(profile.router)
app.include_router(meals.router)
app.include_router(today.router)
app.include_router(foods.router)
app.include_router(chat.router)
app.include_router(proposals.router)

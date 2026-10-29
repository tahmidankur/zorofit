from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.food_data import prepare_food_db
from app.migrate import run_migrations
from app.routers import chat, demo, foods, health, meals, profile, proposals, today, workouts


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    prepare_food_db()
    yield


app = FastAPI(title="Lift & Fuel", lifespan=lifespan)

# The frontend runs on its own origin and sends X-Device-Id, which needs an explicit allow.
# FRONTEND_ORIGIN may list several origins, comma-separated (for example the site and a local preview).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
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
app.include_router(workouts.router)
app.include_router(demo.router)

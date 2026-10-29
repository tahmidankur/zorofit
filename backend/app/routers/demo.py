import sqlite3

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_profile
from app.food_data import get_food_db
from app.models import Profile
from app.ratelimit import DEMO, enforce
from app.services.demo import load_demo_week

router = APIRouter(prefix="/api/demo")


@router.post("")
def load_demo(
    request: Request,
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
    foods_db: sqlite3.Connection = Depends(get_food_db),
):
    enforce(DEMO, request, "Demo data was loaded several times from this network. Try again later.")
    return load_demo_week(db, foods_db, profile)

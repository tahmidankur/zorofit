from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_profile
from app.models import Profile
from app.schemas import Targets, TodayOut
from app.services.meals import meals_on, today_for
from app.services.nutrition import day_totals
from app.services.workouts import ensure_planned

router = APIRouter(prefix="/api/today")


@router.get("", response_model=TodayOut)
def read_today(
    date: date | None = None,
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
):
    day = date or today_for(profile)
    meals = meals_on(db, profile.device_id, day)
    return TodayOut(
        date=day,
        targets=Targets(kcal=profile.calorie_target, protein_g=profile.protein_target_g),
        totals=day_totals(meals),
        meals=meals,
        workout=ensure_planned(db, profile, day),
    )

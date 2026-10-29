from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_profile
from app.models import Profile, Workout
from app.schemas import TemplateOut, WorkoutOut, WorkoutStatusIn
from app.services.workout_gen import load_templates
from app.services.workouts import get_for_device

router = APIRouter(prefix="/api/workouts")


@router.get("/templates", response_model=list[TemplateOut])
def list_templates():
    return [TemplateOut(id=template["id"], name=template["name"]) for template in load_templates().values()]


@router.get("", response_model=list[WorkoutOut])
def list_workouts(
    limit: int = Query(60, ge=1, le=200), profile: Profile = Depends(get_profile), db: Session = Depends(get_db)
):
    query = (
        select(Workout)
        .where(Workout.device_id == profile.device_id)
        .order_by(Workout.local_date.desc(), Workout.id.desc())
        .limit(limit)
    )
    return list(db.scalars(query))


@router.put("/{workout_id}/status", response_model=WorkoutOut)
def set_status(
    workout_id: int, body: WorkoutStatusIn, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)
):
    workout = get_for_device(db, profile.device_id, workout_id)
    workout.status = body.status
    db.commit()
    return workout

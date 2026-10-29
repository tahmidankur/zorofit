from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Profile, Proposal, Workout
from app.services import workout_gen


def plan_for(profile: Profile, day: date, minutes: int | None = None, focus: str | None = None) -> dict:
    return workout_gen.generate(
        profile.template_id, profile.equipment, minutes or profile.session_minutes, profile.goal, day, focus
    )


def workout_on(db: Session, device_id: str, day: date) -> Workout | None:
    query = select(Workout).where(Workout.device_id == device_id, Workout.local_date == day).order_by(Workout.id.desc())
    return db.scalars(query).first()


def ensure_planned(db: Session, profile: Profile, day: date) -> Workout | None:
    existing = workout_on(db, profile.device_id, day)
    if existing or day.weekday() not in profile.training_days:
        return existing
    workout = save_plan(db, profile, day, plan_for(profile, day))
    db.commit()
    return workout


def save_plan(db: Session, profile: Profile, day: date, plan: dict) -> Workout:
    workout = workout_on(db, profile.device_id, day)
    if workout is None:
        workout = Workout(device_id=profile.device_id, local_date=day)
        db.add(workout)
    workout.template_id = plan["template_id"]
    workout.minutes_planned = plan["minutes_planned"]
    workout.exercises = plan
    workout.status = "planned"
    db.flush()
    return workout


def apply_workout_proposal(db: Session, profile: Profile, proposal: Proposal) -> None:
    day = date.fromisoformat(proposal.payload["local_date"])
    save_plan(db, profile, day, proposal.payload["workout"])


def get_for_device(db: Session, device_id: str, workout_id: int) -> Workout:
    workout = db.get(Workout, workout_id)
    if workout is None or workout.device_id != device_id:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout

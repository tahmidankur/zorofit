from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_profile
from app.models import Profile
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/api/profile")


@router.get("", response_model=ProfileOut)
def read_profile(profile: Profile = Depends(get_profile)):
    return profile


@router.put("", response_model=ProfileOut)
def update_profile(body: ProfileIn, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    for field, value in body.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    return profile

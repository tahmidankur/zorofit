import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Profile
from app.schemas import check_timezone


def get_device_id(x_device_id: str = Header()) -> str:
    try:
        return str(uuid.UUID(x_device_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Device-Id must be a UUID")


def _browser_timezone(value: str | None) -> str:
    if not value:
        return "UTC"
    try:
        return check_timezone(value)
    except ValueError:
        return "UTC"


def get_profile(
    device_id: str = Depends(get_device_id),
    x_timezone: str | None = Header(None),
    db: Session = Depends(get_db),
) -> Profile:
    profile = db.get(Profile, device_id)
    if profile is None:
        # A new device gets usable defaults so Today works before the profile form is filled in.
        profile = Profile(device_id=device_id, timezone=_browser_timezone(x_timezone))
        db.add(profile)
        db.commit()
    return profile

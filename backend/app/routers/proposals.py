import sqlite3

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_profile
from app.food_data import get_food_db
from app.models import Profile
from app.schemas import ProposalEdit, ProposalOut
from app.services import proposals

router = APIRouter(prefix="/api/proposals")


@router.put("/{proposal_id}", response_model=ProposalOut)
def edit_proposal(
    proposal_id: str,
    body: ProposalEdit,
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
    foods_db: sqlite3.Connection = Depends(get_food_db),
):
    proposal = proposals.get_for_device(db, profile.device_id, proposal_id)
    return proposals.to_out(db, proposals.apply_edit(db, foods_db, proposal, body))


@router.post("/{proposal_id}/confirm", response_model=ProposalOut)
def confirm_proposal(proposal_id: str, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return proposals.to_out(db, proposals.confirm(db, profile, proposal_id))


@router.post("/{proposal_id}/discard", response_model=ProposalOut)
def discard_proposal(proposal_id: str, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return proposals.to_out(db, proposals.discard(db, profile.device_id, proposal_id))

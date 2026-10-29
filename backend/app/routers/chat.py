import sqlite3
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_profile
from app.food_data import get_food_db
from app.models import ChatMessage, Profile, Proposal, utcnow
from app.ratelimit import CHAT, enforce
from app.schemas import ChatIn, ChatMessageOut
from app.services import chat, proposals
from app.services.llm import get_interpreter
from app.services.llm.base import Interpreter

router = APIRouter(prefix="/api/chat")

HISTORY_LIMIT = 60


def message_out(db: Session, message: ChatMessage, fallback_query: str | None = None) -> ChatMessageOut:
    proposal = db.get(Proposal, message.proposal_id) if message.proposal_id else None
    return ChatMessageOut(
        id=message.id,
        role=message.role,
        text=message.text,
        created_at=message.created_at,
        proposal=proposals.to_out(db, proposal) if proposal else None,
        fallback_query=fallback_query,
    )


def user_messages_since(db: Session, since, device_id: str | None = None) -> int:
    query = select(func.count(ChatMessage.id)).where(ChatMessage.role == "user", ChatMessage.created_at >= since)
    if device_id is not None:
        query = query.where(ChatMessage.device_id == device_id)
    return db.scalar(query)


def check_rate_limit(db: Session, device_id: str, request: Request) -> None:
    now = utcnow()
    if user_messages_since(db, now - timedelta(hours=1), device_id) >= settings.chat_limit_per_hour:
        raise HTTPException(status_code=429, detail="That's a lot of messages this hour. Try again a bit later.")
    # Device ids are free to mint, so the network limit is what actually bounds one person's use.
    enforce(CHAT, request, "That's a lot of messages from this network this hour. Try again a bit later.")
    # Every message can cost a model call on the project's key; this caps the whole app's daily spend.
    if user_messages_since(db, now - timedelta(days=1)) >= settings.chat_daily_limit:
        raise HTTPException(status_code=429, detail="Zoro has hit today's message limit. Log meals by hand for now.")


@router.get("", response_model=list[ChatMessageOut])
def history(profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    query = (
        select(ChatMessage)
        .where(ChatMessage.device_id == profile.device_id)
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_LIMIT)
    )
    messages = list(db.scalars(query))[::-1]
    return [message_out(db, message) for message in messages]


@router.post("", response_model=list[ChatMessageOut])
def send(
    body: ChatIn,
    request: Request,
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
    foods_db: sqlite3.Connection = Depends(get_food_db),
    interpreter: Interpreter = Depends(get_interpreter),
):
    check_rate_limit(db, profile.device_id, request)
    text = body.message.strip()
    user_message = chat.save_message(db, profile.device_id, "user", text)
    turn = chat.Turn(db=db, foods_db=foods_db, profile=profile)
    replies = chat.run(turn, text, interpreter)
    saved = [(chat.save_message(db, profile.device_id, "zoro", reply.text, reply.proposal), reply) for reply in replies]
    db.commit()
    return [message_out(db, user_message)] + [message_out(db, message, reply.fallback_query) for message, reply in saved]

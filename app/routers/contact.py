from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app.config import get_settings
from app.schemas import ContactMessageCreate, ContactMessageOut
from app.security import require_admin

# DB-backed version disabled for now — using YAML file storage (see app/storage.py)
# from sqlalchemy import func, select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.database import get_db
# from app.models import ContactMessage

router = APIRouter(prefix="/api", tags=["contact"])
settings = get_settings()


def _check_rate_limit(email: str) -> None:
    window_start = datetime.now(timezone.utc) - timedelta(seconds=settings.apply_rate_limit_window_seconds)
    recent = [
        m
        for m in storage.find_all_by("contact_messages", email=email.lower())
        if m.get("created_at", "") >= window_start.isoformat()
    ]
    if len(recent) >= settings.apply_rate_limit_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages submitted recently. Please try again later.",
        )


@router.post(
    "/contact",
    response_model=ContactMessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_contact_message(payload: ContactMessageCreate):
    _check_rate_limit(payload.email)

    message = storage.insert(
        "contact_messages",
        {
            "full_name": payload.full_name,
            "email": payload.email.lower(),
            "phone": payload.phone,
            "matter_type": payload.matter_type,
            "message": payload.message,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    # In production: send a notification email to ipmarkandmind@gmail.com here
    # (e.g. via a simple smtplib call or a transactional email API like Resend/SendGrid).

    return message


@router.get(
    "/contact",
    response_model=list[ContactMessageOut],
    dependencies=[Depends(require_admin)],
)
async def list_contact_messages():
    messages = storage.list_all("contact_messages")
    messages.sort(key=lambda m: m.get("created_at", ""), reverse=True)
    return messages

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import ContactMessage
from app.schemas import ContactMessageCreate, ContactMessageOut
from app.security import require_admin

router = APIRouter(prefix="/api", tags=["contact"])
settings = get_settings()


async def _check_rate_limit(db: AsyncSession, email: str) -> None:
    window_start = datetime.now(timezone.utc) - timedelta(seconds=settings.apply_rate_limit_window_seconds)
    result = await db.execute(
        select(func.count()).select_from(ContactMessage).where(
            ContactMessage.email == email.lower(),
            ContactMessage.created_at >= window_start,
        )
    )
    count = result.scalar_one()
    if count >= settings.apply_rate_limit_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages submitted recently. Please try again later.",
        )


@router.post(
    "/contact",
    response_model=ContactMessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_contact_message(payload: ContactMessageCreate, db: AsyncSession = Depends(get_db)):
    await _check_rate_limit(db, payload.email)

    message = ContactMessage(
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        matter_type=payload.matter_type,
        message=payload.message,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # In production: send a notification email to ipmarkandmind@gmail.com here
    # (e.g. via a simple smtplib call or a transactional email API like Resend/SendGrid).

    return message


@router.get(
    "/contact",
    response_model=list[ContactMessageOut],
    dependencies=[Depends(require_admin)],
)
async def list_contact_messages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).order_by(ContactMessage.created_at.desc()))
    return result.scalars().all()

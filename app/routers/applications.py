import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Application, Job
from app.schemas import ApplicationOut, ApplicationStatusUpdate
from app.security import require_admin

router = APIRouter(prefix="/api", tags=["applications"])
settings = get_settings()


def _validate_resume(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_resume_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resume must be one of: {', '.join(settings.allowed_resume_types)}",
        )


async def _check_rate_limit(db: AsyncSession, email: str) -> None:
    """DB-backed rate limit: blocks an email from submitting more than
    `apply_rate_limit_count` applications within the configured window."""
    window_start = datetime.now(timezone.utc) - timedelta(seconds=settings.apply_rate_limit_window_seconds)
    result = await db.execute(
        select(func.count()).select_from(Application).where(
            Application.email == email.lower(),
            Application.created_at >= window_start,
        )
    )
    count = result.scalar_one()
    if count >= settings.apply_rate_limit_count:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many applications submitted recently. Please try again later.",
        )


@router.post(
    "/jobs/{slug}/apply",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
async def apply_to_job(
    slug: str,
    full_name: str = Form(..., max_length=120),
    email: str = Form(...),
    phone: str = Form(..., max_length=20),
    cover_note: str | None = Form(None),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    await _check_rate_limit(db, email)

    result = await db.execute(select(Job).where(Job.slug == slug, Job.is_active.is_(True)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    _validate_resume(resume)

    contents = await resume.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Resume must be under {settings.max_upload_mb}MB",
        )

    job_dir = os.path.join(settings.upload_dir, str(job.id))
    os.makedirs(job_dir, exist_ok=True)

    ext = Path(resume.filename or "").suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(job_dir, stored_name)

    with open(stored_path, "wb") as f:
        f.write(contents)

    application = Application(
        job_id=job.id,
        full_name=full_name,
        email=email.lower(),
        phone=phone,
        cover_note=cover_note,
        resume_filename=resume.filename or stored_name,
        resume_path=stored_path,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    # In production: send a confirmation email to the applicant and a
    # notification to ipmarkandmind@gmail.com here (e.g. via a simple
    # smtplib call or a transactional email API like Resend/SendGrid).

    return application


# ---------- Admin routes ----------

@router.get(
    "/jobs/{slug}/applications",
    response_model=list[ApplicationOut],
    dependencies=[Depends(require_admin)],
)
async def list_applications_for_job(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.slug == slug))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    result = await db.execute(
        select(Application).where(Application.job_id == job.id).order_by(Application.created_at.desc())
    )
    return result.scalars().all()


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationOut,
    dependencies=[Depends(require_admin)],
)
async def update_application_status(
    application_id: uuid.UUID, payload: ApplicationStatusUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Application).where(Application.id == application_id))
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    application.status = payload.status
    await db.commit()
    await db.refresh(application)
    return application

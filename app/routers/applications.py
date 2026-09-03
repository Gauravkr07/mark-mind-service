import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app import storage
from app.config import get_settings
from app.models import ApplicationStatus
from app.schemas import ApplicationOut, ApplicationStatusUpdate
from app.security import require_admin

# DB-backed version disabled for now — using YAML file storage (see app/storage.py)
# from sqlalchemy import func, select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.database import get_db
# from app.models import Application, Job

router = APIRouter(prefix="/api", tags=["applications"])
settings = get_settings()


def _validate_resume(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_resume_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resume must be one of: {', '.join(settings.allowed_resume_types)}",
        )


def _check_rate_limit(email: str) -> None:
    """File-backed rate limit: blocks an email from submitting more than
    `apply_rate_limit_count` applications within the configured window."""
    window_start = datetime.now(timezone.utc) - timedelta(seconds=settings.apply_rate_limit_window_seconds)
    recent = [
        a
        for a in storage.find_all_by("applications", email=email.lower())
        if a.get("created_at", "") >= window_start.isoformat()
    ]
    if len(recent) >= settings.apply_rate_limit_count:
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
):
    _check_rate_limit(email)

    job = storage.get_by("jobs", slug=slug, is_active=True)
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

    job_dir = os.path.join(settings.upload_dir, str(job["id"]))
    os.makedirs(job_dir, exist_ok=True)

    ext = Path(resume.filename or "").suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(job_dir, stored_name)

    with open(stored_path, "wb") as f:
        f.write(contents)

    application = storage.insert(
        "applications",
        {
            "job_id": job["id"],
            "full_name": full_name,
            "email": email.lower(),
            "phone": phone,
            "cover_note": cover_note,
            "resume_filename": resume.filename or stored_name,
            "resume_path": stored_path,
            "status": ApplicationStatus.received.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

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
async def list_applications_for_job(slug: str):
    job = storage.get_by("jobs", slug=slug)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    apps = storage.find_all_by("applications", job_id=job["id"])
    apps.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    return apps


@router.patch(
    "/applications/{application_id}",
    response_model=ApplicationOut,
    dependencies=[Depends(require_admin)],
)
async def update_application_status(application_id: uuid.UUID, payload: ApplicationStatusUpdate):
    application = storage.update("applications", str(application_id), {"status": payload.status.value})
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application

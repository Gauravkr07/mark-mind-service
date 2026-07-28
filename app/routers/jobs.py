import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job
from app.schemas import JobCreate, JobListItem, JobOut, JobUpdate
from app.security import require_admin

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListItem])
async def list_active_jobs(db: AsyncSession = Depends(get_db)):
    """Public endpoint — plain DB read. Job postings change rarely enough that
    a cache isn't needed at this scale; add one back later if traffic grows."""
    result = await db.execute(select(Job).where(Job.is_active.is_(True)).order_by(Job.created_at.desc()))
    return result.scalars().all()


@router.get("/{slug}", response_model=JobOut)
async def get_job(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.slug == slug, Job.is_active.is_(True)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


# ---------- Admin routes ----------

@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Job).where(Job.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A job with this slug already exists")

    job = Job(**payload.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.patch("/{job_id}", response_model=JobOut, dependencies=[Depends(require_admin)])
async def update_job(job_id: uuid.UUID, payload: JobUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    await db.delete(job)
    await db.commit()

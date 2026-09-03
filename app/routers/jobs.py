import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app import storage
from app.schemas import JobCreate, JobListItem, JobOut, JobUpdate
from app.security import require_admin

# DB-backed version disabled for now — using YAML file storage (see app/storage.py)
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.database import get_db
# from app.models import Job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobListItem])
async def list_active_jobs():
    """Public endpoint — plain YAML read. Job postings change rarely enough that
    a cache isn't needed at this scale; add one back later if traffic grows."""
    jobs = [j for j in storage.list_all("jobs") if j.get("is_active")]
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs


@router.get("/{slug}", response_model=JobOut)
async def get_job(slug: str):
    job = storage.get_by("jobs", slug=slug, is_active=True)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


# ---------- Admin routes ----------

@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_job(payload: JobCreate):
    if storage.get_by("jobs", slug=payload.slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A job with this slug already exists")

    now = datetime.now(timezone.utc).isoformat()
    job = storage.insert(
        "jobs",
        {
            **payload.model_dump(mode="json"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    )
    return job


@router.patch("/{job_id}", response_model=JobOut, dependencies=[Depends(require_admin)])
async def update_job(job_id: uuid.UUID, payload: JobUpdate):
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_at"] = datetime.now(timezone.utc).isoformat()

    job = storage.update("jobs", str(job_id), changes)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
async def delete_job(job_id: uuid.UUID):
    if not storage.delete("jobs", str(job_id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

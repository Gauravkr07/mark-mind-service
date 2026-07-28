import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ApplicationStatus, EmploymentType


# ---------- Job schemas ----------

class JobBase(BaseModel):
    title: str = Field(..., max_length=160)
    department: str = Field(..., max_length=80)
    location: str = Field(default="New Delhi, India", max_length=120)
    employment_type: EmploymentType = EmploymentType.full_time
    summary: str = Field(..., max_length=300)
    description: str
    requirements: str


class JobCreate(JobBase):
    slug: str = Field(..., max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class JobUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType | None = None
    summary: str | None = None
    description: str | None = None
    requirements: str | None = None
    is_active: bool | None = None


class JobOut(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    is_active: bool
    created_at: datetime


class JobListItem(BaseModel):
    """Slim shape used for the cached public listing endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    department: str
    location: str
    employment_type: EmploymentType
    summary: str


# ---------- Application schemas ----------

class ApplicationCreate(BaseModel):
    full_name: str = Field(..., max_length=120)
    email: EmailStr
    phone: str = Field(..., max_length=20)
    cover_note: str | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    full_name: str
    email: str
    phone: str
    status: ApplicationStatus
    resume_filename: str
    created_at: datetime


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


# ---------- Contact message schemas ----------

class ContactMessageCreate(BaseModel):
    full_name: str = Field(..., max_length=120)
    email: EmailStr
    phone: str = Field(..., max_length=20)
    matter_type: str = Field(..., max_length=80)
    message: str = Field(..., max_length=4000)


class ContactMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    phone: str
    matter_type: str
    message: str
    created_at: datetime

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import get_settings
from app.database import Base, engine
from app.routers import applications, contact, jobs

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: auto-create tables. For production, use Alembic migrations instead.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Mark & Mind Careers API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(contact.router)


@app.get("/health")
async def health():
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {"status": "ok" if db_ok else "degraded", "postgres": db_ok}


# Serve the careers page directly at /careers as a user-friendly route.
@app.get("/careers")
async def careers_page():
    return FileResponse("app/static/careers.html")


# Serve the website pages and assets from app/static at the root path.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

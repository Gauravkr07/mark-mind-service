# DB usage disabled for now — switched to YAML file storage (see app/storage.py).
# Left here commented out so it's easy to switch back to Postgres later.

# from collections.abc import AsyncGenerator
#
# from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
# from sqlalchemy.orm import DeclarativeBase
#
# from app.config import get_settings
#
# settings = get_settings()
#
# engine = create_async_engine(
#     settings.database_url,
#     echo=False,
#     pool_pre_ping=True,
#     pool_size=10,
#     max_overflow=20,
# )
#
# AsyncSessionLocal = async_sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
# )
#
#
# class Base(DeclarativeBase):
#     pass
#
#
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with AsyncSessionLocal() as session:
#         yield session

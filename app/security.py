from fastapi import Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


async def require_admin(x_admin_key: str = Header(...)) -> None:
    """
    Minimal header-based auth for admin-only routes (create/update jobs, view applications).
    Swap this for JWT + RBAC later if you need multiple admin users or roles.
    """
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from . import config

security = HTTPBasic()


def require_hr_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Gate for HR-facing pages (dashboard, create, detail). The assignee's
    /update/<token> link deliberately does NOT use this — it's secured by
    the unguessable per-incident token instead."""
    valid_password = config.ADMIN_CREDENTIALS.get(credentials.username)
    is_valid = valid_password is not None and secrets.compare_digest(credentials.password, valid_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HR credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

import os
import uuid as uuid_module
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Doctor, Patient

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRES_DAYS = 7

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRES_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@dataclass
class AuthenticatedUser:
    id: UUID
    role: str
    name: str
    email: str


def _load_user(db: Session, raw_user_id: str, role: str) -> Optional[AuthenticatedUser]:
    try:
        user_id = uuid_module.UUID(raw_user_id)
    except (ValueError, AttributeError, TypeError):
        return None

    if role == "doctor":
        row = db.query(Doctor).filter(Doctor.id == user_id).first()
    elif role == "patient":
        row = db.query(Patient).filter(Patient.id == user_id).first()
    else:
        return None

    if not row:
        return None
    return AuthenticatedUser(id=row.id, role=role, name=row.name, email=row.email)


def get_current_user(required_role: Optional[str] = None) -> Callable[..., AuthenticatedUser]:
    """FastAPI dependency factory. Decodes the bearer token, loads the
    Doctor/Patient row it refers to, and enforces `required_role` if given.
    """

    def _dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
        db: Session = Depends(get_db),
    ) -> AuthenticatedUser:
        if not credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        try:
            payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        role = payload.get("role")
        raw_user_id = payload.get("sub")
        if not role or not raw_user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        if required_role and role != required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"This action requires a {required_role} account")

        user = _load_user(db, raw_user_id, role)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    return _dependency

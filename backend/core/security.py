from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from core.config import get_settings
from models.database_models import User

settings = get_settings()

# IMPORTANT: Remove bcrypt rounds customization
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)



def _safe_password(password: str) -> str:
    """
    Force password to max 72 bytes (bcrypt limit)
    """
    return password.encode("utf-8")[:72].decode("utf-8", "ignore")


def get_password_hash(password: str) -> str:
    safe = _safe_password(password)
    return pwd_context.hash(safe)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    safe = _safe_password(plain_password)
    return pwd_context.verify(safe, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=15)
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

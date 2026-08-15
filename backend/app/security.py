"""security.py - password hashing and JWT access tokens."""
import uuid
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings
from security.token_manager import is_denylisted

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_minutes: int = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES
    )
    # jti lets a single token be revoked early (logout, device revoke)
    # without invalidating every other token for the user - see
    # security/token_manager.py.
    payload = {"sub": subject, "exp": expire, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if is_denylisted(payload.get("jti")):
            return None
        return payload.get("sub")
    except JWTError:
        return None


def decode_access_token_payload(token: str):
    """Full payload (sub, exp, jti) - used by /auth/logout to denylist the
    current token's jti. Returns None if the token is malformed/expired."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None

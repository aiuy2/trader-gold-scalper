"""encryption.py - symmetric encryption for values that must be stored
(MT5 account passwords) but never kept in plaintext. Used by
services/account_service.py.

Uses Fernet (AES-128-CBC + HMAC, via the `cryptography` package, already
in requirements.txt). The key is read from the ENCRYPTION_KEY env var; if
unset, a key is derived from JWT_SECRET so local/dev setups still work
without extra config - set ENCRYPTION_KEY explicitly in production so
rotating JWT_SECRET doesn't also break stored passwords.
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _derive_key(raw: str) -> bytes:
    """Turn an arbitrary secret string into a valid 32-byte urlsafe-base64
    Fernet key."""
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    raw_key = os.getenv("ENCRYPTION_KEY") or settings.JWT_SECRET
    return Fernet(_derive_key(raw_key))


def encrypt_value(plaintext: str) -> str:
    if plaintext is None:
        return None
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    if ciphertext is None:
        return None
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Could not decrypt value - wrong key or corrupted data.")

"""
Password hashing (Argon2).

Note: authentication/login has been removed from this application (see
app/core/dependencies.py). These helpers are kept only because the demo
seed scripts (app/seed/*) still populate a hashed_password column on the
users table for record-keeping; nothing verifies a password anymore.
"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

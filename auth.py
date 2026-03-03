from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import hashlib

SECRET_KEY = "secretkey123"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ================= PASSWORD HASH =================
def hash_password(password: str):
    # bcrypt only accepts 72 bytes → pre-hash first (industry standard fix)
    password_bytes = password.encode("utf-8")
    safe_password = hashlib.sha256(password_bytes).hexdigest()
    return pwd_context.hash(safe_password)


# ================= VERIFY =================
def verify_password(plain, hashed):
    plain_bytes = plain.encode("utf-8")
    safe_plain = hashlib.sha256(plain_bytes).hexdigest()
    return pwd_context.verify(safe_plain, hashed)


# ================= TOKEN =================
def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
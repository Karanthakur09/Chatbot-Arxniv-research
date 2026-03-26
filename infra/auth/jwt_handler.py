from datetime import datetime, timedelta
from jose import jwt, JWTError

from shared.config import settings


ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: int = 60 * 24):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
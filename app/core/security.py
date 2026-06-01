from pwdlib import PasswordHash
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from jose import jwt

pwd_hash=PasswordHash.recommended()

def hash_password(password) -> str:
    return pwd_hash.hash(password)

def verify_password(password, hashed_password) -> bool:
    return pwd_hash.verify(password, hashed_password)

def create_jwt_token(data:dict):
    to_encode=data.copy()

    expire=datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})

    token=jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    return token

def create_refresh_token(data:dict):
    to_encode=data.copy()

    expire=datetime.now(timezone.utc)+timedelta(days=settings.refresh_token_expire_days)

    to_encode.update({"exp": expire, "type": "refresh"})

    token=jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    return token

def verify_token(token:str):
    try:
        payload=jwt.decode(token,settings.secret_key,algorithms=[settings.algorithm]) 
        return payload
    except:
        return None







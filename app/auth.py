import secrets
import hashlib
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from .database import get_db
from .models import Agent

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    token = secrets.token_urlsafe(32)
    return f"pred_{token}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_current_agent(
    api_key: str = Security(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> Agent:
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Add header: X-API-Key: pred_..."
        )
    key_hash = hash_api_key(api_key)
    agent = db.query(Agent).filter(Agent.api_key_hash == key_hash).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    if not agent.is_active:
        raise HTTPException(status_code=403, detail="Account suspended.")
    return agent
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from infra.db.session import SessionLocal
from core.auth.service import AuthService
from infra.auth.jwt_handler import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


# -------------------------
# DB Dependency
# -------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------
# Schemas
# -------------------------

class AuthRequest(BaseModel):
    email: str
    password: str


# -------------------------
# Routes
# -------------------------

@router.post("/signup")
def signup(req: AuthRequest, db: Session = Depends(get_db)):

    service = AuthService(db)

    user, error = service.signup(req.email, req.password)

    if error:
        return {"error": error}

    return {"message": "User created successfully"}


@router.post("/login")
def login(req: AuthRequest, db: Session = Depends(get_db)):

    service = AuthService(db)

    user = service.login(req.email, req.password)

    if not user:
        return {"error": "Invalid credentials"}

    token = create_access_token({"user_id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer"
    }
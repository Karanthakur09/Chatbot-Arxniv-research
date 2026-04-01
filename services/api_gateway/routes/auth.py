from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession 
from core.auth.service import AuthService
from infra.auth.jwt_handler import create_access_token
from services.api_gateway.dependencies.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


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
# 2. Add 'async' to the function
async def signup(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    
    # 3. Add 'await' (Your AuthService must also be updated to async!)
    user, error = await service.signup(req.email, req.password)

    if error:
        return {"error": error}
    return {"message": "User created successfully"}

@router.post("/login")
# 4. Add 'async' here too
async def login(req: AuthRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    
    # 5. Add 'await'
    user = await service.login(req.email, req.password)

    if not user:
        return {"error": "Invalid credentials"}

    token = create_access_token({"user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer"
    }
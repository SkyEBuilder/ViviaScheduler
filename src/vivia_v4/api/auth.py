from fastapi import APIRouter, HTTPException, Header, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Annotated
from vivia_v4.api.config import settings
from vivia_v4.api.manager import UserManager

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: EmailStr

class AdminRegisterRequest(BaseModel):
    email: EmailStr
    admin_secret: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    api_key: str
    is_active: bool

async def get_current_user(x_api_key: Annotated[str | None, Header()] = None) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key header")
    
    user = UserManager.get_user_by_key(x_api_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
        
    if not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        
    return user

@router.post("/register")
async def register(request: RegisterRequest):
    """
    Public registration endpoint.
    Currently a placeholder.
    """
    return {
        "message": "Public registration is currently unavailable. Please contact the administrator or use the admin registration endpoint if you have the secret."
    }

@router.post("/admin/register", response_model=UserResponse)
async def admin_register(request: AdminRegisterRequest):
    """
    Admin registration endpoint.
    Creates an active user directly if the secret is correct.
    """
    if request.admin_secret != settings.admin_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin secret")
    
    try:
        user = UserManager.create_user(email=request.email, is_active=True)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

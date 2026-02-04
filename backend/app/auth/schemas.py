"""
Pydantic schemas pour l'authentification
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
import uuid


class UserCreate(BaseModel):
    """Schema pour la création d'un utilisateur"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Mot de passe (8 caractères minimum)")
    full_name: str = Field(..., min_length=2, max_length=100, description="Nom complet")


class UserLogin(BaseModel):
    """Schema pour la connexion"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema de réponse utilisateur (sans mot de passe)"""
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema pour les tokens JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema pour les données extraites du token"""
    user_id: Optional[str] = None
    email: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Schema pour la requête de refresh token"""
    refresh_token: str

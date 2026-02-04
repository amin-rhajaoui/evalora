"""
Router d'authentification pour Evalora
Endpoints: register, login, me, refresh
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.database import get_db
from ..db.models import User
from ..auth.schemas import UserCreate, UserLogin, UserResponse, Token, RefreshTokenRequest
from ..auth.utils import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from ..auth.dependencies import get_current_user
from ..config import logger

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Inscription d'un nouvel utilisateur

    - **email**: Adresse email (unique)
    - **password**: Mot de passe (8 caractères minimum)
    - **full_name**: Nom complet
    """
    # Vérifier si l'email existe déjà
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà utilisé"
        )

    # Créer l'utilisateur
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"Nouvel utilisateur inscrit: {user.email}")
    return user


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Connexion utilisateur

    Retourne un access token et un refresh token
    """
    # Rechercher l'utilisateur
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    # Vérifier les credentials
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    # Vérifier si le compte est actif
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce compte a été désactivé"
        )

    # Générer les tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"Connexion réussie: {user.email}")
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Récupère le profil de l'utilisateur connecté

    Nécessite un token d'accès valide
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Renouvelle le token d'accès à partir du refresh token

    - **refresh_token**: Le refresh token obtenu lors de la connexion
    """
    payload = decode_token(request.refresh_token)

    # Vérifier que c'est un refresh token valide
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide"
        )

    # Récupérer l'utilisateur
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce compte a été désactivé"
        )

    # Générer de nouveaux tokens
    new_access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"Token rafraîchi pour: {user.email}")
    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Déconnexion (côté serveur, on log juste l'action)

    Note: La vraie déconnexion se fait côté client en supprimant les tokens
    """
    logger.info(f"Déconnexion: {current_user.email}")
    return {"message": "Déconnexion réussie"}

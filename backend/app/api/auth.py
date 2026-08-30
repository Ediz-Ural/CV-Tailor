from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.generated_cv import GeneratedCV
from app.models.user import User
from app.schemas.auth import DeleteAccountRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
DELETE_ACCOUNT_CONFIRMATION = "HESABIMI SIL"


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbSession) -> User:
    if not payload.kvkk_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kayıt için KVKK açık rızası zorunludur",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        kvkk_consent_at=datetime.now(UTC),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi zaten kayıtlı",
        ) from None
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya parola hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> User:
    return current_user


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(payload: DeleteAccountRequest, db: DbSession, current_user: CurrentUser) -> Response:
    if payload.confirmation != DELETE_ACCOUNT_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hesap silmek icin confirmation alani '{DELETE_ACCOUNT_CONFIRMATION}' olmalidir",
        )

    pdf_paths = db.scalars(
        select(GeneratedCV.pdf_path).where(
            GeneratedCV.user_id == current_user.id,
            GeneratedCV.pdf_path.is_not(None),
        )
    ).all()
    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        if path.exists() and path.is_file():
            path.unlink()

    db.delete(current_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.db.session import get_db
from app.models.llm_credential import LLMCredential
from app.schemas.llm_credential import LLMCredentialResponse, LLMCredentialUpsert
from app.services.llm import LLMConfigurationError, LLMError, LLMService
from app.services.llm_credentials import delete_credential, read_credential, store_credential

router = APIRouter(prefix="/llm-credential", tags=["llm-credential"])
DbSession = Annotated[Session, Depends(get_db)]


def get_verification_service(payload: LLMCredentialUpsert) -> LLMService:
    return LLMService(
        settings.model_copy(
            update={
                "llm_provider": payload.provider,
                "llm_model": payload.model,
                "llm_api_key": payload.api_key,
            }
        )
    )


VerificationService = Annotated[LLMService, Depends(get_verification_service)]


@router.get("", response_model=LLMCredentialResponse)
def read_llm_credential(db: DbSession, current_user: CurrentUser) -> LLMCredential:
    credential = read_credential(db, current_user.id)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıtlı bir API anahtarı yok")
    return credential


@router.put("", response_model=LLMCredentialResponse)
async def upsert_llm_credential(
    payload: LLMCredentialUpsert,
    db: DbSession,
    current_user: CurrentUser,
    verification_service: VerificationService,
) -> LLMCredential:
    # Fail here rather than several minutes into a pipeline run.
    try:
        await verification_service.verify_credentials()
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return store_credential(
        db,
        current_user.id,
        provider=payload.provider,
        model=payload.model,
        api_key=payload.api_key,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def remove_llm_credential(db: DbSession, current_user: CurrentUser) -> Response:
    if not delete_credential(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kayıtlı bir API anahtarı yok")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

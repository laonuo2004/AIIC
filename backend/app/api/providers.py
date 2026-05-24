from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, current_user
from app.models.entities import User
from app.schemas.providers import (
    OpenRouterConfigResponse,
    OpenRouterKeyRequest,
    OpenRouterModelPreferencesRequest,
    OpenRouterModelsResponse,
)
from app.services.openrouter import (
    cache_models,
    cached_models,
    decrypt_api_key,
    delete_credential_and_preferences,
    enabled_model_ids,
    fetch_openrouter_models,
    get_credential,
    set_model_preferences,
    upsert_credential,
)

router = APIRouter(prefix="/api/providers/openrouter", tags=["providers"])
CurrentUser = Annotated[User, Depends(current_user)]


def _config_response(db: DbSession, user: User) -> OpenRouterConfigResponse:
    credential = get_credential(db, user.id)
    return OpenRouterConfigResponse(
        configured=credential is not None,
        key_hint=credential.key_hint if credential else None,
        selected_model_id=credential.selected_model_id if credential else None,
        enabled_model_ids=enabled_model_ids(db, user.id),
        last_synced_at=credential.last_synced_at if credential else None,
    )


@router.get("/config", response_model=OpenRouterConfigResponse)
def get_config(db: DbSession, user: CurrentUser) -> OpenRouterConfigResponse:
    return _config_response(db, user)


@router.put("/key", response_model=OpenRouterConfigResponse)
def put_key(
    request: OpenRouterKeyRequest,
    db: DbSession,
    user: CurrentUser,
) -> OpenRouterConfigResponse:
    credential = upsert_credential(db, user, request.api_key)
    try:
        models = fetch_openrouter_models(request.api_key)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key could not be verified.",
        ) from exc

    cache_models(db, models)
    credential.last_synced_at = datetime.now(UTC)
    db.add(credential)
    db.commit()
    return _config_response(db, user)


@router.delete("/key", status_code=status.HTTP_204_NO_CONTENT)
def delete_key(db: DbSession, user: CurrentUser) -> None:
    delete_credential_and_preferences(db, user.id)
    db.commit()


@router.get("/models", response_model=OpenRouterModelsResponse)
def get_models(
    db: DbSession,
    user: CurrentUser,
    refresh: bool = False,
) -> OpenRouterModelsResponse:
    warning = None
    credential = get_credential(db, user.id)
    if refresh:
        if credential is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenRouter API key is required before syncing models.",
            )
        try:
            models = fetch_openrouter_models(decrypt_api_key(credential))
        except Exception as exc:
            models = cached_models(db)
            if not models:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="OpenRouter model sync failed and no cached models are available.",
                ) from exc
            warning = "Using cached models because OpenRouter refresh failed."
        else:
            cache_models(db, models)
            credential.last_synced_at = datetime.now(UTC)
            db.add(credential)
            db.commit()

    return OpenRouterModelsResponse(models=cached_models(db), warning=warning)


@router.patch("/models", response_model=OpenRouterConfigResponse)
def patch_models(
    request: OpenRouterModelPreferencesRequest,
    db: DbSession,
    user: CurrentUser,
) -> OpenRouterConfigResponse:
    credential = get_credential(db, user.id)
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenRouter API key is required before selecting models.",
        )
    if request.selected_model_id and request.selected_model_id not in request.enabled_model_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected model must be enabled.",
        )
    set_model_preferences(db, user.id, request.enabled_model_ids, request.selected_model_id)
    db.commit()
    return _config_response(db, user)

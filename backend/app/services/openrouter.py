import json
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.entities import (
    EnabledOpenRouterModel,
    OpenRouterCredential,
    OpenRouterModel,
    User,
)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def to_litellm_model_id(model_id: str) -> str:
    return model_id if model_id.startswith("openrouter/") else f"openrouter/{model_id}"


def normalize_model(raw: dict[str, Any]) -> dict[str, Any]:
    architecture = raw.get("architecture") or {}
    input_modalities = architecture.get("input_modalities") or raw.get("input_modalities") or []
    output_modalities = architecture.get("output_modalities") or raw.get("output_modalities") or []
    return {
        "id": raw["id"],
        "name": raw.get("name") or raw["id"],
        "input_modalities": input_modalities,
        "output_modalities": output_modalities,
        "context_length": raw.get("context_length"),
        "pricing": raw.get("pricing") or {},
    }


def fetch_openrouter_models(api_key: str) -> list[dict[str, Any]]:
    settings = get_settings()
    client_kwargs: dict[str, Any] = {"timeout": 30.0, "trust_env": True}
    if settings.openrouter_http_proxy:
        client_kwargs["proxy"] = settings.openrouter_http_proxy

    with httpx.Client(**client_kwargs) as client:
        response = client.get(
            OPENROUTER_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
    data = response.json().get("data", [])
    return [normalize_model(item) for item in data if item.get("id")]


def get_credential(db: Session, user_id: int) -> OpenRouterCredential | None:
    return db.scalar(select(OpenRouterCredential).where(OpenRouterCredential.user_id == user_id))


def decrypt_api_key(credential: OpenRouterCredential) -> str:
    return decrypt_secret(credential.encrypted_api_key)


def enabled_model_ids(db: Session, user_id: int) -> list[str]:
    return list(
        db.scalars(
            select(EnabledOpenRouterModel.model_id)
            .where(EnabledOpenRouterModel.user_id == user_id)
            .order_by(EnabledOpenRouterModel.model_id.asc())
        )
    )


def upsert_credential(db: Session, user: User, api_key: str) -> OpenRouterCredential:
    now = datetime.now(UTC)
    credential = get_credential(db, user.id)
    if credential is None:
        credential = OpenRouterCredential(user_id=user.id, encrypted_api_key="", key_hint="")
    credential.encrypted_api_key = encrypt_secret(api_key)
    credential.key_hint = api_key[-4:]
    credential.updated_at = now
    db.add(credential)
    db.flush()
    return credential


def delete_credential_and_preferences(db: Session, user_id: int) -> None:
    db.execute(delete(EnabledOpenRouterModel).where(EnabledOpenRouterModel.user_id == user_id))
    db.execute(delete(OpenRouterCredential).where(OpenRouterCredential.user_id == user_id))


def cache_models(db: Session, models: list[dict[str, Any]]) -> None:
    now = datetime.now(UTC)
    for item in models:
        record = db.get(OpenRouterModel, item["id"])
        if record is None:
            record = OpenRouterModel(id=item["id"], name=item["name"])
        record.name = item["name"]
        record.input_modalities_json = json.dumps(item["input_modalities"])
        record.output_modalities_json = json.dumps(item["output_modalities"])
        record.context_length = item["context_length"]
        record.pricing_json = json.dumps(item["pricing"])
        record.updated_at = now
        db.add(record)


def cached_models(db: Session) -> list[dict[str, Any]]:
    records = db.scalars(select(OpenRouterModel).order_by(OpenRouterModel.name.asc())).all()
    return [
        {
            "id": record.id,
            "name": record.name,
            "input_modalities": json.loads(record.input_modalities_json),
            "output_modalities": json.loads(record.output_modalities_json),
            "context_length": record.context_length,
            "pricing": json.loads(record.pricing_json),
        }
        for record in records
    ]


def set_model_preferences(
    db: Session,
    user_id: int,
    enabled_ids: list[str],
    selected_model_id: str | None,
) -> None:
    db.execute(delete(EnabledOpenRouterModel).where(EnabledOpenRouterModel.user_id == user_id))
    for model_id in dict.fromkeys(enabled_ids):
        db.add(EnabledOpenRouterModel(user_id=user_id, model_id=model_id))
    credential = get_credential(db, user_id)
    if credential is not None:
        credential.selected_model_id = selected_model_id
        credential.updated_at = datetime.now(UTC)
        db.add(credential)

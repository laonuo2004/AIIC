from datetime import datetime

from pydantic import BaseModel, Field


class OpenRouterConfigResponse(BaseModel):
    configured: bool
    key_hint: str | None
    selected_model_id: str | None
    enabled_model_ids: list[str]
    last_synced_at: datetime | None


class OpenRouterKeyRequest(BaseModel):
    api_key: str = Field(min_length=8, max_length=400)


class OpenRouterModelResponse(BaseModel):
    id: str
    name: str
    input_modalities: list[str]
    output_modalities: list[str]
    context_length: int | None
    pricing: dict[str, object]


class OpenRouterModelsResponse(BaseModel):
    models: list[OpenRouterModelResponse]
    warning: str | None = None


class OpenRouterModelPreferencesRequest(BaseModel):
    enabled_model_ids: list[str] = Field(max_length=100)
    selected_model_id: str | None = None

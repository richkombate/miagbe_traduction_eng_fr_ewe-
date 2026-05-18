from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source_lang: str = Field(..., examples=["fra", "eng", "ewe"])
    target_lang: str = Field(..., examples=["eng", "fra", "ewe"])


class TranslateResponse(BaseModel):
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    backend: str
    warning: str | None = None


class HealthResponse(BaseModel):
    status: str
    backend: str
    model_name: str
    stt_enabled: bool
    tts_enabled: bool

from functools import lru_cache
from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware

from traducteur.config import (
    get_settings,
    GROUP_NAME,
    GROUP_MEMBERS,
    PROJECT_TITLE,
    COURSE,
)
from traducteur.nlp.translator import build_translator
from traducteur.nlp.languages import LANGUAGES
from traducteur.nlp.normalization import is_reasonable_text
from traducteur.storage import history_store
from .auth import resolve_user, AuthUser
from .schemas import (
    TranslateRequest,
    TranslateResponse,
    HealthResponse,
    AboutResponse,
    TranscribeResponse,
    HistoryPayload,
    HistoryResponse,
)

settings = get_settings()
app = FastAPI(
    title=f"{PROJECT_TITLE} - Groupe {GROUP_NAME}",
    description=(
        "API de traduction automatique (NLLB-200 + LoRA éwé) et pipeline vocal. "
        f"Projet de groupe {GROUP_NAME} - {COURSE}."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def get_translator():
    return build_translator(
        settings.translation_backend,
        settings.model_name,
        settings.device,
        settings.adapter_path,
    )


@app.get("/")
def root() -> dict[str, object]:
    return {
        "message": "API Traducteur multilingue Francais-Anglais-Ewe",
        "group": GROUP_NAME,
        "members": GROUP_MEMBERS,
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "/translate",
            "/transcribe",
            "/synthesize",
            "/history",
            "/about",
            "/languages",
        ],
    }


@app.get("/about", response_model=AboutResponse)
def about() -> AboutResponse:
    return AboutResponse(
        project=PROJECT_TITLE,
        course=COURSE,
        group=GROUP_NAME,
        members=GROUP_MEMBERS,
        languages=[f"{code} ({lang.label})" for code, lang in LANGUAGES.items()],
    )


@app.get("/languages")
def languages() -> dict[str, object]:
    return {
        "languages": [
            {"code": code, "label": lang.label, "nllb_code": lang.nllb_code}
            for code, lang in LANGUAGES.items()
        ]
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        backend=settings.translation_backend,
        model_name=settings.model_name,
        stt_enabled=settings.enable_stt,
        tts_enabled=settings.enable_tts,
    )


@app.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest) -> TranslateResponse:
    if not is_reasonable_text(payload.text, settings.max_input_chars):
        raise HTTPException(status_code=400, detail="Texte vide ou trop long.")
    try:
        result = get_translator().translate(payload.text, payload.source_lang, payload.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur traduction: {exc}") from exc
    return TranslateResponse(**result.__dict__)


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...), lang: str = "fra") -> TranscribeResponse:
    if not settings.enable_stt:
        return TranscribeResponse(
            text="",
            lang=lang,
            warning="STT serveur désactivé. Activez ENABLE_STT=true (Whisper) ou utilisez le micro du navigateur.",
        )
    from traducteur.audio.stt import transcribe

    data = await file.read()
    try:
        text = transcribe(data, lang=lang)
    except Exception as exc:
        return TranscribeResponse(text="", lang=lang, warning=f"Erreur STT: {exc}")
    return TranscribeResponse(text=text, lang=lang)


@app.post("/synthesize")
def synthesize(text: str, lang: str = "fra"):
    if not settings.enable_tts:
        return {"audio_url": None, "warning": "TTS désactivé dans cette version de démonstration."}
    from traducteur.audio.tts import synthesize_to_file

    path = synthesize_to_file(text, lang=lang)
    return {"audio_url": str(path)}


# --- Historique serveur (synchronisation entre navigateurs) -------------------


@app.get("/history", response_model=HistoryResponse)
def get_history(user: AuthUser = Depends(resolve_user)) -> HistoryResponse:
    entries = history_store.load_history(settings.history_db_path, user.id)
    return HistoryResponse(entries=entries, count=len(entries))


@app.put("/history", response_model=HistoryResponse)
def put_history(
    payload: HistoryPayload, user: AuthUser = Depends(resolve_user)
) -> HistoryResponse:
    entries = history_store.replace_history(
        settings.history_db_path,
        user.id,
        [entry.model_dump() for entry in payload.entries],
    )
    return HistoryResponse(entries=entries, count=len(entries))

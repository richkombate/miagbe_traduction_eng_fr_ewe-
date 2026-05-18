from functools import lru_cache
from fastapi import FastAPI, HTTPException, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from traducteur.config import get_settings
from traducteur.nlp.translator import build_translator
from traducteur.nlp.normalization import is_reasonable_text
from .schemas import TranslateRequest, TranslateResponse, HealthResponse

settings = get_settings()
app = FastAPI(
    title="Traducteur multilingue Français-Anglais-Ewe",
    description="API de traduction et pipeline vocal pour projet universitaire IA/NLP.",
    version="0.1.0",
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
    return build_translator(settings.translation_backend, settings.model_name, settings.device)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "message": "API Traducteur multilingue Francais-Anglais-Ewe",
        "docs": "/docs",
        "health": "/health",
        "endpoints": ["/translate", "/transcribe", "/synthesize"],
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


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...), lang: str = "fra"):
    if not settings.enable_stt:
        return {
            "text": "",
            "lang": lang,
            "warning": "STT désactivé. Activez ENABLE_STT=true et configurez le module audio.",
        }
    from traducteur.audio.stt import transcribe

    data = await file.read()
    text = transcribe(data, lang=lang)
    return {"text": text, "lang": lang}


@app.post("/synthesize")
def synthesize(text: str, lang: str = "fra"):
    if not settings.enable_tts:
        return {"audio_url": None, "warning": "TTS désactivé dans cette version de démonstration."}
    from traducteur.audio.tts import synthesize_to_file

    path = synthesize_to_file(text, lang=lang)
    return {"audio_url": str(path)}

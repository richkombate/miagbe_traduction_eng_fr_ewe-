"""Identification de l'utilisateur pour la persistance de l'historique.

Deux modes, dans l'ordre de préférence :

1. **Vérifié (production)** : si un client OAuth Google est configuré
   (``GOOGLE_CLIENT_ID``) et que la requête porte un en-tête
   ``Authorization: Bearer <id_token>``, le jeton est vérifié auprès de Google
   (endpoint *tokeninfo*). On obtient un ``sub`` de confiance.

2. **Démo (sans configuration Google)** : on accepte les en-têtes
   ``X-User-Id`` / ``X-User-Email`` fournis par le frontend (identité non
   vérifiée). Pratique pour tester la synchronisation sans configurer Google.

Dans les deux cas, l'identité sert uniquement de clé de rangement de
l'historique ; aucun mot de passe n'est stocké.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from traducteur.config import get_settings

_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
# Petit cache en mémoire {id_token: (sub, email)} pour éviter un appel réseau à
# chaque requête tant que le jeton est valide.
_TOKEN_CACHE: dict[str, "AuthUser"] = {}


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None
    verified: bool


def _verify_google_token(id_token: str, client_id: str) -> AuthUser | None:
    """Vérifie un jeton Google. Renvoie l'utilisateur, ou None si invalide.

    Ne lève pas : un jeton expiré ne doit pas casser la synchronisation, on
    laisse alors l'appelant retomber sur l'identité de l'en-tête X-User-Id.
    """
    if id_token in _TOKEN_CACHE:
        return _TOKEN_CACHE[id_token]

    try:
        import httpx

        response = httpx.get(_TOKENINFO_URL, params={"id_token": id_token}, timeout=5.0)
        if response.status_code != 200:
            return None
        data = response.json()
        if data.get("aud") != client_id or not data.get("sub"):
            return None
    except Exception:
        return None

    user = AuthUser(id=data["sub"], email=data.get("email"), verified=True)
    _TOKEN_CACHE[id_token] = user
    return user


def resolve_user(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> AuthUser:
    """Dépendance FastAPI : renvoie l'utilisateur courant ou lève 401."""
    settings = get_settings()

    if authorization and authorization.lower().startswith("bearer ") and settings.google_client_id:
        verified = _verify_google_token(authorization[7:].strip(), settings.google_client_id)
        if verified is not None:
            return verified

    # Repli (mode démo ou jeton expiré) : identité non vérifiée fournie par le
    # frontend. Suffit comme clé de rangement de l'historique.
    if x_user_id:
        return AuthUser(id=x_user_id, email=x_user_email, verified=False)

    raise HTTPException(
        status_code=401,
        detail="Authentification requise pour l'historique (connectez-vous).",
    )

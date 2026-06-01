"""Persistance serveur de l'historique de traduction (SQLite).

L'historique et les favoris sont stockés côté serveur, rattachés à l'identifiant
du compte de l'utilisateur (``user_id``, le ``sub`` Google). Ainsi, l'historique
suit l'utilisateur d'un navigateur ou d'une machine à l'autre, contrairement au
stockage local du navigateur.

On utilise le module standard ``sqlite3`` : aucune dépendance ni serveur de base
de données externe n'est nécessaire. Une connexion est ouverte par opération, ce
qui est sûr avec le serveur multi-thread d'Uvicorn.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

_INIT_LOCK = threading.Lock()
_INITIALISED: set[str] = set()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    user_id         TEXT NOT NULL,
    entry_id        TEXT NOT NULL,
    source_text     TEXT,
    translated_text TEXT,
    source          TEXT,
    target          TEXT,
    favorite        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT,
    position        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, entry_id)
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, position);
"""


def _connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if db_path not in _INITIALISED:
        with _INIT_LOCK:
            if db_path not in _INITIALISED:
                conn.executescript(_SCHEMA)
                conn.commit()
                _INITIALISED.add(db_path)
    return conn


def _row_to_entry(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["entry_id"],
        "sourceText": row["source_text"],
        "translatedText": row["translated_text"],
        "source": row["source"],
        "target": row["target"],
        "favorite": bool(row["favorite"]),
        "createdAt": row["created_at"],
    }


def load_history(db_path: str, user_id: str) -> list[dict[str, Any]]:
    """Renvoie l'historique d'un utilisateur, du plus récent au plus ancien."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY position ASC",
            (user_id,),
        ).fetchall()
        return [_row_to_entry(row) for row in rows]
    finally:
        conn.close()


def replace_history(
    db_path: str, user_id: str, entries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Remplace l'intégralité de l'historique d'un utilisateur.

    Le frontend gère la liste complète (≤ 60 entrées) ; on la réécrit donc en
    bloc, ce qui garde la logique d'ordre et de déduplication côté client.
    """
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
        conn.executemany(
            """
            INSERT INTO history
                (user_id, entry_id, source_text, translated_text,
                 source, target, favorite, created_at, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    user_id,
                    str(entry.get("id")),
                    entry.get("sourceText", ""),
                    entry.get("translatedText", ""),
                    entry.get("source", ""),
                    entry.get("target", ""),
                    1 if entry.get("favorite") else 0,
                    entry.get("createdAt"),
                    position,
                )
                for position, entry in enumerate(entries)
            ],
        )
        conn.commit()
        return load_history(db_path, user_id)
    finally:
        conn.close()

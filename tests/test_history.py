import importlib

from fastapi.testclient import TestClient


def make_client(tmp_path, monkeypatch):
    # Base de données isolée par test, et identité de démo (sans Google).
    monkeypatch.setenv("HISTORY_DB_PATH", str(tmp_path / "history.db"))
    monkeypatch.setenv("TRANSLATION_BACKEND", "fallback")

    from traducteur import config

    config.get_settings.cache_clear()
    main = importlib.import_module("traducteur.api.main")
    importlib.reload(main)
    return main.app


USER = {"X-User-Id": "user-123", "X-User-Email": "a@b.com"}


def test_history_requires_identity(tmp_path, monkeypatch):
    client = TestClient(make_client(tmp_path, monkeypatch))
    assert client.get("/history").status_code == 401


def test_history_roundtrip_and_cross_client(tmp_path, monkeypatch):
    app = make_client(tmp_path, monkeypatch)

    entries = [
        {
            "id": "e1",
            "sourceText": "bonjour",
            "translatedText": "hello",
            "source": "fra",
            "target": "eng",
            "favorite": True,
            "createdAt": "2026-06-01T10:00:00Z",
        }
    ]

    writer = TestClient(app)
    saved = writer.put("/history", json={"entries": entries}, headers=USER).json()
    assert saved["count"] == 1

    # Un autre client (autre navigateur), même utilisateur -> mêmes données.
    reader = TestClient(app)
    got = reader.get("/history", headers=USER).json()
    assert got["count"] == 1
    assert got["entries"][0]["favorite"] is True

    # Un autre utilisateur est isolé.
    other = reader.get("/history", headers={"X-User-Id": "user-999"}).json()
    assert other["count"] == 0

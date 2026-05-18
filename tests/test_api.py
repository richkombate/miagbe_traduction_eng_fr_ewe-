from fastapi.testclient import TestClient
from traducteur.api.main import app


def test_translate_endpoint():
    client = TestClient(app)
    response = client.post("/translate", json={"text": "Bonjour", "source_lang": "fra", "target_lang": "eng"})
    assert response.status_code == 200
    data = response.json()
    assert data["translated_text"]
    assert data["backend"] in {"fallback", "nllb"}


def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["docs"] == "/docs"
    assert "/translate" in data["endpoints"]


def test_favicon_endpoint():
    client = TestClient(app)
    response = client.get("/favicon.ico")
    assert response.status_code == 204

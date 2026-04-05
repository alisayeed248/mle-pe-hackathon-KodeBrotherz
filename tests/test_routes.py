import pytest
from unittest.mock import patch
from app import create_app
from app.database import db
from app.models.url import URL

@pytest.fixture(autouse=True)
def mock_redis():
    with patch('app.routes.urls.redis_client') as mock:
        mock.get.return_value = None  # cache miss by default
        mock.setex.return_value = True
        yield mock

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_tables([URL], safe=True)
        yield app
        URL.delete().execute()

@pytest.fixture
def client(app):
    return app.test_client()
# ── /health ──────────────────────────────────────────────────────────────────

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"

# ── POST /shorten ─────────────────────────────────────────────────────────────

def test_shorten_valid_url(client):
    res = client.post("/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
    data = res.get_json()
    assert "short_code" in data
    assert "short_url" in data

def test_shorten_missing_url(client):
    res = client.post("/shorten", json={})
    assert res.status_code == 400
    assert "error" in res.get_json()

def test_shorten_invalid_url(client):
    res = client.post("/shorten", json={"url": "not-a-url"})
    assert res.status_code == 400

def test_shorten_custom_code(client):
    res = client.post("/shorten", json={"url": "https://example.com", "custom_code": "mycode"})
    assert res.status_code == 201
    assert res.get_json()["short_code"] == "mycode"

def test_shorten_duplicate_custom_code(client):
    client.post("/shorten", json={"url": "https://example.com", "custom_code": "dupe"})
    res = client.post("/shorten", json={"url": "https://other.com", "custom_code": "dupe"})
    assert res.status_code == 409

def test_shorten_custom_code_too_short(client):
    res = client.post("/shorten", json={"url": "https://example.com", "custom_code": "ab"})
    assert res.status_code == 400

# ── GET /<code> ───────────────────────────────────────────────────────────────

def test_redirect_valid_code(client):
    res = client.post("/shorten", json={"url": "https://example.com"})
    code = res.get_json()["short_code"]
    res = client.get(f"/{code}")
    assert res.status_code == 302

def test_redirect_invalid_code(client):
    res = client.get("/doesnotexist")
    assert res.status_code == 404

# ── GET /<code>/stats ─────────────────────────────────────────────────────────

def test_stats_valid_code(client):
    res = client.post("/shorten", json={"url": "https://example.com"})
    code = res.get_json()["short_code"]
    res = client.get(f"/{code}/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["short_code"] == code
    assert "click_count" in data

def test_stats_invalid_code(client):
    res = client.get("/fakecode/stats")
    assert res.status_code == 404

# ── Error handlers ────────────────────────────────────────────────────────────

def test_404_returns_json(client):
    res = client.get("/nonexistent-route-xyz")
    assert res.content_type == "application/json"

def test_method_not_allowed(client):
    res = client.delete("/shorten")
    assert res.status_code == 405
    assert "error" in res.get_json()
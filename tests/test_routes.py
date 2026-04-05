import pytest
from app import create_app
from app.database import db
from app.models.url import URL
from app.models.user import User
from app.models.event import Event

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        db.create_tables([URL, User, Event], safe=True)
        yield app
        Event.delete().execute()
        URL.delete().execute()
        User.delete().execute()

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


# ── /users endpoints ─────────────────────────────────────────────────────────

def test_list_users_empty(client):
    res = client.get("/users")
    assert res.status_code == 200
    assert res.get_json() == []


def test_create_user(client):
    res = client.post("/users", json={"username": "testuser", "email": "test@example.com"})
    assert res.status_code == 201
    data = res.get_json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_create_user_missing_username(client):
    res = client.post("/users", json={"email": "test@example.com"})
    assert res.status_code == 400


def test_create_user_missing_email(client):
    res = client.post("/users", json={"username": "testuser"})
    assert res.status_code == 400


def test_create_user_duplicate(client):
    client.post("/users", json={"username": "dupe", "email": "dupe@example.com"})
    res = client.post("/users", json={"username": "dupe", "email": "other@example.com"})
    assert res.status_code == 400


def test_get_user(client):
    res = client.post("/users", json={"username": "getme", "email": "getme@example.com"})
    user_id = res.get_json()["id"]
    res = client.get(f"/users/{user_id}")
    assert res.status_code == 200
    assert res.get_json()["username"] == "getme"


def test_get_user_not_found(client):
    res = client.get("/users/99999")
    assert res.status_code == 404


def test_update_user(client):
    res = client.post("/users", json={"username": "original", "email": "original@example.com"})
    user_id = res.get_json()["id"]
    res = client.put(f"/users/{user_id}", json={"username": "updated"})
    assert res.status_code == 200
    assert res.get_json()["username"] == "updated"


def test_update_user_not_found(client):
    res = client.put("/users/99999", json={"username": "updated"})
    assert res.status_code == 404


def test_delete_user(client):
    res = client.post("/users", json={"username": "deleteme", "email": "deleteme@example.com"})
    user_id = res.get_json()["id"]
    res = client.delete(f"/users/{user_id}")
    assert res.status_code == 200
    res = client.get(f"/users/{user_id}")
    assert res.status_code == 404


def test_delete_user_not_found(client):
    res = client.delete("/users/99999")
    assert res.status_code == 404


# ── /urls CRUD endpoints ─────────────────────────────────────────────────────

def test_list_urls_empty(client):
    res = client.get("/urls")
    assert res.status_code == 200
    assert res.get_json() == []


def test_create_url_crud(client):
    res = client.post("/urls", json={"original_url": "https://example.com"})
    assert res.status_code == 201
    data = res.get_json()
    assert data["original_url"] == "https://example.com"
    assert "short_code" in data


def test_create_url_with_custom_code(client):
    res = client.post("/urls", json={"original_url": "https://example.com", "short_code": "custom1"})
    assert res.status_code == 201
    assert res.get_json()["short_code"] == "custom1"


def test_create_url_duplicate_code(client):
    client.post("/urls", json={"original_url": "https://example.com", "short_code": "dupeurl"})
    res = client.post("/urls", json={"original_url": "https://other.com", "short_code": "dupeurl"})
    assert res.status_code == 400


def test_create_url_missing_original(client):
    res = client.post("/urls", json={})
    assert res.status_code == 400


def test_get_url_crud(client):
    res = client.post("/urls", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    res = client.get(f"/urls/{url_id}")
    assert res.status_code == 200


def test_get_url_not_found(client):
    res = client.get("/urls/99999")
    assert res.status_code == 404


def test_update_url_crud(client):
    res = client.post("/urls", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    res = client.put(f"/urls/{url_id}", json={"title": "My URL", "is_active": False})
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "My URL"
    assert data["is_active"] == False


def test_update_url_not_found(client):
    res = client.put("/urls/99999", json={"title": "Test"})
    assert res.status_code == 404


def test_delete_url_crud(client):
    res = client.post("/urls", json={"original_url": "https://example.com"})
    url_id = res.get_json()["id"]
    res = client.delete(f"/urls/{url_id}")
    assert res.status_code == 200
    res = client.get(f"/urls/{url_id}")
    assert res.status_code == 404


def test_delete_url_not_found(client):
    res = client.delete("/urls/99999")
    assert res.status_code == 404


def test_list_urls_with_filters(client):
    client.post("/urls", json={"original_url": "https://example.com", "user_id": 1})
    res = client.get("/urls?user_id=1")
    assert res.status_code == 200
    res = client.get("/urls?is_active=true")
    assert res.status_code == 200


# ── /events endpoints ────────────────────────────────────────────────────────

def test_list_events_empty(client):
    res = client.get("/events")
    assert res.status_code == 200
    assert res.get_json() == []


def test_create_event(client):
    res = client.post("/events", json={"event_type": "click", "url_id": 1})
    assert res.status_code == 201
    data = res.get_json()
    assert data["event_type"] == "click"


def test_create_event_missing_type(client):
    res = client.post("/events", json={"url_id": 1})
    assert res.status_code == 400


def test_create_event_with_details(client):
    res = client.post("/events", json={"event_type": "click", "details": {"ip": "127.0.0.1"}})
    assert res.status_code == 201
    data = res.get_json()
    assert data["details"]["ip"] == "127.0.0.1"


def test_get_event(client):
    res = client.post("/events", json={"event_type": "view"})
    event_id = res.get_json()["id"]
    res = client.get(f"/events/{event_id}")
    assert res.status_code == 200


def test_get_event_not_found(client):
    res = client.get("/events/99999")
    assert res.status_code == 404


def test_list_events_with_filters(client):
    client.post("/events", json={"event_type": "click", "url_id": 5})
    res = client.get("/events?url_id=5")
    assert res.status_code == 200
    res = client.get("/events?event_type=click")
    assert res.status_code == 200
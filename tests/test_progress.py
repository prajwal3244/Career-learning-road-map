"""Tests for server-side per-user progress sync."""
import app as app_module
import pytest


@pytest.fixture
def client(tmp_path):
    app_module.DB_FILE = tmp_path / "test_users.db"
    app_module.init_db()
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


def _login(client):
    with client.session_transaction() as s:
        s["csrf_token"] = "tok"
    client.post("/register", data={
        "csrf_token": "tok", "name": "Grace", "email": "grace@example.com",
        "password": "navylife99", "confirm": "navylife99",
    })
    # ensure token still present after session.clear() on register
    with client.session_transaction() as s:
        s["csrf_token"] = "tok"


def test_guest_get_progress_is_unauthed(client):
    data = client.get("/api/progress?career=data-scientist").get_json()
    assert data["authed"] is False
    assert data["done"] == []


def test_guest_cannot_save(client):
    resp = client.post("/api/progress", json={"career": "data-scientist", "done": ["x"]})
    assert resp.status_code == 401


def test_save_requires_csrf_header(client):
    _login(client)
    resp = client.post("/api/progress", json={"career": "data-scientist", "done": ["programming"]})
    assert resp.status_code == 403


def test_save_and_read_back(client):
    _login(client)
    resp = client.post(
        "/api/progress",
        json={"career": "data-scientist", "done": ["programming", "math_stats"]},
        headers={"X-CSRFToken": "tok"},
    )
    assert resp.status_code == 200
    data = client.get("/api/progress?career=data-scientist").get_json()
    assert data["authed"] is True
    assert set(data["done"]) == {"programming", "math_stats"}


def test_save_is_per_career(client):
    _login(client)
    client.post("/api/progress", json={"career": "data-scientist", "done": ["ml"]}, headers={"X-CSRFToken": "tok"})
    other = client.get("/api/progress?career=data-analyst").get_json()
    assert other["done"] == []


def test_save_overwrites(client):
    _login(client)
    client.post("/api/progress", json={"career": "data-scientist", "done": ["a", "b"]}, headers={"X-CSRFToken": "tok"})
    client.post("/api/progress", json={"career": "data-scientist", "done": ["c"]}, headers={"X-CSRFToken": "tok"})
    data = client.get("/api/progress?career=data-scientist").get_json()
    assert data["done"] == ["c"]


def test_save_rejects_bad_body(client):
    _login(client)
    resp = client.post("/api/progress", json={"career": "data-scientist", "done": "not-a-list"}, headers={"X-CSRFToken": "tok"})
    assert resp.status_code == 400

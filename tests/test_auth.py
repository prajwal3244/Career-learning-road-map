"""Tests for the register / login / logout flow.

Uses a throwaway SQLite database so the real users.db is never touched.
"""
import app as app_module
import pytest


@pytest.fixture
def client(tmp_path):
    # Point the app at a temporary user DB and (re)initialize it.
    app_module.DB_FILE = tmp_path / "test_users.db"
    app_module.init_db()
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


def _csrf(client):
    """Seed a CSRF token into the session and return it."""
    with client.session_transaction() as s:
        s["csrf_token"] = "test-token"
    return "test-token"


def register(client, **over):
    data = {
        "csrf_token": _csrf(client),
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "password": "hunter2pass",
        "confirm": "hunter2pass",
    }
    data.update(over)
    return client.post("/register", data=data)


# --------------------------------------------------------------------------- #
def test_register_success_logs_in(client):
    resp = register(client)
    assert resp.status_code == 302  # redirect home
    with client.session_transaction() as s:
        assert s.get("user_id")


def test_register_requires_valid_email(client):
    resp = register(client, email="not-an-email")
    assert resp.status_code == 400


def test_register_rejects_short_password(client):
    resp = register(client, password="short", confirm="short")
    assert resp.status_code == 400


def test_register_rejects_mismatched_passwords(client):
    resp = register(client, confirm="different1")
    assert resp.status_code == 400


def test_register_rejects_missing_csrf(client):
    resp = client.post("/register", data={"name": "A", "email": "a@b.com", "password": "longenough", "confirm": "longenough"})
    assert resp.status_code == 400


def test_duplicate_email_rejected(client):
    register(client)
    with client.session_transaction() as s:
        s.pop("user_id", None)  # simulate logged out
    resp = register(client)
    assert resp.status_code == 400


def test_login_success(client):
    register(client)
    with client.session_transaction() as s:
        s.pop("user_id", None)
    resp = client.post("/login", data={"csrf_token": _csrf(client), "email": "ada@example.com", "password": "hunter2pass"})
    assert resp.status_code == 302
    with client.session_transaction() as s:
        assert s.get("user_id")


def test_login_wrong_password(client):
    register(client)
    with client.session_transaction() as s:
        s.pop("user_id", None)
    resp = client.post("/login", data={"csrf_token": _csrf(client), "email": "ada@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_page_renders(client):
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200


def test_password_is_hashed_not_plaintext(client):
    register(client)
    with app_module.get_db() as db:
        row = db.execute("SELECT password_hash FROM users WHERE email = ?", ("ada@example.com",)).fetchone()
    assert row is not None
    assert "hunter2pass" not in row["password_hash"]


def test_logout_clears_session(client):
    register(client)
    resp = client.post("/logout", data={"csrf_token": _csrf(client)})
    assert resp.status_code == 302
    with client.session_transaction() as s:
        assert not s.get("user_id")


def test_open_redirect_is_blocked(client):
    resp = client.post(
        "/register?next=https://evil.example.com",
        data={"csrf_token": _csrf(client), "name": "A", "email": "a@b.com", "password": "longenough", "confirm": "longenough"},
    )
    assert resp.status_code == 302
    assert "evil.example.com" not in resp.headers["Location"]

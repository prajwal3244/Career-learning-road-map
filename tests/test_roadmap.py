"""Unit tests for the roadmap engine and API.

Run: pytest
"""
import json

import pytest

import app as app_module
from app import _clamp_score, generate_roadmap


@pytest.fixture
def client():
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as c:
        yield c


# --------------------------------------------------------------------------- #
# _clamp_score
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [(50, 50), ("75", 75), (-10, 0), (150, 100), (0, 0), (100, 100),
     (None, 0), ("abc", 0), (33.9, 33)],
)
def test_clamp_score(raw, expected):
    assert _clamp_score(raw) == expected


# --------------------------------------------------------------------------- #
# generate_roadmap
# --------------------------------------------------------------------------- #
def test_unknown_career_returns_error():
    result = generate_roadmap({}, "nope")
    assert "error" in result


def test_beginner_gets_full_track():
    # A total beginner data scientist should get every core skill + capstone + closing.
    scores = {k: 0 for k in ("programming", "math_stats", "sql_databases",
                             "data_wrangling", "data_viz", "machine_learning")}
    result = generate_roadmap(scores, "data-scientist")
    keys = [s["key"] for s in result["stages"]]
    assert keys[-2:] == ["capstone", "closing"]
    assert "machine_learning" in keys
    assert result["summary"]["skills_mastered"] == []
    assert result["summary"]["total_hours"] > 0


def test_mastered_skills_are_skipped_and_reported():
    scores = {"programming": 95, "math_stats": 95, "sql_databases": 95,
              "data_wrangling": 95, "data_viz": 95}
    result = generate_roadmap(scores, "data-analyst")
    keys = [s["key"] for s in result["stages"]]
    # All five core skills mastered -> only capstone + closing remain.
    assert keys == ["capstone", "closing"]
    assert len(result["summary"]["skills_mastered"]) == 5


def test_stage_keys_are_stable_ids_not_positions():
    result = generate_roadmap({}, "data-analyst")
    for stage in result["stages"]:
        assert isinstance(stage["key"], str)
        assert stage["key"]  # non-empty, used for progress persistence


def test_foundations_vs_levelup_label():
    # programming threshold is 60 -> boundary at 30.
    low = generate_roadmap({"programming": 10}, "data-analyst")
    high = generate_roadmap({"programming": 45}, "data-analyst")
    prog_low = next(s for s in low["stages"] if s["key"] == "programming")
    prog_high = next(s for s in high["stages"] if s["key"] == "programming")
    assert prog_low["level"] == "Foundations"
    assert prog_high["level"] == "Level up"


def test_week_math():
    result = generate_roadmap({}, "data-analyst")
    hours = result["summary"]["total_hours"]
    assert result["summary"]["weeks_full_time"] == round(hours / 40, 1)
    assert result["summary"]["weeks_part_time"] == round(hours / 10, 1)


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_config_shape(client):
    data = client.get("/api/config").get_json()
    assert {"meta", "skills", "careers"} <= data.keys()
    assert len(data["careers"]) >= 1


def test_roadmap_endpoint_ok(client):
    resp = client.post("/api/roadmap", json={"career": "data-scientist", "skills": {}})
    assert resp.status_code == 200
    assert "stages" in resp.get_json()


def test_roadmap_missing_career_is_400(client):
    resp = client.post("/api/roadmap", json={"skills": {}})
    assert resp.status_code == 400


def test_roadmap_non_object_body_is_400_not_500(client):
    resp = client.post("/api/roadmap", data=json.dumps([1, 2, 3]),
                       content_type="application/json")
    assert resp.status_code == 400


def test_roadmap_bad_skills_type_is_400(client):
    resp = client.post("/api/roadmap", json={"career": "data-scientist", "skills": "oops"})
    assert resp.status_code == 400


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "Content-Security-Policy" in resp.headers

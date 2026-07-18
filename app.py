"""
Data & AI Career Learning Roadmap
=================================

A data-driven Flask app that generates a personalized learning roadmap for
Data/AI/ML careers based on a learner's self-assessed skills and target role.

The curriculum lives in ``data/roadmap.json`` (data), and this module contains
the roadmap *engine* (logic) and the web/API layer. Keeping data and logic
separate makes the roadmap easy to extend without touching Python.

Run (development):
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5001

Run (production):
    gunicorn app:app          # debug stays off unless FLASK_DEBUG=1
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "roadmap.json"

# Tunable engine constants (named rather than inlined for readability).
FULL_TIME_HOURS_PER_WEEK = 40
PART_TIME_HOURS_PER_WEEK = 10
FOUNDATIONS_RATIO = 0.5      # score below threshold * this => "Foundations"
DEFAULT_THRESHOLD = 60       # used when a module omits its own threshold

app = Flask(__name__)


def load_curriculum() -> dict[str, Any]:
    """Open ``data/roadmap.json`` and return the parsed curriculum dict.

    This is a plain loader. The decision to reload per-request in debug mode
    lives in the callers (:func:`_refresh_globals` and :func:`api_config`).
    """
    with DATA_FILE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


# Load once at import so lookups (skills, careers) are cheap and validated early.
CURRICULUM: dict[str, Any] = load_curriculum()
SKILLS_BY_ID: dict[str, Any] = {s["id"]: s for s in CURRICULUM["skills"]}
CAREERS_BY_ID: dict[str, Any] = {c["id"]: c for c in CURRICULUM["careers"]}
MODULES: dict[str, Any] = CURRICULUM["modules"]


def _clamp_score(value: object) -> int:
    """Coerce an incoming skill score to an int in the range [0, 100]."""
    try:
        score = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, score))


def generate_roadmap(skill_scores: dict[str, Any], career_id: str) -> dict[str, Any]:
    """Build a personalized, ordered roadmap.

    Args:
        skill_scores: mapping of skill_id -> self-assessed proficiency (0-100).
        career_id: the target career id (must exist in the curriculum).

    Returns:
        A structured roadmap dict the frontend renders. An unknown career
        returns an ``error`` payload instead of raising. Every stage carries a
        stable ``key`` (skill id / "capstone" / "closing") so client-side
        progress survives re-assessment, plus a positional ``step`` for display.
    """
    career = CAREERS_BY_ID.get(career_id)
    if career is None:
        return {"error": f"Unknown career: {career_id!r}"}

    normalized = {sid: _clamp_score(skill_scores.get(sid, 0)) for sid in SKILLS_BY_ID}

    stages = []
    step_no = 1
    total_hours = 0
    skills_mastered = []

    for skill_id in career["core_skills"]:
        skill = SKILLS_BY_ID.get(skill_id)
        if skill is None:
            # Unknown skill id in the data — nothing sensible to render.
            continue

        module = MODULES.get(skill_id)
        score = normalized.get(skill_id, 0)
        threshold = module.get("threshold", DEFAULT_THRESHOLD) if module else DEFAULT_THRESHOLD

        if score >= threshold:
            # Learner already meets the bar for this skill -> acknowledge, skip.
            skills_mastered.append(skill["name"])
            continue

        if module is None:
            # Known skill but no learning module authored yet: don't silently
            # drop it — surface a minimal stage so the gap is visible.
            total_hours += 0
            stages.append(
                {
                    "step": step_no,
                    "key": skill_id,
                    "type": "skill",
                    "skill_id": skill_id,
                    "icon": skill.get("icon", "•"),
                    "title": skill.get("name", skill_id),
                    "level": "Foundations",
                    "why": skill.get("description", ""),
                    "current_score": score,
                    "target_score": threshold,
                    "gap": threshold - score,
                    "hours": 0,
                    "objectives": [],
                    "resources": [],
                    "project": "",
                }
            )
            step_no += 1
            continue

        # Distance below threshold drives a rough priority/level label.
        gap = threshold - score
        level = "Foundations" if score < threshold * FOUNDATIONS_RATIO else "Level up"

        hours = module.get("hours", 0)
        total_hours += hours

        stages.append(
            {
                "step": step_no,
                "key": skill_id,
                "type": "skill",
                "skill_id": skill_id,
                "icon": skill.get("icon", "•"),
                "title": module.get("title", skill.get("name", skill_id)),
                "level": level,
                "why": module.get("why", ""),
                "current_score": score,
                "target_score": threshold,
                "gap": gap,
                "hours": hours,
                "objectives": module.get("objectives", []),
                "resources": module.get("resources", []),
                "project": module.get("project", ""),
            }
        )
        step_no += 1

    # Career-specific capstone.
    capstone = career.get("capstone")
    if capstone:
        total_hours += capstone.get("hours", 0)
        stages.append(
            {
                "step": step_no,
                "key": "capstone",
                "type": "capstone",
                "icon": career.get("icon", "🎯"),
                "title": f"Capstone: {capstone.get('title', 'Project')}",
                "why": capstone.get("summary", ""),
                "hours": capstone.get("hours", 0),
                "objectives": capstone.get("steps", []),
                "resources": capstone.get("resources", []),
                "project": "",
            }
        )
        step_no += 1

    # Universal closing stage: portfolio + interview prep.
    closing = CURRICULUM.get("closing_stage")
    if closing:
        total_hours += closing.get("hours", 0)
        stages.append(
            {
                "step": step_no,
                "key": "closing",
                "type": "closing",
                "icon": "🚀",
                "title": closing.get("title", "Portfolio & Interview Prep"),
                "why": closing.get("why", ""),
                "hours": closing.get("hours", 0),
                "objectives": closing.get("objectives", []),
                "resources": closing.get("resources", []),
                "project": closing.get("project", ""),
            }
        )

    weeks_ft = round(total_hours / FULL_TIME_HOURS_PER_WEEK, 1) if total_hours else 0
    weeks_pt = round(total_hours / PART_TIME_HOURS_PER_WEEK, 1) if total_hours else 0

    return {
        "career": {
            "id": career["id"],
            "title": career["title"],
            "icon": career.get("icon", ""),
            "tagline": career.get("tagline", ""),
            "avg_salary_us": career.get("avg_salary_us", ""),
            "avg_salary_in": career.get("avg_salary_in", ""),
            "demand": career.get("demand", ""),
        },
        "summary": {
            "total_stages": len(stages),
            "total_hours": total_hours,
            "weeks_full_time": weeks_ft,
            "weeks_part_time": weeks_pt,
            "skills_mastered": skills_mastered,
        },
        "stages": stages,
    }


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config")
def api_config():
    """Expose skills + careers so the frontend builds its UI from the data."""
    if app.debug:
        _refresh_globals()
    return jsonify(
        {
            "meta": CURRICULUM["meta"],
            "skills": CURRICULUM["skills"],
            "careers": [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "icon": c.get("icon", ""),
                    "tagline": c.get("tagline", ""),
                    "avg_salary_us": c.get("avg_salary_us", ""),
                    "avg_salary_in": c.get("avg_salary_in", ""),
                    "demand": c.get("demand", ""),
                    "core_skills": c.get("core_skills", []),
                }
                for c in CURRICULUM["careers"]
            ],
        }
    )


@app.route("/api/roadmap", methods=["POST"])
def api_roadmap():
    # Distinguish "no/invalid JSON body" from "valid JSON, missing field".
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be valid JSON with Content-Type: application/json."}), 400
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    career_id = payload.get("career")
    skills = payload.get("skills", {})

    if not career_id:
        return jsonify({"error": "Missing 'career' in request body."}), 400
    if not isinstance(skills, dict):
        return jsonify({"error": "'skills' must be an object of skill_id -> score."}), 400

    # Refresh data in debug so content edits are live.
    if app.debug:
        _refresh_globals()

    try:
        result = generate_roadmap(skills, career_id)
    except Exception as exc:  # defensive: never leak a 500 stack to the client
        app.logger.exception("Roadmap generation failed")
        return jsonify({"error": f"Could not generate roadmap: {exc}"}), 500

    status = 400 if "error" in result else 200
    return jsonify(result), status


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "careers": len(CAREERS_BY_ID), "skills": len(SKILLS_BY_ID)})


@app.after_request
def set_security_headers(response):
    """Defense-in-depth response headers (no auth/cookies, so this is a floor)."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'",
    )
    return response


def _refresh_globals() -> None:
    """Reload curriculum + lookups (used in debug so edits are picked up)."""
    global CURRICULUM, SKILLS_BY_ID, CAREERS_BY_ID, MODULES
    CURRICULUM = load_curriculum()
    SKILLS_BY_ID = {s["id"]: s for s in CURRICULUM["skills"]}
    CAREERS_BY_ID = {c["id"]: c for c in CURRICULUM["careers"]}
    MODULES = CURRICULUM["modules"]


if __name__ == "__main__":
    # Debug is OFF unless FLASK_DEBUG=1. Port defaults to 5001 to dodge the
    # macOS AirPlay Receiver, which occupies 5000. Both are env-overridable.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5001")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )

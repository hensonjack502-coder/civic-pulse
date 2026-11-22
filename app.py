"""Flask server and SQLite storage for Civic Pulse complaints."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory


PROJECT_DIR = Path(__file__).resolve().parent
ALLOWED_CATEGORIES = {"Garbage", "Roads", "Water", "Streetlights", "Other"}


def create_app(test_config: dict | None = None) -> Flask:
    """Build the web app. Tests can pass a temporary database path."""
    app = Flask(__name__, static_folder=None)
    app.config.from_mapping(
        DATABASE=str(PROJECT_DIR / "instance" / "civic_pulse.db"),
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    def connect_database() -> sqlite3.Connection:
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def database_session():
        """Commit successful work and always close the SQLite connection."""
        connection = connect_database()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize_database() -> None:
        database_path = Path(app.config["DATABASE"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with database_session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS complaints (
                    complaint_id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    created_at TEXT NOT NULL
                )
                """
            )

    initialize_database()

    def complaint_as_dict(row: sqlite3.Row) -> dict:
        return {
            "id": row["complaint_id"],
            "category": row["category"],
            "location": row["location"],
            "description": row["description"],
            "status": row["status"],
            "created_at": row["created_at"],
        }

    @app.get("/")
    def home():
        return send_from_directory(PROJECT_DIR, "index.html")

    @app.get("/styles.css")
    @app.get("/app.js")
    def frontend_file():
        # Only the existing CSS and JavaScript files are served from this route.
        return send_from_directory(PROJECT_DIR, request.path.lstrip("/"))

    @app.post("/api/complaints")
    def submit_complaint():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(success=False, message="Send complaint details as JSON."), 400

        category = data.get("category")
        location = data.get("location")
        description = data.get("description")
        if not all(isinstance(value, str) for value in (category, location, description)):
            return jsonify(success=False, message="Category, location and description are required."), 400

        category = category.strip()
        location = location.strip()
        description = description.strip()
        if category not in ALLOWED_CATEGORIES:
            return jsonify(success=False, message="Choose a valid issue category."), 400
        if not location or len(location) > 120:
            return jsonify(success=False, message="Location is required and must be 120 characters or fewer."), 400
        if not description or len(description) > 600:
            return jsonify(success=False, message="Description is required and must be 600 characters or fewer."), 400

        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with database_session() as connection:
            while True:
                complaint_id = f"CP-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex.upper()}"
                try:
                    connection.execute(
                        """INSERT INTO complaints
                           (complaint_id, category, location, description, status, created_at)
                           VALUES (?, ?, ?, ?, 'Pending', ?)""",
                        (complaint_id, category, location, description, created_at),
                    )
                    break
                except sqlite3.IntegrityError:
                    # A primary-key collision is extremely unlikely, but SQLite is the final
                    # authority for uniqueness. Retry only if this exact ID already exists.
                    existing = connection.execute(
                        "SELECT 1 FROM complaints WHERE complaint_id = ?", (complaint_id,)
                    ).fetchone()
                    if existing is None:
                        raise
            row = connection.execute(
                "SELECT * FROM complaints WHERE complaint_id = ?", (complaint_id,)
            ).fetchone()

        return jsonify(
            success=True,
            message="Complaint saved. This demo is not connected to a government department.",
            complaint=complaint_as_dict(row),
        ), 201

    @app.get("/api/complaints/summary")
    def complaint_summary():
        with database_session() as connection:
            total = connection.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
            pending = connection.execute(
                "SELECT COUNT(*) FROM complaints WHERE status = 'Pending'"
            ).fetchone()[0]
            resolved = connection.execute(
                "SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'"
            ).fetchone()[0]
        return jsonify(success=True, total=total, pending=pending, resolved=resolved)

    @app.get("/api/complaints/<complaint_id>")
    def track_complaint(complaint_id: str):
        with database_session() as connection:
            row = connection.execute(
                "SELECT * FROM complaints WHERE complaint_id = ? COLLATE NOCASE",
                (complaint_id.strip(),),
            ).fetchone()
        if row is None:
            return jsonify(success=False, message="No complaint was found with that ID."), 404
        return jsonify(success=True, complaint=complaint_as_dict(row)), 200

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify(success=False, message="API endpoint not found."), 404
        return "Page not found", 404

    @app.errorhandler(413)
    def request_too_large(_error):
        if request.path.startswith("/api/"):
            return jsonify(success=False, message="The request is too large."), 413
        return "Request too large", 413

    return app


app = create_app()


if __name__ == "__main__":
    # Local development only. Do not expose Flask's development server publicly.
    app.run(host="0.0.0.0", port=5000, debug=False)

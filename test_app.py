"""Small API checks that run with Python's built-in unittest module."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app


class ComplaintApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        database = Path(self.temp_directory.name) / "test_civic_pulse.db"
        self.app = create_app({"TESTING": True, "DATABASE": str(database)})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_submit_then_track_complaint(self):
        payload = {
            "category": "Roads",
            "location": "Demo Main Street",
            "description": "A pothole needs attention.",
        }
        submitted = self.client.post("/api/complaints", json=payload)
        self.assertEqual(submitted.status_code, 201)
        submitted_data = submitted.get_json()
        self.assertTrue(submitted_data["success"])
        complaint_id = submitted_data["complaint"]["id"]
        self.assertRegex(complaint_id, r"^CP-\d{8}-[A-F0-9]{32}$")

        tracked = self.client.get(f"/api/complaints/{complaint_id.lower()}")
        self.assertEqual(tracked.status_code, 200)
        tracked_data = tracked.get_json()
        self.assertEqual(tracked_data["complaint"]["id"], complaint_id)
        self.assertEqual(tracked_data["complaint"]["status"], "Pending")

    def test_id_collision_retries_with_a_new_uuid(self):
        first_suffix = "A" * 32
        second_suffix = "B" * 32
        existing_id = f"CP-{datetime.now().strftime('%Y%m%d')}-{first_suffix}"
        with closing(sqlite3.connect(self.app.config["DATABASE"])) as connection:
            with connection:
                connection.execute(
                    """INSERT INTO complaints
                       (complaint_id, category, location, description, status, created_at)
                       VALUES (?, 'Roads', 'Existing place', 'Existing report', 'Pending', '2026-01-01T00:00:00+00:00')""",
                    (existing_id,),
                )

        with patch(
            "app.uuid4",
            side_effect=[SimpleNamespace(hex=first_suffix.lower()), SimpleNamespace(hex=second_suffix.lower())],
        ):
            response = self.client.post(
                "/api/complaints",
                json={"category": "Water", "location": "New place", "description": "New report."},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["complaint"]["id"].split("-")[-1], second_suffix)

    def test_reject_invalid_category(self):
        response = self.client.post(
            "/api/complaints",
            json={"category": "Unlisted", "location": "Somewhere", "description": "Something happened."},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_unknown_complaint_returns_not_found(self):
        response = self.client.get("/api/complaints/CP-00000000-NOTREAL")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_summary_counts_saved_complaints(self):
        self.client.post(
            "/api/complaints",
            json={"category": "Water", "location": "Sample Lane", "description": "Leak reported."},
        )
        response = self.client.get("/api/complaints/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"success": True, "total": 1, "pending": 1, "resolved": 0})


if __name__ == "__main__":
    unittest.main()

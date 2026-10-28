"""Unit tests for SQLite database state management and milestone tracking."""

import os
import tempfile
import unittest
from datetime import date
import sys

# Ensure src is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from packaging_agent.db import (
    get_all_tracked_tasks,
    get_pending_milestone_tasks,
    get_task_by_id,
    init_db,
    sync_task_record,
    update_milestone_status,
)


class TestDatabaseLifecycle(unittest.TestCase):
    """Test suite for database persistence and milestone tracking."""

    def setUp(self):
        """Create a temporary database for isolation."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        init_db(self.db_path)

    def tearDown(self):
        """Clean up temporary test database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_sync_task_record_and_deduplication(self):
        """Verify task registration and email recipient deduplication."""
        recipients = [
            "guillaume.meunier@renault.com",
            "guillaume.meunier@renault.com",
            "GUILLAUME.MEUNIER@RENAULT.COM",
        ]
        msg = sync_task_record(
            task_id="SCTASK1001",
            ritm_id="RITM1001",
            app_name="TEST APP",
            req_type="Existing Application",
            closed_date="2026-10-25T10:00:00Z",
            recipients=recipients,
            db_path=self.db_path,
        )
        self.assertIn("SCTASK1001", msg)

        task = get_task_by_id("SCTASK1001", db_path=self.db_path)
        self.assertIsNotNone(task)
        self.assertEqual(task["task_id"], "SCTASK1001")
        # Ensure duplicates and casing are normalized to a single recipient
        self.assertEqual(task["recipients"], "guillaume.meunier@renault.com")

    def test_milestone_calculation_d1_d3_d7(self):
        """Verify dynamic milestone evaluation for D+1, D+3, and D+7."""
        today = date(2026, 10, 28)

        # Task closed yesterday -> D+1
        sync_task_record(
            "TASK_D1", "RITM_D1", "APP1", "Existing Application",
            "2026-10-27T08:00:00Z", ["user1@renault.com"], db_path=self.db_path
        )

        # Task closed 3 days ago -> D+3
        sync_task_record(
            "TASK_D3", "RITM_D3", "APP2", "Horse Application",
            "2026-10-25T08:00:00Z", ["user2@renault.com"], db_path=self.db_path
        )

        # Task closed 8 days ago -> D+7
        sync_task_record(
            "TASK_D7", "RITM_D7", "APP3", "Distribution",
            "2026-10-20T08:00:00Z", ["user3@renault.com"], db_path=self.db_path
        )

        pending = get_pending_milestone_tasks(current_date=today, db_path=self.db_path)
        self.assertEqual(len(pending), 3)

        milestones_found = {item["task_id"]: item["due_milestone"] for item in pending}
        self.assertEqual(milestones_found["TASK_D1"], "D+1")
        self.assertEqual(milestones_found["TASK_D3"], "D+3")
        self.assertEqual(milestones_found["TASK_D7"], "D+7")

    def test_milestone_completion_flow(self):
        """Verify that updating a milestone prevents re-triggering and D+7 completes task."""
        today = date(2026, 10, 28)
        sync_task_record(
            "TASK_FLOW", "RITM_FLOW", "FLOW APP", "Existing Application",
            "2026-10-27T08:00:00Z", ["user@renault.com"], db_path=self.db_path
        )

        # Should be due for D+1
        pending = get_pending_milestone_tasks(current_date=today, db_path=self.db_path)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["due_milestone"], "D+1")

        # Mark D+1 as dispatched
        updated = update_milestone_status("TASK_FLOW", "D+1", db_path=self.db_path)
        self.assertTrue(updated)

        # Re-check on same day: should have 0 pending
        pending_after = get_pending_milestone_tasks(current_date=today, db_path=self.db_path)
        self.assertEqual(len(pending_after), 0)

        # Fast forward to D+7 date
        future = date(2026, 11, 5)
        pending_future = get_pending_milestone_tasks(current_date=future, db_path=self.db_path)
        self.assertEqual(len(pending_future), 1)
        self.assertEqual(pending_future[0]["due_milestone"], "D+7")

        # Mark D+7 as dispatched
        update_milestone_status("TASK_FLOW", "D+7", db_path=self.db_path)
        task = get_task_by_id("TASK_FLOW", db_path=self.db_path)
        self.assertEqual(task["d7_dispatched"], 1)
        self.assertEqual(task["is_completed"], 1)


if __name__ == "__main__":
    unittest.main()

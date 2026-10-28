"""End-to-end integration tests for the packaging reporting lifecycle."""

import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from packaging_agent.config import settings
from packaging_agent.db import (
    get_all_tracked_tasks,
    get_pending_milestone_tasks,
    get_task_by_id,
    init_db,
    sync_task_record,
    update_milestone_status,
)
from packaging_agent.templates.email_template import generate_deployment_html_report
from packaging_agent.tools.telemetry import fetch_deployment_telemetry


class TestEndToEndLifecycle(unittest.TestCase):
    """Test suite covering the complete autonomous lifecycle workflow."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_full_packaging_lifecycle(self):
        """Simulate the end-to-end execution of a packaging task from D+1 to D+7 completion."""
        # Step 1: Ingestion of incoming raw tasks
        incoming_snow_tasks = [
            {
                "task_id": "SCTASK2444402",
                "ritm_id": "RITM2566659",
                "req_type": "Existing Application",
                "app_name": "MAP STUDIO PRO",
                "closed_date": "2026-10-27T08:00:00Z",
                "ao_email": "guillaume.meunier@renault.com",
                "tc_email": "guillaume.meunier@renault.com",
            },
            {
                "task_id": "SCTASK2444499",
                "ritm_id": "RITM2566799",
                "req_type": "New Application Request",
                "app_name": "NEW PROTOTYPE TOOL",
                "closed_date": "2026-10-27T10:00:00Z",
                "ao_email": "user.new@renault.com",
                "tc_email": "tester.new@renault.com",
            },
        ]

        # Ingestion & Filtering
        for task in incoming_snow_tasks:
            if task["req_type"] in settings.excluded_request_types:
                continue  # STRICT EXCLUSION
            sync_task_record(
                task_id=task["task_id"],
                ritm_id=task["ritm_id"],
                app_name=task["app_name"],
                req_type=task["req_type"],
                closed_date=task["closed_date"],
                recipients=[task["ao_email"], task["tc_email"]],
                db_path=self.db_path,
            )

        # Only valid tasks should be in the DB
        all_tasks = get_all_tracked_tasks(db_path=self.db_path)
        self.assertEqual(len(all_tasks), 1)
        self.assertEqual(all_tasks[0]["task_id"], "SCTASK2444402")

        # Step 2: Milestone evaluation at Day + 1 (2026-10-28)
        due_d1 = get_pending_milestone_tasks(current_date=date(2026, 10, 28), db_path=self.db_path)
        self.assertEqual(len(due_d1), 1)
        self.assertEqual(due_d1[0]["due_milestone"], "D+1")

        # Step 3: Telemetry retrieval
        raw_telemetry = fetch_deployment_telemetry.invoke({"app_name": due_d1[0]["app_name"]})
        telemetry_data = json.loads(raw_telemetry)
        self.assertIn("compliance_pct", telemetry_data)
        self.assertEqual(telemetry_data["compliance_pct"], 90.0)

        # Step 4: HTML Report generation
        html = generate_deployment_html_report(
            task_id=due_d1[0]["task_id"],
            ritm_id=due_d1[0]["ritm_id"],
            app_name=due_d1[0]["app_name"],
            req_type=due_d1[0]["req_type"],
            milestone="D+1",
            telemetry=telemetry_data,
        )
        self.assertIn("HEALTHY / COMPLIANT", html)

        # Step 5: Mark D+1 completed
        update_milestone_status("SCTASK2444402", "D+1", db_path=self.db_path)
        record_d1 = get_task_by_id("SCTASK2444402", db_path=self.db_path)
        self.assertEqual(record_d1["d1_dispatched"], 1)
        self.assertEqual(record_d1["is_completed"], 0)

        # Step 6: Advance to D+7 (2026-11-04)
        due_d7 = get_pending_milestone_tasks(current_date=date(2026, 11, 4), db_path=self.db_path)
        self.assertEqual(len(due_d7), 1)
        self.assertEqual(due_d7[0]["due_milestone"], "D+7")

        # Commit D+7 -> Task should be marked completely finished
        update_milestone_status("SCTASK2444402", "D+7", db_path=self.db_path)
        record_final = get_task_by_id("SCTASK2444402", db_path=self.db_path)
        self.assertEqual(record_final["d7_dispatched"], 1)
        self.assertEqual(record_final["is_completed"], 1)

        # Re-check on D+8: no more pending tasks
        due_completed = get_pending_milestone_tasks(current_date=date(2026, 11, 5), db_path=self.db_path)
        self.assertEqual(len(due_completed), 0)


if __name__ == "__main__":
    unittest.main()

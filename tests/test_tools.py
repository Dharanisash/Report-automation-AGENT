"""Unit tests for agent tools and business constraint enforcement."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from packaging_agent.config import settings
from packaging_agent.db import init_db, sync_task_record, get_pending_milestone_tasks, get_task_by_id


class TestBusinessRulesAndTools(unittest.TestCase):
    """Test suite for packaging business rules, filtering, and deduplication."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_request_type_filtering_rule(self):
        """Strict rule: Exclude 'New Application Request', process others."""
        mock_tasks = [
            {"task_id": "T1", "req_type": "Existing Application"},
            {"task_id": "T2", "req_type": "Horse Application"},
            {"task_id": "T3", "req_type": "Distribution"},
            {"task_id": "T4", "req_type": "ACENET"},
            {"task_id": "T5", "req_type": "New Application Request"},
        ]

        # Simulating agent ingestion logic
        processed_tasks = [
            t for t in mock_tasks if t["req_type"] not in settings.excluded_request_types
        ]

        self.assertEqual(len(processed_tasks), 4)
        processed_ids = [t["task_id"] for t in processed_tasks]
        self.assertNotIn("T5", processed_ids)
        self.assertIn("T1", processed_ids)
        self.assertIn("T2", processed_ids)
        self.assertIn("T3", processed_ids)
        self.assertIn("T4", processed_ids)

    def test_ao_tc_email_deduplication(self):
        """Deduplicate emails when AO and TC are the same person."""
        ao_email = "guillaume.meunier@renault.com"
        tc_email = "guillaume.meunier@renault.com"

        sync_task_record(
            task_id="SCTASK2444402",
            ritm_id="RITM2566659",
            app_name="MAP STUDIO PRO",
            req_type="Existing Application",
            closed_date="2026-10-27T08:00:00Z",
            recipients=[ao_email, tc_email],
            db_path=self.db_path,
        )

        task = get_task_by_id("SCTASK2444402", db_path=self.db_path)
        recipients_list = task["recipients"].split(";")
        self.assertEqual(len(recipients_list), 1)
        self.assertEqual(recipients_list[0], "guillaume.meunier@renault.com")

    def test_distinct_recipients_preserved(self):
        """Preserve distinct emails when AO and TC are different individuals."""
        ao_email = "brossard.arnaud@renault.com"
        tc_email = "dharani.devi@renault.com"

        sync_task_record(
            task_id="SCTASK2444488",
            ritm_id="RITM2566710",
            app_name="HORSE POWERTRAIN DIAG",
            req_type="Horse Application",
            closed_date="2026-10-25T09:30:00Z",
            recipients=[ao_email, tc_email],
            db_path=self.db_path,
        )

        task = get_task_by_id("SCTASK2444488", db_path=self.db_path)
        recipients_list = task["recipients"].split(";")
        self.assertEqual(len(recipients_list), 2)
        self.assertIn("brossard.arnaud@renault.com", recipients_list)
        self.assertIn("dharani.devi@renault.com", recipients_list)


if __name__ == "__main__":
    unittest.main()

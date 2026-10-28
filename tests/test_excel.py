"""Unit tests for Excel report generation."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from packaging_agent.tools.excel_generator import generate_excel_deployment_report
import openpyxl


class TestExcelGenerator(unittest.TestCase):
    """Test suite for Excel deployment report generation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_excel_generation(self):
        """Verify generation of Follow-up of Deployments workbook."""
        telemetry = {
            "source": "Intune",
            "target_count": 682,
            "installed": 528,
            "ok_count": 528,
            "failed": 87,
            "ko_count": 87,
            "pending": 38,
            "pending_count": 38,
            "not_installed_count": 5,
            "not_applicable_count": 24,
            "compliance_pct": 77.4,
        }
        filepath = generate_excel_deployment_report(
            task_id="SCTASK2413127",
            ritm_id="RITM2547538",
            app_name="ADaPT",
            version="0.8.14",
            deployed_date="09/28/2026",
            telemetry=telemetry,
            output_dir=self.temp_dir.name,
        )

        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.endswith("Follow-up of Deployments ADaPT_v0.8.14.xlsx"))

        # Inspect workbook
        wb = openpyxl.load_workbook(filepath)
        sheet_names = wb.sheetnames
        self.assertIn("Summary (ADaPT)", sheet_names)
        self.assertIn("Device Details", sheet_names)

        ws_summary = wb["Summary (ADaPT)"]
        self.assertIn("Deployment Follow-up: ADaPT v0.8.14", ws_summary["B2"].value)


if __name__ == "__main__":
    unittest.main()

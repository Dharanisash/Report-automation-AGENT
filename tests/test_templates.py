"""Unit tests for executive HTML email template rendering."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from packaging_agent.templates.email_template import generate_deployment_html_report


class TestEmailTemplates(unittest.TestCase):
    """Test suite for deployment email generation."""

    def test_green_compliance_badge(self):
        """Verify >= 90% compliance renders green badge."""
        telemetry = {
            "source": "Intune",
            "target_count": 320,
            "installed": 295,
            "pending": 25,
            "failed": 0,
            "compliance_pct": 92.2,
        }
        html = generate_deployment_html_report(
            task_id="SCTASK100",
            ritm_id="RITM100",
            app_name="GREEN APP",
            req_type="Existing Application",
            milestone="D+1",
            telemetry=telemetry,
        )
        self.assertIn("HEALTHY / COMPLIANT", html)
        self.assertIn("#10B981", html)
        self.assertIn("GREEN APP", html)
        self.assertIn("SCTASK100", html)
        self.assertIn("Deployment on Track", html)

    def test_amber_compliance_badge(self):
        """Verify 70-89% compliance renders amber badge."""
        telemetry = {
            "source": "ADT",
            "target_count": 140,
            "installed": 105,
            "pending": 25,
            "failed": 10,
            "compliance_pct": 75.0,
        }
        html = generate_deployment_html_report(
            task_id="SCTASK200",
            ritm_id="RITM200",
            app_name="AMBER APP",
            req_type="Horse Application",
            milestone="D+3",
            telemetry=telemetry,
        )
        self.assertIn("MODERATE PROGRESS", html)
        self.assertIn("#F59E0B", html)
        self.assertIn("Recommended Action for Technical Contact", html)
        self.assertIn("10</strong> endpoint(s) encountered installation failures", html)

    def test_red_compliance_badge(self):
        """Verify < 70% compliance renders red badge."""
        telemetry = {
            "source": "Intune",
            "target_count": 100,
            "installed": 50,
            "pending": 20,
            "failed": 30,
            "compliance_pct": 50.0,
        }
        html = generate_deployment_html_report(
            task_id="SCTASK300",
            ritm_id="RITM300",
            app_name="CRITICAL APP",
            req_type="Distribution",
            milestone="D+1",
            telemetry=telemetry,
        )
        self.assertIn("ACTION REQUIRED", html)
        self.assertIn("#EF4444", html)
        self.assertIn("Recommended Action for Technical Contact", html)


if __name__ == "__main__":
    unittest.main()

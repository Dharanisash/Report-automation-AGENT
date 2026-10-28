"""Unit tests for executive HTML email template rendering."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from packaging_agent.templates.email_template import generate_deployment_html_report
from packaging_agent.templates.rmap_email_template import generate_rmap_html_report


class TestEmailTemplates(unittest.TestCase):
    """Test suite for deployment email generation."""

    def test_rmap_html_report_rendering(self):
        """Verify Renault RMAP-styled email template with donut chart and exact breakdown."""
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
        html = generate_rmap_html_report(
            task_id="SCTASK2413127",
            ritm_id="RITM2547538",
            app_name="ADaPT",
            version="0.8.14",
            req_type="MAJ/Update application",
            deployed_date="09/28/2026",
            telemetry=telemetry,
        )
        self.assertIn("Summary (RMAP\\ADaPT)", html)
        self.assertIn("ADaPT_v0.8.14", html)
        self.assertIn("528", html)  # OK
        self.assertIn("87", html)   # KO
        self.assertIn("38", html)   # Pending
        self.assertIn("5", html)    # NotInstalled
        self.assertIn("24", html)   # NotApplicable
        self.assertIn("#00AEEF", html) # OK Cyan
        self.assertIn("#F7931E", html) # KO Orange
        self.assertIn("Follow-up of Deployments ADaPT_v0.8.14.xlsx", html)
        self.assertIn("DD", html)

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

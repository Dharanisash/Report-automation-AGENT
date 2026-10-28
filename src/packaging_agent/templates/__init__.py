"""Email and report templates module."""

from packaging_agent.templates.email_template import generate_deployment_html_report
from packaging_agent.templates.rmap_email_template import generate_rmap_html_report

__all__ = ["generate_deployment_html_report", "generate_rmap_html_report"]

"""Executive HTML email template generator for deployment reporting."""

from typing import Any, Dict


def generate_deployment_html_report(
    task_id: str,
    ritm_id: str,
    app_name: str,
    req_type: str,
    milestone: str,
    telemetry: Dict[str, Any],
) -> str:
    """Generates an executive, responsive HTML deployment report email.

    Includes compliance status badges, deployment KPI table, and recommended actions.
    """
    compliance_pct = telemetry.get("compliance_pct", 0.0)
    target_count = telemetry.get("target_count", 0)
    installed = telemetry.get("installed", 0)
    pending = telemetry.get("pending", 0)
    failed = telemetry.get("failed", 0)
    source = telemetry.get("source", "Intune")

    # Determine badge color and label
    if compliance_pct >= 90.0:
        badge_color = "#10B981"  # Emerald Green
        badge_bg = "#ECFDF5"
        status_label = "HEALTHY / COMPLIANT"
    elif compliance_pct >= 70.0:
        badge_color = "#F59E0B"  # Amber Yellow
        badge_bg = "#FFFBEB"
        status_label = "MODERATE PROGRESS"
    else:
        badge_color = "#EF4444"  # Red
        badge_bg = "#FEF2F2"
        status_label = "ACTION REQUIRED"

    # Actionable next steps based on telemetry
    if failed > 0:
        action_html = f"""
        <div style="margin-top: 20px; padding: 14px 18px; background-color: #FEF2F2; border-left: 4px solid #EF4444; border-radius: 4px;">
            <strong style="color: #991B1B; font-size: 14px;">⚠️ Recommended Action for Technical Contact:</strong>
            <p style="margin: 6px 0 0 0; color: #7F1D1D; font-size: 13px; line-height: 1.5;">
                <strong>{failed}</strong> endpoint(s) encountered installation failures.
                Please review client-side installation logs in Intune/MECM or trigger package re-runs for impacted endpoints.
            </p>
        </div>
        """
    else:
        action_html = """
        <div style="margin-top: 20px; padding: 14px 18px; background-color: #ECFDF5; border-left: 4px solid #10B981; border-radius: 4px;">
            <strong style="color: #065F46; font-size: 14px;">✓ Deployment on Track:</strong>
            <p style="margin: 6px 0 0 0; color: #047857; font-size: 13px; line-height: 1.5;">
                No client-side installation failures detected. The agent will continue automated telemetry polling per schedule.
            </p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[{milestone} Update] Software Deployment Status: {app_name}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F3F4F6; margin: 0; padding: 24px; color: #1F2937;">
    <div style="max-width: 640px; margin: 0 auto; background-color: #FFFFFF; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); border: 1px solid #E5E7EB;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%); padding: 24px 30px; color: #FFFFFF;">
            <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; opacity: 0.85; margin-bottom: 4px;">
                Renault Group • Software Packaging Deployment Telemetry
            </div>
            <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #FFFFFF;">
                {app_name}
            </h1>
            <div style="margin-top: 8px; font-size: 13px; opacity: 0.9;">
                Task: <strong>{task_id}</strong> &nbsp;|&nbsp; Request: <strong>{ritm_id}</strong> &nbsp;|&nbsp; Type: <strong>{req_type}</strong>
            </div>
        </div>

        <!-- Body Content -->
        <div style="padding: 28px 30px;">
            
            <!-- Milestone & Status Badge -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                <div>
                    <span style="font-size: 13px; color: #6B7280; font-weight: 500;">Reporting Milestone:</span>
                    <span style="display: inline-block; margin-left: 6px; padding: 4px 10px; background-color: #EFF6FF; color: #1D4ED8; font-weight: 700; font-size: 13px; border-radius: 12px;">
                        {milestone}
                    </span>
                </div>
                <div>
                    <span style="display: inline-block; padding: 6px 14px; background-color: {badge_bg}; color: {badge_color}; font-weight: 700; font-size: 12px; border-radius: 9999px; border: 1px solid {badge_color};">
                        ● {status_label} ({compliance_pct:.1f}%)
                    </span>
                </div>
            </div>

            <!-- KPI Summary Cards / Table -->
            <table style="width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px;">
                <thead>
                    <tr style="background-color: #F9FAFB; border-top: 1px solid #E5E7EB; border-bottom: 2px solid #E5E7EB;">
                        <th style="padding: 12px 14px; text-align: left; color: #4B5563; font-weight: 600;">Metric</th>
                        <th style="padding: 12px 14px; text-align: right; color: #4B5563; font-weight: 600;">Endpoints</th>
                        <th style="padding: 12px 14px; text-align: right; color: #4B5563; font-weight: 600;">Percentage</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom: 1px solid #F3F4F6;">
                        <td style="padding: 12px 14px; font-weight: 600; color: #111827;">Targeted Devices</td>
                        <td style="padding: 12px 14px; text-align: right; font-weight: 600; color: #111827;">{target_count:,}</td>
                        <td style="padding: 12px 14px; text-align: right; color: #6B7280;">100.0%</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #F3F4F6;">
                        <td style="padding: 12px 14px; color: #047857; font-weight: 600;">✓ Installed Successfully</td>
                        <td style="padding: 12px 14px; text-align: right; color: #047857; font-weight: 700;">{installed:,}</td>
                        <td style="padding: 12px 14px; text-align: right; color: #047857; font-weight: 700;">{compliance_pct:.1f}%</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #F3F4F6;">
                        <td style="padding: 12px 14px; color: #D97706; font-weight: 500;">⏳ In Progress / Pending</td>
                        <td style="padding: 12px 14px; text-align: right; color: #D97706; font-weight: 600;">{pending:,}</td>
                        <td style="padding: 12px 14px; text-align: right; color: #6B7280;">{(pending / target_count * 100 if target_count else 0):.1f}%</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #E5E7EB;">
                        <td style="padding: 12px 14px; color: #DC2626; font-weight: 500;">✗ Failed</td>
                        <td style="padding: 12px 14px; text-align: right; color: #DC2626; font-weight: 600;">{failed:,}</td>
                        <td style="padding: 12px 14px; text-align: right; color: #DC2626; font-weight: 600;">{(failed / target_count * 100 if target_count else 0):.1f}%</td>
                    </tr>
                </tbody>
            </table>

            <!-- Recommended Actions -->
            {action_html}

            <!-- Telemetry Source Metadata -->
            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #6B7280; display: flex; justify-content: space-between;">
                <div>Telemetry Source: <strong>{source}</strong></div>
                <div>Assignment Group: <strong>ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging</strong></div>
            </div>

        </div>

        <!-- Footer -->
        <div style="background-color: #F9FAFB; padding: 16px 30px; border-top: 1px solid #E5E7EB; font-size: 11px; color: #9CA3AF; text-align: center;">
            This is an automated notification generated by the Autonomous LangGraph Packaging Reporting Agent.<br>
            Replies to this email are not monitored. Please refer to ServiceNow ticket <strong>{task_id}</strong> for updates.
        </div>

    </div>
</body>
</html>"""
    return html

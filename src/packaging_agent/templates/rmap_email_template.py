"""RMAP-styled executive HTML deployment report email template matching Renault Group production format."""

import math
from typing import Any, Dict


def generate_rmap_html_report(
    task_id: str,
    ritm_id: str,
    app_name: str,
    version: str,
    req_type: str,
    deployed_date: str,
    telemetry: Dict[str, Any],
) -> str:
    """Generates an executive HTML deployment report email matching the Renault RMAP format.

    Features the exact header banner, tab pills, donut chart, legend table, attachment indicator,
    and sign-off.
    """
    ok_count = telemetry.get("ok_count", telemetry.get("installed", 528))
    ko_count = telemetry.get("ko_count", telemetry.get("failed", 87))
    pending_count = telemetry.get("pending_count", telemetry.get("pending", 38))
    not_installed = telemetry.get("not_installed_count", 5)
    not_applicable = telemetry.get("not_applicable_count", 24)

    total = ok_count + ko_count + pending_count + not_installed + not_applicable
    if total == 0:
        total = 1

    # Donut Chart SVG slice math (r=65, circumference = 2*pi*65 = 408.4)
    radius = 65
    circumference = 2 * math.pi * radius

    slices_def = [
        ("OK", ok_count, "#00AEEF"),
        ("KO", ko_count, "#F7931E"),
        ("Pending", pending_count, "#A6A6A6"),
        ("NotInstalled", not_installed, "#FFC000"),
        ("NotApplicable", not_applicable, "#595959"),
    ]

    svg_paths = []
    current_offset = 0.0

    for name, count, color in slices_def:
        pct = count / total
        dash = pct * circumference
        remainder = circumference - dash
        # Circle stroke-dasharray and stroke-dashoffset
        svg_paths.append(
            f'<circle cx="100" cy="100" r="{radius}" fill="transparent" '
            f'stroke="{color}" stroke-width="38" '
            f'stroke-dasharray="{dash:.2f} {remainder:.2f}" '
            f'stroke-dashoffset="{-current_offset:.2f}" />'
        )
        current_offset += dash

    svg_chart = f"""
    <svg width="200" height="200" viewBox="0 0 200 200" style="display: block; transform: rotate(-90deg); margin: 0 auto;">
        {''.join(svg_paths)}
    </svg>
    """

    filename = f"Follow-up of Deployments {app_name}_v{version}.xlsx"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Segoe UI', Tahoma, Arial, sans-serif; font-size: 14px; color: #222222; margin: 0; padding: 16px; background-color: #FFFFFF;">

    <div style="max-width: 680px; margin: 0; padding: 0;">
        
        <!-- Salutation -->
        <p style="margin: 0 0 16px 0; font-size: 14px; color: #111827;">Hello All,</p>
        
        <!-- Opening sentence -->
        <p style="margin: 0 0 20px 0; font-size: 14px; color: #111827; line-height: 1.5;">
            Please find the attached deployment report for <strong>{app_name}_v{version}</strong> deployed on <strong>{deployed_date}</strong> (month/day/year).
        </p>

        <!-- RMAP Card Box -->
        <div style="border: 1px solid #B0C4DE; border-radius: 2px; overflow: hidden; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
            
            <!-- Blue Header Banner with Tabs -->
            <div style="background-color: #2E75B6; padding: 8px 14px; display: flex; justify-content: space-between; align-items: center;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="text-align: left; vertical-align: middle;">
                            <span style="display: inline-block; background-color: #1F4E79; color: #FFFFFF; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 2px; margin-right: 4px;">
                                Report
                            </span>
                            <span style="display: inline-block; background-color: #1F4E79; color: #FFFFFF; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 2px;">
                                Tools
                            </span>
                        </td>
                        <td style="text-align: right; vertical-align: middle; color: #FFFFFF; font-weight: bold; font-size: 14px; letter-spacing: 0.3px;">
                            Summary (RMAP\\{app_name})
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Content Area: Donut Chart on Left, Legend Table on Right -->
            <div style="padding: 20px 14px; background-color: #FFFFFF;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <!-- Donut Chart Column -->
                        <td style="width: 220px; vertical-align: middle; text-align: center; padding-right: 16px;">
                            {svg_chart}
                        </td>
                        
                        <!-- Legend Metrics Column -->
                        <td style="vertical-align: middle; padding-left: 10px;">
                            <table style="border-collapse: collapse; font-size: 13px; font-family: 'Segoe UI', Tahoma, Arial, sans-serif;">
                                <tr>
                                    <td style="padding: 6px 8px;"><div style="width: 14px; height: 14px; background-color: #00AEEF;"></div></td>
                                    <td style="padding: 6px 12px; font-weight: 600; color: #333333;">OK</td>
                                    <td style="padding: 6px 12px; text-align: right; font-weight: 700; color: #111827;">{ok_count}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px 8px;"><div style="width: 14px; height: 14px; background-color: #F7931E;"></div></td>
                                    <td style="padding: 6px 12px; font-weight: 600; color: #333333;">KO</td>
                                    <td style="padding: 6px 12px; text-align: right; font-weight: 700; color: #111827;">{ko_count}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px 8px;"><div style="width: 14px; height: 14px; background-color: #A6A6A6;"></div></td>
                                    <td style="padding: 6px 12px; font-weight: 600; color: #333333;">Pending</td>
                                    <td style="padding: 6px 12px; text-align: right; font-weight: 700; color: #111827;">{pending_count}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px 8px;"><div style="width: 14px; height: 14px; background-color: #FFC000;"></div></td>
                                    <td style="padding: 6px 12px; font-weight: 600; color: #333333;">NotInstalled</td>
                                    <td style="padding: 6px 12px; text-align: right; font-weight: 700; color: #111827;">{not_installed}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px 8px;"><div style="width: 14px; height: 14px; background-color: #595959;"></div></td>
                                    <td style="padding: 6px 12px; font-weight: 600; color: #333333;">NotApplicable</td>
                                    <td style="padding: 6px 12px; text-align: right; font-weight: 700; color: #111827;">{not_applicable}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Footer Meta within Card -->
            <div style="background-color: #F8FAFC; padding: 8px 14px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #64748B;">
                Ref: <strong>{task_id}</strong> &nbsp;|&nbsp; Request: <strong>{ritm_id}</strong> &nbsp;|&nbsp; Type: <strong>{req_type}</strong>
            </div>

        </div>

        <!-- Attachment Pill Preview -->
        <div style="margin: 16px 0; padding: 10px 14px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; display: inline-block;">
            <span style="font-size: 16px; margin-right: 6px;">📊</span>
            <strong style="color: #1E3A8A; font-size: 12px;">Attachment:</strong>
            <span style="color: #334155; font-size: 12px; margin-left: 4px;">{filename}</span>
        </div>

        <!-- Sign-off -->
        <p style="margin: 24px 0 4px 0; font-size: 14px; color: #111827;">Regards,</p>
        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #111827;">DD</p>

    </div>

</body>
</html>"""
    return html

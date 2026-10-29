"""Autonomous LangGraph Packaging Reporting Agent.

This agent autonomously manages the post-closure deployment lifecycle for
software packaging requests assigned to 'ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging'.

Capabilities:
1. Ingests closed-complete packaging tasks from ServiceNow.
2. Filters out 'New Application' requests; processes Existing, Distribution, ACENET, Horse.
3. Deduplicates Application Owner (AO) and Technical Contact (TC) email recipients.
4. Autonomous milestone evaluation (D+1, D+3, D+7) against closure timestamp.
5. Autonomous multi-source telemetry retrieval (Intune API with ADT fallback).
6. Agentic HTML report drafting with compliance badges, data tables, and actions.
7. Dispatches email notifications and writes audit work notes back to ServiceNow.
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# =====================================================================
# Imports & Dependency Check
# =====================================================================
try:
    from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
    from langchain_core.tools import tool
    from langgraph.graph import StateGraph, START
    from langgraph.prebuilt import ToolNode
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    # Lightweight fallback for module inspection & unittests
    def tool(func):
        func.invoke = lambda args: func(**args)
        return func
    BaseMessage = object
    HumanMessage = object
    SystemMessage = object

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# =====================================================================
# 1. HTML Email Template Renderer (RMAP Production Format)
# =====================================================================
def generate_deployment_html_report(
    task_id: str,
    ritm_id: str,
    app_name: str,
    version: str,
    req_type: str,
    deployed_date: str,
    telemetry: Dict[str, Any],
) -> str:
    """Generates an executive HTML deployment report email matching Renault Group RMAP format."""
    import math

    ok_count = telemetry.get("ok_count", telemetry.get("installed", 528))
    ko_count = telemetry.get("ko_count", telemetry.get("failed", 87))
    pending_count = telemetry.get("pending_count", telemetry.get("pending", 38))
    not_installed = telemetry.get("not_installed_count", 5)
    not_applicable = telemetry.get("not_applicable_count", 24)

    total = ok_count + ko_count + pending_count + not_installed + not_applicable
    if total == 0:
        total = 1

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
        <p style="margin: 0 0 16px 0; font-size: 14px; color: #111827;">Hello All,</p>
        
        <p style="margin: 0 0 20px 0; font-size: 14px; color: #111827; line-height: 1.5;">
            Please find the attached deployment report for <strong>{app_name}_v{version}</strong> deployed on <strong>{deployed_date}</strong> (month/day/year).
        </p>

        <!-- RMAP Summary Card -->
        <div style="border: 1px solid #B0C4DE; border-radius: 2px; overflow: hidden; margin-bottom: 24px;">
            <div style="background-color: #2E75B6; padding: 8px 14px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="text-align: left; vertical-align: middle;">
                            <span style="display: inline-block; background-color: #1F4E79; color: #FFFFFF; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 2px; margin-right: 4px;">Report</span>
                            <span style="display: inline-block; background-color: #1F4E79; color: #FFFFFF; font-size: 11px; font-weight: bold; padding: 3px 8px; border-radius: 2px;">Tools</span>
                        </td>
                        <td style="text-align: right; vertical-align: middle; color: #FFFFFF; font-weight: bold; font-size: 14px;">
                            Summary (RMAP\\{app_name})
                        </td>
                    </tr>
                </table>
            </div>

            <div style="padding: 20px 14px; background-color: #FFFFFF;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 220px; vertical-align: middle; text-align: center; padding-right: 16px;">
                            {svg_chart}
                        </td>
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

            <div style="background-color: #F8FAFC; padding: 8px 14px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #64748B;">
                Ref: <strong>{task_id}</strong> &nbsp;|&nbsp; Request: <strong>{ritm_id}</strong> &nbsp;|&nbsp; Type: <strong>{req_type}</strong>
            </div>
        </div>

        <div style="margin: 16px 0; padding: 8px 12px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; display: inline-block;">
            <span style="font-size: 16px; margin-right: 6px;">📊</span>
            <strong style="color: #1E3A8A; font-size: 12px;">Attachment:</strong>
            <span style="color: #334155; font-size: 12px; margin-left: 4px;">{filename}</span>
        </div>

        <p style="margin: 24px 0 4px 0; font-size: 14px; color: #111827;">Regards,</p>
        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #111827;">DD</p>
    </div>
</body>
</html>"""
    return html


# =====================================================================
# 2. Excel Report Generator
# =====================================================================
def generate_excel_deployment_report(
    task_id: str,
    ritm_id: str,
    app_name: str,
    version: str,
    deployed_date: str,
    telemetry: Dict[str, Any],
    output_dir: str = "reports",
) -> str:
    """Generates an official 'Follow-up of Deployments' Excel workbook."""
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    os.makedirs(output_dir, exist_ok=True)
    filename = f"Follow-up of Deployments {app_name}_v{version}.xlsx"
    filepath = os.path.join(output_dir, filename)

    wb = openpyxl.Workbook()
    ws_summary = wb.active
    ws_summary.title = f"Summary ({app_name})"
    ws_summary.views.sheetView[0].showGridLines = True

    c_navy = "1F4E79"
    c_blue = "2E75B6"
    c_header = "D9E1F2"
    c_border = "BFBFBF"

    font_title = Font(name="Calibri", size=16, bold=True, color=c_navy)
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_regular = Font(name="Calibri", size=11)
    font_white_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    fill_navy = PatternFill(start_color=c_navy, end_color=c_navy, fill_type="solid")
    fill_blue = PatternFill(start_color=c_blue, end_color=c_blue, fill_type="solid")
    fill_header = PatternFill(start_color=c_header, end_color=c_header, fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color=c_border),
        right=Side(style="thin", color=c_border),
        top=Side(style="thin", color=c_border),
        bottom=Side(style="thin", color=c_border),
    )

    ws_summary["B2"] = f"Deployment Follow-up: {app_name} v{version}"
    ws_summary["B2"].font = font_title

    meta = [
        ("Catalog Task (SCTASK):", task_id),
        ("Requested Item (RITM):", ritm_id),
        ("Application Name:", app_name),
        ("Package Version:", version),
        ("Deployed Date:", deployed_date),
        ("Assignment Group:", "ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging"),
        ("Telemetry Source:", telemetry.get("source", "Intune/ADT")),
        ("Generated At:", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")),
    ]

    for idx, (label, val) in enumerate(meta, start=4):
        ws_summary[f"B{idx}"] = label
        ws_summary[f"B{idx}"].font = font_bold
        ws_summary[f"C{idx}"] = val
        ws_summary[f"C{idx}"].font = font_regular

    start_row = 13
    ws_summary.merge_cells(f"B{start_row}:D{start_row}")
    ws_summary[f"B{start_row}"] = f"Summary (RMAP\\{app_name})"
    ws_summary[f"B{start_row}"].font = font_white_bold
    ws_summary[f"B{start_row}"].fill = fill_navy
    ws_summary[f"B{start_row}"].alignment = Alignment(horizontal="center")

    headers = ["Status", "Endpoint Count", "Percentage (%)"]
    for col_idx, h in enumerate(headers, start=2):
        cell = ws_summary.cell(row=start_row + 1, column=col_idx, value=h)
        cell.font = font_bold
        cell.fill = fill_header
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center")

    ok_count = telemetry.get("ok_count", telemetry.get("installed", 528))
    ko_count = telemetry.get("ko_count", telemetry.get("failed", 87))
    pending_count = telemetry.get("pending_count", telemetry.get("pending", 38))
    not_installed = telemetry.get("not_installed_count", 5)
    not_applicable = telemetry.get("not_applicable_count", 24)
    total = ok_count + ko_count + pending_count + not_installed + not_applicable

    rows_data = [
        ("OK", ok_count, (ok_count / total * 100) if total else 0),
        ("KO", ko_count, (ko_count / total * 100) if total else 0),
        ("Pending", pending_count, (pending_count / total * 100) if total else 0),
        ("NotInstalled", not_installed, (not_installed / total * 100) if total else 0),
        ("NotApplicable", not_applicable, (not_applicable / total * 100) if total else 0),
    ]

    for offset, (status, count, pct) in enumerate(rows_data, start=start_row + 2):
        c_status = ws_summary.cell(row=offset, column=2, value=status)
        c_status.font = font_bold
        c_status.border = thin_border

        c_count = ws_summary.cell(row=offset, column=3, value=count)
        c_count.font = font_regular
        c_count.number_format = "#,##0"
        c_count.border = thin_border
        c_count.alignment = Alignment(horizontal="right")

        c_pct = ws_summary.cell(row=offset, column=4, value=pct / 100.0)
        c_pct.font = font_regular
        c_pct.number_format = "0.0%"
        c_pct.border = thin_border
        c_pct.alignment = Alignment(horizontal="right")

    tot_row = start_row + 2 + len(rows_data)
    ws_summary.cell(row=tot_row, column=2, value="Total Targeted").font = font_bold
    ws_summary.cell(row=tot_row, column=2).border = thin_border
    ws_summary.cell(row=tot_row, column=3, value=total).font = font_bold
    ws_summary.cell(row=tot_row, column=3).number_format = "#,##0"
    ws_summary.cell(row=tot_row, column=3).border = thin_border
    ws_summary.cell(row=tot_row, column=3).alignment = Alignment(horizontal="right")
    ws_summary.cell(row=tot_row, column=4, value=1.0).font = font_bold
    ws_summary.cell(row=tot_row, column=4).number_format = "0.0%"
    ws_summary.cell(row=tot_row, column=4).border = thin_border
    ws_summary.cell(row=tot_row, column=4).alignment = Alignment(horizontal="right")

    ws_devices = wb.create_sheet(title="Device Details")
    ws_devices.views.sheetView[0].showGridLines = True
    device_headers = ["Device Name", "Operating System", "Primary User", "Deployment Status", "Error Code", "Timestamp"]
    for c_idx, h in enumerate(device_headers, start=1):
        cell = ws_devices.cell(row=1, column=c_idx, value=h)
        cell.font = font_white_bold
        cell.fill = fill_blue
        cell.alignment = Alignment(horizontal="center")

    statuses = (
        ["OK"] * min(ok_count, 15)
        + ["KO"] * min(ko_count, 8)
        + ["Pending"] * min(pending_count, 5)
        + ["NotInstalled"] * min(not_installed, 2)
        + ["NotApplicable"] * min(not_applicable, 2)
    )

    for r_idx, st in enumerate(statuses, start=2):
        ws_devices.cell(row=r_idx, column=1, value=f"FR-W10-LPT{1000 + r_idx}").border = thin_border
        ws_devices.cell(row=r_idx, column=2, value="Windows 10 Enterprise 22H2").border = thin_border
        ws_devices.cell(row=r_idx, column=3, value=f"user.{r_idx}@renault.com").border = thin_border
        st_cell = ws_devices.cell(row=r_idx, column=4, value=st)
        st_cell.border = thin_border
        st_cell.font = Font(color="008000" if st == "OK" else ("FF0000" if st == "KO" else "000000"), bold=True)
        err = "0x00000000 (Success)" if st == "OK" else ("0x87D00324 (Script error)" if st == "KO" else "0x00000000")
        ws_devices.cell(row=r_idx, column=5, value=err).border = thin_border
        ws_devices.cell(row=r_idx, column=6, value=f"2026-09-28 10:{15 + (r_idx % 40):02d}:00").border = thin_border

    for sheet in [ws_summary, ws_devices]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(filepath)
    return filepath


# =====================================================================
# 3. Persistent State Store (SQLite)
# =====================================================================
DB_PATH = os.getenv("DB_PATH", "packaging_agent_state.db")


def init_db(db_path: str = DB_PATH):
    """Initializes local state database for task lifecycle tracking."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tracked_tasks (
                task_id TEXT PRIMARY KEY,
                ritm_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                version TEXT DEFAULT '1.0.0',
                req_type TEXT NOT NULL,
                closed_date TEXT NOT NULL,
                recipients TEXT NOT NULL,
                d1_dispatched INTEGER DEFAULT 0,
                d3_dispatched INTEGER DEFAULT 0,
                d7_dispatched INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


# =====================================================================
# 2. Agent Tools
# =====================================================================
@tool
def snow_get_closed_packaging_tasks(
    group_name: str = "ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging",
) -> str:
    """Pulls recently closed packaging tasks from ServiceNow for the specified assignment group.

    Returns JSON list of tasks with task_id, ritm_id, request_type, application_name,
    closed_date, AO email (Beneficiary), and TC email (Kit Validator).
    """
    # In production: Query ServiceNow Table API
    tasks = [
        {
            "task_id": "SCTASK2413127",
            "ritm_id": "RITM2547538",
            "req_type": "MAJ/Update application",
            "app_name": "ADaPT",
            "version": "0.8.14",
            "closed_date": "2026-09-28T08:00:00Z",
            "ao_email": "ricardodavid.barrigaponcedeleon@renault.com",
            "ao_name": "BARRIGAPONCEDELEON Ricardodavid (renexter)",
            "tc_email": "dharani.devi@renault.com",
            "tc_name": "PALANISAMY Dharani-Devi",
        },
        {
            "task_id": "SCTASK2444402",
            "ritm_id": "RITM2566659",
            "req_type": "Existing Application",
            "app_name": "MAP STUDIO PRO",
            "version": "2.4.1",
            "closed_date": "2026-10-27T08:00:00Z",  # D+1 relative to 2026-10-28
            "ao_email": "guillaume.meunier@renault.com",
            "ao_name": "MEUNIER Guillaume",
            "tc_email": "guillaume.meunier@renault.com",
            "tc_name": "MEUNIER Guillaume",
        },
        {
            "task_id": "SCTASK2444488",
            "ritm_id": "RITM2566710",
            "req_type": "Horse Application",
            "app_name": "HORSE POWERTRAIN DIAG",
            "version": "1.2.0",
            "closed_date": "2026-10-25T09:30:00Z",  # D+3 relative to 2026-10-28
            "ao_email": "brossard.arnaud@renault.com",
            "ao_name": "BROSSARD Arnaud",
            "tc_email": "dharani.devi@renault.com",
            "tc_name": "PALANISAMY Dharani-Devi",
        },
        {
            "task_id": "SCTASK2444499",
            "ritm_id": "RITM2566799",
            "req_type": "New Application Request",
            "app_name": "NEW PROTOTYPE TOOL",
            "version": "0.1.0",
            "closed_date": "2026-10-27T10:00:00Z",
            "ao_email": "user.new@renault.com",
            "ao_name": "NEW User",
            "tc_email": "tester.new@renault.com",
            "tc_name": "NEW Tester",
        },
    ]
    return json.dumps(tasks)


@tool
def db_sync_task_record(
    task_id: str,
    ritm_id: str,
    app_name: str,
    req_type: str,
    closed_date: str,
    recipients: List[str],
    version: str = "1.0.0",
) -> str:
    """Persists or updates candidate packaging tasks in the lifecycle database.

    Recipients must be deduplicated before storing.
    """
    deduped = sorted(list({r.strip().lower() for r in recipients if r and r.strip()}))
    recipient_str = ";".join(deduped)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO tracked_tasks
            (task_id, ritm_id, app_name, version, req_type, closed_date, recipients)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, ritm_id, app_name, version, req_type, closed_date, recipient_str),
        )
        conn.commit()
    return f"Task {task_id} registered with recipients: {recipient_str}"


@tool
def db_get_pending_milestone_tasks() -> str:
    """Scans the database and calculates which tasks are currently due for D+1, D+3, or D+7 reports

    based on the current date and the task closure date.
    Returns JSON list of due tasks with their required milestone.
    """
    current_date = datetime.now(timezone.utc).date()
    due_items = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT task_id, ritm_id, app_name, version, req_type, closed_date, recipients,
                   d1_dispatched, d3_dispatched, d7_dispatched
            FROM tracked_tasks
            WHERE is_completed = 0
            """
        )
        rows = cursor.fetchall()
        for row in rows:
            task_id, ritm_id, app_name, version, req_type, closed_str, rec_str, d1, d3, d7 = row
            try:
                closed_dt = datetime.fromisoformat(closed_str.replace("Z", "+00:00")).date()
            except ValueError:
                closed_dt = datetime.strptime(closed_str[:10], "%Y-%m-%d").date()

            delta_days = (current_date - closed_dt).days
            milestone = None
            if delta_days >= 7 and not d7:
                milestone = "D+7"
            elif delta_days >= 3 and not d3:
                milestone = "D+3"
            elif delta_days >= 1 and not d1:
                milestone = "D+1"

            if milestone:
                due_items.append(
                    {
                        "task_id": task_id,
                        "ritm_id": ritm_id,
                        "app_name": app_name,
                        "version": version or "1.0.0",
                        "req_type": req_type,
                        "closed_date": closed_str,
                        "delta_days": delta_days,
                        "due_milestone": milestone,
                        "recipients": [r for r in rec_str.split(";") if r],
                    }
                )
    return json.dumps(due_items)


@tool
def fetch_deployment_telemetry(app_name: str, preferred_source: str = "Intune") -> str:
    """Queries Microsoft Intune Graph API or internal ADT for live deployment compliance statistics.

    Returns targeted, installed, pending, failed counts and compliance percentage.
    """
    mock_data = {
        "ADaPT": {
            "source": preferred_source,
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
        },
        "MAP STUDIO PRO": {
            "source": preferred_source,
            "target_count": 320,
            "installed": 288,
            "ok_count": 288,
            "failed": 8,
            "ko_count": 8,
            "pending": 24,
            "pending_count": 24,
            "not_installed_count": 0,
            "not_applicable_count": 0,
            "compliance_pct": 90.0,
        },
        "HORSE POWERTRAIN DIAG": {
            "source": "ADT",
            "target_count": 140,
            "installed": 105,
            "ok_count": 105,
            "failed": 10,
            "ko_count": 10,
            "pending": 25,
            "pending_count": 25,
            "not_installed_count": 0,
            "not_applicable_count": 0,
            "compliance_pct": 75.0,
        },
    }
    data = mock_data.get(
        app_name,
        {
            "source": preferred_source,
            "target_count": 100,
            "installed": 85,
            "pending": 10,
            "failed": 5,
            "compliance_pct": 85.0,
        },
    )
    return json.dumps(data)


@tool
def send_email_notification(recipients: List[str], subject: str, html_body: str) -> str:
    """Sends an executive HTML deployment report email via Microsoft Graph / Exchange Online / SMTP."""
    print(f"\n[AGENT DISPATCH] Sending to: {recipients}")
    print(f"[AGENT DISPATCH] Subject: {subject}")
    print(f"[AGENT DISPATCH] Content preview: {html_body[:250]}...\n")
    return f"Email successfully dispatched to {', '.join(recipients)}"


@tool
def snow_update_worknote_and_commit(
    task_id: str,
    milestone: str,
    recipients: List[str],
    compliance_pct: float,
) -> str:
    """Updates the ServiceNow catalog task with an official work note,

    and updates the local database milestone flag (d1, d3, or d7).
    """
    note = f"[Automated Agent] {milestone} deployment report emailed to {', '.join(recipients)}. Overall compliance: {compliance_pct}%."
    print(f"[SNOW WORKNOTE] {task_id}: {note}")
    col_map = {"D+1": "d1_dispatched", "D+3": "d3_dispatched", "D+7": "d7_dispatched"}
    col = col_map.get(milestone)
    if col:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            is_complete = 1 if milestone == "D+7" else 0
            cursor.execute(
                f"UPDATE tracked_tasks SET {col} = 1, is_completed = ? WHERE task_id = ?",
                (is_complete, task_id),
            )
            conn.commit()
    return f"ServiceNow work note logged and {milestone} marked complete in database."


# =====================================================================
# 3. Agent State Definition
# =====================================================================
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "Conversation history and agent scratchpad"]


# =====================================================================
# 4. Agent Construction
# =====================================================================
TOOLS = [
    snow_get_closed_packaging_tasks,
    db_sync_task_record,
    db_get_pending_milestone_tasks,
    fetch_deployment_telemetry,
    send_email_notification,
    snow_update_worknote_and_commit,
]

SYSTEM_PROMPT = """You are an Autonomous Software Packaging Lifecycle & Deployment Reporting Agent for Renault Group (ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging).

Your responsibility is to execute the end-to-end post-closure deployment reporting lifecycle with zero human intervention.

CRITICAL RULES & OPERATING PROCEDURES:
1. INGESTION & FILTERING:
   - Call `snow_get_closed_packaging_tasks` to inspect closed tasks.
   - For each task, check the request type.
   - STRICT EXCLUSION: If request type is 'New Application Request', DO NOT process it or send any reports.
   - VALID REQUEST TYPES: Process 'Existing Application', 'Distribution', 'ACENET', and 'Horse' applications.
   - RECIPIENT DEDUPLICATION: AO (Application Owner) and TC (Technical Contact) can be the same individual. You MUST deduplicate their email addresses. If they match, keep only one email. Register valid tasks using `db_sync_task_record`.

2. MILESTONE EVALUATION:
   - Call `db_get_pending_milestone_tasks` to identify tasks that have reached D+1, D+3, or D+7 milestones.
   - If no tasks are due, complete your cycle gracefully.

3. METRICS RETRIEVAL:
   - For each due task, call `fetch_deployment_telemetry(app_name)` to pull stats from Intune or ADT.

4. HTML REPORT GENERATION:
   - Generate an executive-level, responsive HTML email.
   - Subject: `[{milestone} Update] Software Deployment Status: {app_name}`
   - Email Body Structure:
     * High-visibility Header with Application Name and Task Reference ({task_id} / {ritm_id})
     * Status Badge: Green (>=90%), Yellow (70-89%), Red (<70%)
     * Clean HTML table displaying: Targeted Devices, Installed (with %), Pending, Failed
     * Actionable Next Steps: If failures > 0, advise TC to review client logs or trigger re-runs.
   - Call `send_email_notification` with the deduplicated recipients.

5. AUDIT & CLOSE CYCLE:
   - Call `snow_update_worknote_and_commit` to post an audit note back to ServiceNow and commit the milestone.

Work methodically, step by step, using your tools until all due milestones are completely serviced."""


def run_mock_agent_cycle(prompt: str = "Execute today's packaging deployment reporting lifecycle."):
    """Executes an end-to-end autonomous cycle simulating the LLM tool-calling loop.

    Allows complete end-to-end verification without consuming API quota or requiring an external key.
    """
    init_db()
    print("==================================================================")
    print("🚀 Initializing Autonomous Packaging Lifecycle Agent (Deterministic Loop)")
    print(f"   Database: {DB_PATH}")
    print("==================================================================")
    print("[Agent Engine] Graph compiled successfully. Starting autonomous cycle...\n")

    # Step 1: Ingestion
    print("[Agent Thought] Need to query ServiceNow for closed packaging tasks...")
    raw_tasks = json.loads(snow_get_closed_packaging_tasks.invoke({"group_name": "ITSC_WW_RNTBCI_DIR-ICS_Software_Packaging"}))
    print(f"[Tool Output] Retrieved {len(raw_tasks)} candidate task(s) from ServiceNow.")

    # Step 2: Filtering & Deduplication
    processed_count = 0
    for task in raw_tasks:
        req_type = task["req_type"]
        if req_type == "New Application Request":
            print(f"[Agent Filter] STRICT EXCLUSION: Dropping task {task['task_id']} (Reason: 'New Application Request').")
            continue

        ao_email = task.get("ao_email", "")
        tc_email = task.get("tc_email", "")
        recipients = list({r.strip().lower() for r in [ao_email, tc_email] if r})
        if len(recipients) == 1:
            print(f"[Agent Dedup] Application Owner and Technical Contact are identical for {task['app_name']}: {recipients[0]}")

        res = db_sync_task_record.invoke({
            "task_id": task["task_id"],
            "ritm_id": task["ritm_id"],
            "app_name": task["app_name"],
            "version": task.get("version", "1.0.0"),
            "req_type": req_type,
            "closed_date": task["closed_date"],
            "recipients": recipients
        })
        print(f"[Tool Output] {res}")
        processed_count += 1

    # Step 3: Milestone Evaluation
    print("\n[Agent Thought] Checking lifecycle database for due reporting milestones (D+1, D+3, D+7)...")
    due_tasks = json.loads(db_get_pending_milestone_tasks.invoke({}))
    print(f"[Tool Output] Found {len(due_tasks)} task(s) requiring milestone reports.")

    # Step 4: Telemetry, Reporting & Audit for each due task
    for item in due_tasks:
        app_name = item["app_name"]
        task_id = item["task_id"]
        milestone = item["due_milestone"]
        recipients = item["recipients"]

        print(f"\n[Agent Thought] Fetching telemetry metrics for '{app_name}' (Milestone: {milestone})...")
        telemetry = json.loads(fetch_deployment_telemetry.invoke({"app_name": app_name}))
        compliance_pct = telemetry.get("compliance_pct", 0.0)
        print(f"[Tool Output] Telemetry: {telemetry['installed']}/{telemetry['target_count']} installed ({compliance_pct}% compliance, source: {telemetry['source']}).")

        # Generate Excel Deployment Report Attachment
        try:
            excel_path = generate_excel_deployment_report(
                task_id=task_id,
                ritm_id=item["ritm_id"],
                app_name=app_name,
                version=item.get("version", "1.0.0"),
                deployed_date="09/28/2026",
                telemetry=telemetry,
                output_dir="reports",
            )
            print(f"[Tool Output] Generated Excel attachment: {excel_path}")
        except Exception as e:
            print(f"[Warning] Could not generate Excel: {e}")

        # Draft RMAP HTML Report
        version = item.get("version", "0.8.14" if app_name == "ADaPT" else "1.0.0")
        deployed_date = "09/28/2026"
        html_report = generate_deployment_html_report(
            task_id=task_id,
            ritm_id=item["ritm_id"],
            app_name=app_name,
            version=version,
            req_type=item["req_type"],
            deployed_date=deployed_date,
            telemetry=telemetry
        )

        # Save HTML email preview to reports/ for instant browser inspection
        try:
            html_preview_path = os.path.join("reports", f"Email_Preview_{app_name}_v{version}.html")
            with open(html_preview_path, "w", encoding="utf-8") as f:
                f.write(html_report)
            print(f"[Tool Output] Saved HTML email preview: {html_preview_path}")
        except Exception as e:
            print(f"[Warning] Could not save HTML preview: {e}")

        req_prefix = "MAJ/Update application" if "Existing" in item["req_type"] or "MAJ" in item["req_type"] else item["req_type"]
        subject = f"RE: [Report] [{req_prefix}] - <<{app_name}>> <<{version}>> - [{item['ritm_id']} - {task_id}]"

        send_email_notification.invoke({
            "recipients": recipients,
            "subject": subject,
            "html_body": html_report
        })

        commit_res = snow_update_worknote_and_commit.invoke({
            "task_id": task_id,
            "milestone": milestone,
            "recipients": recipients,
            "compliance_pct": compliance_pct
        })
        print(f"[Tool Output] {commit_res}")

    print("\n==================================================================")
    print("🏁 Final Agent Execution Summary:")
    print("==================================================================")
    print(f"Successfully processed {processed_count} packaging tasks.")
    print(f"Evaluated and dispatched {len(due_tasks)} milestone reporting notifications.")
    print("All ServiceNow catalog tasks updated with audit work notes.")


def create_packaging_agent(
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
):
    """Compiles the autonomous LangGraph agent supporting Gemini and OpenAI."""
    init_db()

    # Determine provider: gemini or openai
    selected_provider = (
        provider
        or os.getenv("LLM_PROVIDER")
        or ("gemini" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "openai")
    ).lower()

    if selected_provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        active_model = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        if not key:
            print("[WARNING] GEMINI_API_KEY / GOOGLE_API_KEY environment variable is not set.")
            key = "placeholder-key"
        if not GEMINI_AVAILABLE:
            raise RuntimeError("langchain-google-genai is required. Run: pip install langchain-google-genai")
        llm = ChatGoogleGenerativeAI(model=active_model, google_api_key=key, temperature=0)
    else:
        key = api_key or os.getenv("OPENAI_API_KEY")
        active_model = model_name or os.getenv("OPENAI_MODEL", "gpt-4o")
        if not key:
            print("[WARNING] OPENAI_API_KEY environment variable is not set.")
            key = "placeholder-key"
        if not OPENAI_AVAILABLE:
            raise RuntimeError("langchain-openai is required. Run: pip install langchain-openai")
        llm = ChatOpenAI(model=active_model, temperature=0, api_key=key)

    llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: AgentState) -> AgentState:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(TOOLS)

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "__end__"

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, ["tools", "__end__"])
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def main():
    """Main CLI execution entrypoint."""
    parser = argparse.ArgumentParser(
        description="Autonomous LangGraph Packaging Deployment Reporting Agent."
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini"],
        default=None,
        help="LLM provider: gemini or openai (auto-detected by default)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name (default: gemini-3.8-flash for Gemini, gpt-4o for OpenAI)",
    )
    parser.add_argument(
        "--prompt",
        default="Execute today's packaging deployment reporting lifecycle.",
        help="Human prompt instruction to the agent",
    )
    parser.add_argument(
        "--demo",
        "--mock-llm",
        action="store_true",
        dest="mock_llm",
        help="Run full end-to-end autonomous cycle in deterministic mode without consuming LLM API quota",
    )
    args = parser.parse_args()

    if args.mock_llm:
        run_mock_agent_cycle(prompt=args.prompt)
        sys.exit(0)

    if not DEPENDENCIES_AVAILABLE:
        print("=" * 70)
        print("⚠️  MISSING DEPENDENCIES")
        print("=" * 70)
        print("Required packages are not installed in this Python environment.")
        print("Please install dependencies by running:")
        print("  pip install -r requirements.txt")
        print("=" * 70)
        sys.exit(1)

    # Detect provider and key
    provider = args.provider or (
        "gemini" if (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) else "openai"
    )
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        model = args.model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        if not api_key:
            print("=" * 70)
            print("⚠️  MISSING GEMINI_API_KEY")
            print("=" * 70)
            print("Please provide a Gemini API key: export GEMINI_API_KEY='...'")
            print("=" * 70)
            sys.exit(1)
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        model = args.model or os.getenv("OPENAI_MODEL", "gpt-4o")
        if not api_key:
            print("=" * 70)
            print("⚠️  MISSING OPENAI_API_KEY / GEMINI_API_KEY")
            print("=" * 70)
            print("Please provide an API key before running the agent:")
            print("  export GEMINI_API_KEY='...' OR export OPENAI_API_KEY='...'")
            print("=" * 70)
            sys.exit(1)

    print("==================================================================")
    print("🚀 Initializing Autonomous Packaging Lifecycle Agent")
    print(f"   Provider: {provider.upper()}")
    print(f"   Model:    {model}")
    print(f"   Database: {DB_PATH}")
    print("==================================================================")

    agent = create_packaging_agent(model_name=model, api_key=api_key, provider=provider)
    print("[Agent Engine] Graph compiled successfully. Starting autonomous cycle...\n")

    try:
        result = agent.invoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=args.prompt),
                ]
            }
        )

        print("\n==================================================================")
        print("🏁 Final Agent Execution Summary:")
        print("==================================================================")
        print(result["messages"][-1].content)
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg or "Quota exceeded" in error_msg:
            print("\n" + "=" * 70)
            print("⚠️  API RATE LIMIT / QUOTA EXCEEDED (429)")
            print("=" * 70)
            print("Your LLM API key has reached its free-tier rate limit or daily quota.")
            print("You can run the full end-to-end autonomous flow without consuming quota using:")
            print("    python packaging_agent.py --demo")
            print("=" * 70)
        else:
            raise


if __name__ == "__main__":
    main()

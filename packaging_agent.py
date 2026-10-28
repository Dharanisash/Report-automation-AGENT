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
from typing import Annotated, Dict, List, Literal, Optional, TypedDict

# =====================================================================
# Imports & Dependency Check
# =====================================================================
try:
    from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI
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

# =====================================================================
# 1. Persistent State Store (SQLite)
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
            "task_id": "SCTASK2444402",
            "ritm_id": "RITM2566659",
            "req_type": "Existing Application",
            "app_name": "MAP STUDIO PRO",
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
) -> str:
    """Persists or updates candidate packaging tasks in the lifecycle database.

    Recipients must be deduplicated before storing.
    """
    # Clean and deduplicate recipient emails
    deduped = sorted(list({r.strip().lower() for r in recipients if r and r.strip()}))
    recipient_str = ";".join(deduped)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO tracked_tasks
            (task_id, ritm_id, app_name, req_type, closed_date, recipients)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, ritm_id, app_name, req_type, closed_date, recipient_str),
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
            SELECT task_id, ritm_id, app_name, req_type, closed_date, recipients,
                   d1_dispatched, d3_dispatched, d7_dispatched
            FROM tracked_tasks
            WHERE is_completed = 0
            """
        )
        rows = cursor.fetchall()
        for row in rows:
            task_id, ritm_id, app_name, req_type, closed_str, rec_str, d1, d3, d7 = row
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
        "MAP STUDIO PRO": {
            "source": preferred_source,
            "target_count": 320,
            "installed": 288,
            "pending": 24,
            "failed": 8,
            "compliance_pct": 90.0,
        },
        "HORSE POWERTRAIN DIAG": {
            "source": "ADT",
            "target_count": 140,
            "installed": 105,
            "pending": 25,
            "failed": 10,
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


def create_packaging_agent(model_name: str = "gpt-4o", api_key: Optional[str] = None):
    """Compiles the autonomous LangGraph agent."""
    init_db()
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        print("[WARNING] OPENAI_API_KEY environment variable is not set.")
        print("          Set it via: export OPENAI_API_KEY='your-key-here'")
        print("          Or create a .env file with OPENAI_API_KEY.\n")
        key = "placeholder-key"

    llm = ChatOpenAI(model=model_name, temperature=0, api_key=key)
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
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4o"),
        help="OpenAI Model name (default: gpt-4o)",
    )
    parser.add_argument(
        "--prompt",
        default="Execute today's packaging deployment reporting lifecycle.",
        help="Human prompt instruction to the agent",
    )
    args = parser.parse_args()

    if not DEPENDENCIES_AVAILABLE:
        print("=" * 70)
        print("⚠️  MISSING DEPENDENCIES")
        print("=" * 70)
        print("Required packages are not installed in this Python environment.")
        print("Please install dependencies by running:")
        print("  pip install -r requirements.txt")
        print("=" * 70)
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("=" * 70)
        print("⚠️  MISSING OPENAI_API_KEY")
        print("=" * 70)
        print("Please provide an OpenAI API key before running the agent:")
        print("  export OPENAI_API_KEY='sk-proj-...'")
        print("  python packaging_agent.py")
        print("=" * 70)
        sys.exit(1)

    print("==================================================================")
    print("🚀 Initializing Autonomous Packaging Lifecycle Agent")
    print(f"   Model: {args.model}")
    print(f"   Database: {DB_PATH}")
    print("==================================================================")

    agent = create_packaging_agent(model_name=args.model, api_key=api_key)
    print("[Agent Engine] Graph compiled successfully. Starting autonomous cycle...\n")

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


if __name__ == "__main__":
    main()

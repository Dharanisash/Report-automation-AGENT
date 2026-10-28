"""Database lifecycle tracking tools for packaging tasks."""

import json
from typing import List

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        func.invoke = lambda args: func(**args)
        return func

from packaging_agent.db import get_pending_milestone_tasks, sync_task_record


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
    return sync_task_record(task_id, ritm_id, app_name, req_type, closed_date, recipients)


@tool
def db_get_pending_milestone_tasks() -> str:
    """Scans the database and calculates which tasks are currently due for D+1, D+3, or D+7 reports

    based on the current date and the task closure date.
    Returns JSON list of due tasks with their required milestone.
    """
    due_items = get_pending_milestone_tasks()
    return json.dumps(due_items)

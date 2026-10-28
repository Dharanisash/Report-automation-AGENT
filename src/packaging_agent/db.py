"""SQLite state management and lifecycle tracking for packaging tasks."""

import sqlite3
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from packaging_agent.config import settings


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes local state database for task lifecycle tracking."""
    path = db_path or settings.db_path
    with sqlite3.connect(path) as conn:
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


def sync_task_record(
    task_id: str,
    ritm_id: str,
    app_name: str,
    req_type: str,
    closed_date: str,
    recipients: List[str],
    db_path: Optional[str] = None,
) -> str:
    """Persists or updates candidate packaging tasks in the lifecycle database.

    Deduplicates email recipients and ignores duplicate task insertions.
    """
    path = db_path or settings.db_path
    # Ensure recipient deduplication and clean formatting
    deduped_recipients = sorted(list({r.strip().lower() for r in recipients if r and r.strip()}))
    recipient_str = ";".join(deduped_recipients)

    with sqlite3.connect(path) as conn:
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


def get_pending_milestone_tasks(
    current_date: Optional[date] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Scans the database and calculates which tasks are due for D+1, D+3, or D+7 reports.

    Based on the current date and the task closure date.
    """
    path = db_path or settings.db_path
    eval_date = current_date or datetime.now(timezone.utc).date()
    due_items = []

    with sqlite3.connect(path) as conn:
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
                # Handle standard ISO YYYY-MM-DD format
                closed_dt = datetime.strptime(closed_str[:10], "%Y-%m-%d").date()

            delta_days = (eval_date - closed_dt).days
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
    return due_items


def update_milestone_status(
    task_id: str,
    milestone: str,
    db_path: Optional[str] = None,
) -> bool:
    """Updates the dispatched status flag for a specific milestone."""
    path = db_path or settings.db_path
    col_map = {"D+1": "d1_dispatched", "D+3": "d3_dispatched", "D+7": "d7_dispatched"}
    col = col_map.get(milestone.upper())
    if not col:
        return False

    is_complete = 1 if milestone.upper() == "D+7" else 0
    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE tracked_tasks SET {col} = 1, is_completed = ? WHERE task_id = ?",
            (is_complete, task_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_task_by_id(task_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single task record by task ID."""
    path = db_path or settings.db_path
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tracked_tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_tracked_tasks(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all tracked task records in the database."""
    path = db_path or settings.db_path
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tracked_tasks ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

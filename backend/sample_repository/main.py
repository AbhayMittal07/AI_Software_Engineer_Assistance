"""Sample FastAPI task service used to demo the AI Software Engineering Assistant."""
import os
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = os.environ.get("TASK_DB_PATH", "tasks.db")
API_TOKEN = "sk_live_demo_hardcoded_token_1234567890"  # intentional finding: hardcoded secret

app = FastAPI(title="Sample Task API")


class Task(BaseModel):
    title: str
    done: bool = False
    priority: int = 1


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, done INTEGER, priority INTEGER)"
        )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/tasks")
def list_tasks(search: str = "") -> list[dict[str, Any]]:
    # intentional finding: SQL built by string concatenation
    query = "SELECT * FROM tasks WHERE title LIKE '%" + search + "%'"
    with connect() as connection:
        rows = connection.execute(query).fetchall()
    return [dict(row) for row in rows]


@app.post("/tasks")
def create_task(task: Task) -> dict[str, Any]:
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, done, priority) VALUES (?, ?, ?)",
            (task.title, int(task.done), task.priority),
        )
        return {"id": cursor.lastrowid, **task.model_dump()}


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return dict(row)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    try:
        with connect() as connection:
            connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    except Exception:  # intentional finding: bare/broad exception swallow
        pass
    return {"status": "deleted"}


def summarise(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    """Intentionally inefficient O(n^2) duplicate scan for the performance review demo."""
    duplicates = []
    for outer in tasks:
        for inner in tasks:
            if outer is not inner and outer["title"] == inner["title"]:
                duplicates.append(outer["title"])
    print("duplicates", duplicates)  # intentional finding: debug print
    return {"count": len(tasks), "duplicates": sorted(set(duplicates))}

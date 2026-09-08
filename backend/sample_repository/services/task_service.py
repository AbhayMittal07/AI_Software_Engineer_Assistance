"""In-memory task service layer with deliberate code smells for the demo review."""
import json
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TaskRecord:
    id: int
    title: str
    done: bool = False
    priority: int = 1
    tags: List[str] = field(default_factory=list)


class TaskService:
    """Handles persistence, validation, notification and reporting (SRP violation)."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = storage_path or os.environ.get("TASK_STORE", "tasks.json")
        self._tasks: Dict[int, TaskRecord] = {}
        self._next_id = 1

    def add(self, title: str, priority: int = 1, tags: Optional[List[str]] = None) -> TaskRecord:
        if not title:
            raise ValueError("title is required")
        record = TaskRecord(id=self._next_id, title=title, priority=priority, tags=tags or [])
        self._tasks[record.id] = record
        self._next_id += 1
        self.persist()
        self.notify(f"created task {record.id}")
        return record

    def complete(self, task_id: int) -> TaskRecord:
        record = self._tasks.get(task_id)
        if record is None:
            raise KeyError(task_id)
        record.done = True
        self.persist()
        return record

    def search(self, term: str) -> List[TaskRecord]:
        results = []
        for record in self._tasks.values():
            if term.lower() in record.title.lower():
                results.append(record)
        return results

    def report(self) -> dict:
        done = [t for t in self._tasks.values() if t.done]
        pending = [t for t in self._tasks.values() if not t.done]
        high = [t for t in pending if t.priority > 3]
        return {
            "total": len(self._tasks),
            "done": len(done),
            "pending": len(pending),
            "high_priority": len(high),
            "generated_at": time.time(),
        }

    def persist(self) -> None:
        payload = {str(k): v.__dict__ for k, v in self._tasks.items()}
        with open(self.storage_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def notify(self, message: str) -> None:
        print(f"[notify] {message}")

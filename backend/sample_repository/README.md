# Sample Task API

A deliberately imperfect FastAPI service bundled with the AI Software Engineering Assistant so
you can immediately try repository analysis, AI review, documentation and diagram generation.

## Run

```bash
pip install fastapi uvicorn
uvicorn main:app --reload
```

## Known (intentional) issues

- Hardcoded API token in `main.py`
- SQL built with string concatenation in `list_tasks`
- Broad exception swallowing in `delete_task`
- `O(n^2)` duplicate scan in `summarise`
- `TaskService` mixes persistence, validation, notification and reporting

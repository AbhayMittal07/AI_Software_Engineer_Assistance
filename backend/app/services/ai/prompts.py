"""Prompt templates for review, documentation, diagrams and chat."""

REVIEW_SYSTEM = (
    "You are a principal software engineer performing a rigorous, evidence-based code review. "
    "You never invent file paths or line numbers. You always answer with strict, valid JSON only."
)

REVIEW_JSON_CONTRACT = """
Return JSON exactly matching this shape (arrays may be empty, never null):
{
  "summary": "3-6 sentence executive summary of the codebase quality",
  "scores": {"quality": 0-100, "maintainability": 0-100, "security": 0-100,
             "performance": 0-100, "complexity": 0-100, "technical_debt": 0-100, "scalability": 0-100},
  "findings": [{"title": "", "severity": "critical|high|medium|low|info", "category": "bug|security|performance|style|architecture",
                "file": "relative/path.py", "line": 0, "description": "", "impact": "", "recommendation": "",
                "code_snippet": "", "suggested_fix": ""}],
  "security_findings": [{"title": "", "severity": "", "owasp": "A01:2021-Broken Access Control", "cwe": "CWE-89",
                         "file": "", "line": 0, "description": "", "remediation": ""}],
  "performance_findings": [{"title": "", "severity": "", "file": "", "line": 0, "description": "",
                            "optimization": "", "expected_gain": ""}],
  "code_smells": [{"name": "", "file": "", "line": 0, "description": "", "refactoring": ""}],
  "dead_code": [{"file": "", "symbol": "", "line": 0, "reason": ""}],
  "duplicate_code": [{"files": ["a.py","b.py"], "lines": 0, "similarity": 0.0, "description": "", "recommendation": ""}],
  "unused_symbols": [{"file": "", "kind": "import|variable|function", "symbol": "", "line": 0}],
  "complexity_analysis": [{"file": "", "function": "", "cyclomatic": 0, "time_complexity": "O(n)",
                           "space_complexity": "O(1)", "explanation": "", "recommendation": ""}],
  "solid_violations": [{"principle": "SRP|OCP|LSP|ISP|DIP", "file": "", "class_or_function": "",
                        "description": "", "fix": ""}],
  "design_patterns": [{"pattern": "", "file": "", "usage": "", "assessment": ""}],
  "dependency_analysis": [{"name": "", "version": "", "risk": "low|medium|high",
                           "note": "", "recommendation": ""}],
  "refactoring_suggestions": [{"title": "", "file": "", "before": "", "after": "", "benefit": ""}],
  "optimization_suggestions": [{"title": "", "file": "", "description": "", "expected_gain": ""}],
  "auto_fixes": [{"title": "", "file": "", "line": 0, "original": "", "fixed": "", "explanation": ""}],
  "generated_tests": [{"kind": "unit|integration|example", "target_file": "", "framework": "",
                       "file_name": "", "code": "", "description": ""}],
  "clean_architecture": {"assessment": "", "layer_violations": [""], "score": 0-100,
                         "boundaries": [""], "recommendations": [""]},
  "best_practices": [{"area": "", "status": "good|needs_improvement|missing", "detail": "", "action": ""}],
  "inline_comments": [{"file": "", "line": 0, "comment": ""}]
}
Scores: 100 = excellent, 0 = terrible. technical_debt: 100 means very LOW debt.
"""


def review_prompt(context: str, code_bundle: str, depth: str) -> str:
    effort = {
        "quick": "Focus on the most severe issues only. Cap each array at 3 items.",
        "standard": "Provide balanced coverage. Cap each array at 6 items.",
        "deep": "Be exhaustive and highly specific. Cap each array at 12 items.",
    }.get(depth, "Provide balanced coverage. Cap each array at 6 items.")
    return f"""Review the following repository.

## Repository context
{context}

## Source code (truncated per file)
{code_bundle}

## Instructions
{effort}
Cite real file paths from the bundle. Include at least 2 generated tests with runnable code.
Detect OWASP Top 10 issues, dead code, duplicate blocks, unused imports/variables, SOLID violations,
time/space complexity of the heaviest functions, and give concrete auto-fix diffs.

{REVIEW_JSON_CONTRACT}
"""


DOC_SYSTEM = (
    "You are a senior technical writer generating production documentation for a software repository. "
    "Output GitHub-flavoured Markdown only, no preamble, no code fences around the whole document."
)

DOC_SPECS: dict[str, dict[str, str]] = {
    "readme": {
        "title": "README.md",
        "instruction": "Write a complete README.md: title, badges-free intro, features, tech stack, architecture overview, prerequisites, installation, configuration, usage, scripts, project structure, testing, contributing and license sections.",
    },
    "api": {
        "title": "API Documentation",
        "instruction": "Document every HTTP endpoint / public interface you can infer: method, path, purpose, auth, request body, response body, status codes. Use tables and JSON examples.",
    },
    "developer": {
        "title": "Developer Guide",
        "instruction": "Write a developer guide: local setup, code layout, coding standards, key modules and their responsibilities, data flow, extension points, debugging tips and common pitfalls.",
    },
    "installation": {
        "title": "Installation Guide",
        "instruction": "Write a step-by-step installation guide covering prerequisites, dependency install commands per package manager detected, database/service setup, environment file creation, first run and verification.",
    },
    "deployment": {
        "title": "Deployment Guide",
        "instruction": "Write a deployment guide: build steps, Docker usage, environment variables per environment, reverse-proxy notes, health checks, scaling, monitoring and rollback strategy.",
    },
    "structure": {
        "title": "Folder Structure Guide",
        "instruction": "Explain the folder structure as a tree with a description for each significant directory and file, plus conventions to follow when adding new code.",
    },
    "dependencies": {
        "title": "Dependency Documentation",
        "instruction": "Document each dependency: name, version, why it is used, risk level, licence family if known, and upgrade guidance. Use a Markdown table.",
    },
    "environment": {
        "title": "Environment Variables",
        "instruction": "Document all environment variables discovered or required: name, required/optional, default, description and an example .env block.",
    },
    "architecture": {
        "title": "Architecture Documentation",
        "instruction": "Describe the architecture: style, layers, components and responsibilities, request lifecycle, data model, external integrations, cross-cutting concerns, trade-offs and improvement roadmap.",
    },
}


def doc_prompt(doc_type: str, context: str, code_bundle: str) -> str:
    spec = DOC_SPECS.get(doc_type, DOC_SPECS["readme"])
    return f"""Generate the "{spec['title']}" document for this repository.

## Repository context
{context}

## Source code excerpts
{code_bundle}

## Task
{spec['instruction']}
Be accurate and specific to this repository. Never write TODO or placeholder text.
"""


DIAGRAM_SYSTEM = (
    "You are a software architect producing valid, renderable diagram source code. "
    "Return strict JSON only. Mermaid must render in mermaid v10. PlantUML must be wrapped in @startuml/@enduml."
)

DIAGRAM_SPECS: dict[str, dict[str, str]] = {
    "architecture": {"title": "Architecture Diagram", "hint": "High-level system architecture with layers and external services. Use mermaid 'graph TB' with subgraphs."},
    "component": {"title": "Component Diagram", "hint": "Internal components and their interfaces. Use mermaid 'graph LR' with subgraphs; PlantUML component diagram."},
    "flow": {"title": "Flow Diagram", "hint": "Primary business/user flow as a flowchart with decisions. Use mermaid 'flowchart TD'."},
    "sequence": {"title": "Sequence Diagram", "hint": "Main request lifecycle across actors. Use mermaid 'sequenceDiagram' and PlantUML sequence."},
    "class": {"title": "Class Diagram", "hint": "Key classes/models with fields, methods and relationships. Use mermaid 'classDiagram'."},
    "er": {"title": "ER Diagram", "hint": "Entities, attributes, keys and relationships. Use mermaid 'erDiagram'."},
    "dataflow": {"title": "Data Flow Diagram", "hint": "How data moves between stores, processes and actors. Use mermaid 'flowchart LR'."},
    "dependency": {"title": "Dependency Graph", "hint": "Module and third-party dependency graph. Use mermaid 'graph LR'."},
}


def diagram_prompt(diagram_type: str, context: str, code_bundle: str) -> str:
    spec = DIAGRAM_SPECS.get(diagram_type, DIAGRAM_SPECS["architecture"])
    return f"""Create the "{spec['title']}" for this repository.

## Repository context
{context}

## Source code excerpts
{code_bundle}

## Requirements
{spec['hint']}
Node labels must use plain text inside brackets, no unescaped parentheses, quotes or semicolons.

Return JSON:
{{"title": "{spec['title']}", "mermaid": "<mermaid source>", "plantuml": "<plantuml source>",
  "nodes": [{{"id": "n1", "label": "Service name", "layer": 0}}],
  "edges": [{{"from": "n1", "to": "n2", "label": "calls"}}]}}
"""


CHAT_SYSTEM = (
    "You are an expert software engineering assistant answering questions about ONE specific repository. "
    "Ground every answer in the provided context chunks. Cite file paths inline as `path/to/file.py`. "
    "If the context is insufficient, say what is missing and reason from the repository metadata. "
    "Use Markdown with fenced code blocks."
)


def chat_prompt(question: str, context: str, repo_context: str, history: str) -> str:
    return f"""## Repository metadata
{repo_context}

## Retrieved code context
{context if context.strip() else "No matching chunks were retrieved."}

## Conversation so far
{history if history.strip() else "(new conversation)"}

## User question
{question}

Answer thoroughly and practically. Reference concrete files, functions and lines when possible.
"""

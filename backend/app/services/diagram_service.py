"""Architecture diagram generation: Mermaid, PlantUML and Draw.io XML."""
from __future__ import annotations

import asyncio
import html
import re
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.models.analysis import Diagram
from app.models.repository import Repository
from app.repositories.analysis_repository import DiagramRepository
from app.services.ai.factory import get_ai_provider
from app.services.ai.prompts import DIAGRAM_SPECS, DIAGRAM_SYSTEM, diagram_prompt
from app.services.code_analyzer import code_analyzer

logger = get_logger(__name__)

DEFAULT_DIAGRAM_TYPES = list(DIAGRAM_SPECS.keys()) + ["structure"]
ALL_SPECS = {**DIAGRAM_SPECS, "structure": {"title": "Repository Structure Diagram", "hint": ""}}


def _safe_label(text: str, limit: int = 42) -> str:
    cleaned = re.sub(r"[\"'`\[\]{}()<>|;]", " ", str(text)).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:limit] or "node"


def _node_id(index: int) -> str:
    return f"n{index}"


def drawio_xml(title: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    """Builds an editable draw.io (mxGraph) document."""
    cells: list[str] = []
    positions: dict[str, tuple[int, int]] = {}
    per_row = 4
    for index, node in enumerate(nodes):
        col, row = index % per_row, index // per_row
        x, y = 60 + col * 220, 80 + row * 140
        positions[node["id"]] = (x, y)
        cells.append(
            f'<mxCell id="{html.escape(node["id"])}" value="{html.escape(_safe_label(node["label"], 60))}" '
            'style="rounded=0;whiteSpace=wrap;html=1;fillColor=#0F0F0F;strokeColor=#00E5FF;fontColor=#F4F4F5;" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="180" height="60" as="geometry"/></mxCell>'
        )
    for index, edge in enumerate(edges):
        source, target = edge.get("from"), edge.get("to")
        if source not in positions or target not in positions:
            continue
        cells.append(
            f'<mxCell id="e{index}" value="{html.escape(_safe_label(edge.get("label", ""), 30))}" '
            'style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#A1A1AA;fontColor=#A1A1AA;" '
            f'edge="1" parent="1" source="{html.escape(source)}" target="{html.escape(target)}">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
    body = "".join(cells)
    return (
        f'<mxfile host="ai-swe-assistant" modified="" agent="AI Software Engineering Assistant" version="21.0.0">'
        f'<diagram id="{html.escape(title.replace(" ", "-").lower())}" name="{html.escape(title)}">'
        f'<mxGraphModel dx="1100" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
        f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="826" math="0" shadow="0">'
        f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram></mxfile>'
    )


def mermaid_to_graph(mermaid: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extracts nodes/edges from mermaid flow syntax so draw.io stays in sync."""
    nodes: dict[str, str] = {}
    edges: list[dict[str, Any]] = []
    for match in re.finditer(r"(\w+)\s*[\[\(\{]+([^\]\)\}]+)[\]\)\}]+", mermaid):
        nodes.setdefault(match.group(1), match.group(2))
    for match in re.finditer(r"(\w+)\s*-{1,2}[>x-]*\|?([^|>\n]*)\|?>?\s*(\w+)", mermaid):
        source, label, target = match.group(1), match.group(2).strip(), match.group(3)
        if source in nodes or target in nodes:
            nodes.setdefault(source, source)
            nodes.setdefault(target, target)
            edges.append({"from": source, "to": target, "label": label})
    return ([{"id": key, "label": value} for key, value in nodes.items()], edges)


def structure_diagram(repo: Repository) -> tuple[str, str, list[dict], list[dict]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    lines = ["graph TD"]
    counter = {"i": 0}

    def walk(node: dict[str, Any], parent: str | None, depth: int) -> None:
        if depth > 3 or counter["i"] > 45:
            return
        for child in (node.get("children") or [])[:10]:
            if child.get("type") == "info":
                continue
            counter["i"] += 1
            node_id = _node_id(counter["i"])
            label = _safe_label(child.get("name", "?"))
            shape = f'{node_id}["{label}/"]' if child.get("type") == "dir" else f'{node_id}("{label}")'
            lines.append(f"    {shape}")
            nodes.append({"id": node_id, "label": label})
            if parent:
                lines.append(f"    {parent} --> {node_id}")
                edges.append({"from": parent, "to": node_id, "label": ""})
            if child.get("type") == "dir":
                walk(child, node_id, depth + 1)

    root_id = "n0"
    root_label = _safe_label(repo.name)
    lines.append(f'    {root_id}["{root_label}"]')
    nodes.append({"id": root_id, "label": root_label})
    walk(repo.file_tree or {}, root_id, 0)
    mermaid = "\n".join(lines)
    plant_lines = ["@startuml", "skinparam backgroundColor #0F0F0F", "skinparam defaultFontColor #F4F4F5"]
    for node in nodes:
        plant_lines.append(f'folder "{node["label"]}" as {node["id"]}')
    for edge in edges:
        plant_lines.append(f'{edge["from"]} --> {edge["to"]}')
    plant_lines.append("@enduml")
    return mermaid, "\n".join(plant_lines), nodes, edges


def fallback_diagram(diagram_type: str, repo: Repository) -> tuple[str, str, list[dict], list[dict]]:
    if diagram_type == "structure":
        return structure_diagram(repo)

    language = _safe_label(repo.primary_language)
    framework = _safe_label(repo.framework)
    deps = [_safe_label(d.get("name", ""), 24) for d in (repo.dependencies or [])[:6]]
    entry = _safe_label((repo.entrypoints or ["entrypoint"])[0], 30)

    if diagram_type == "er":
        mermaid = (
            "erDiagram\n"
            "    REPOSITORY ||--o{ REVIEW : has\n"
            "    REPOSITORY ||--o{ DOCUMENT : generates\n"
            "    REPOSITORY ||--o{ DIAGRAM : generates\n"
            "    REVIEW ||--o{ FINDING : contains\n"
            "    REPOSITORY {\n        int id\n        string name\n        string language\n    }\n"
            "    REVIEW {\n        int id\n        float quality_score\n        string status\n    }\n"
            "    FINDING {\n        string severity\n        string file\n    }\n"
        )
        plant = "@startuml\nentity REPOSITORY\nentity REVIEW\nentity FINDING\nREPOSITORY ||--o{ REVIEW\nREVIEW ||--o{ FINDING\n@enduml"
        nodes = [{"id": "REPOSITORY", "label": "REPOSITORY"}, {"id": "REVIEW", "label": "REVIEW"}, {"id": "FINDING", "label": "FINDING"}]
        edges = [{"from": "REPOSITORY", "to": "REVIEW", "label": "1..n"}, {"from": "REVIEW", "to": "FINDING", "label": "1..n"}]
        return mermaid, plant, nodes, edges

    if diagram_type == "sequence":
        mermaid = (
            "sequenceDiagram\n    actor User\n    participant UI as Client\n"
            f"    participant App as {framework} App\n    participant Data as Storage\n"
            "    User->>UI: interact\n    UI->>App: request\n    App->>Data: query\n"
            "    Data-->>App: rows\n    App-->>UI: response\n    UI-->>User: render\n"
        )
        plant = f"@startuml\nactor User\nUser -> Client: interact\nClient -> App: request\nApp -> Storage: query\nStorage --> App: rows\nApp --> Client: response\n@enduml"
        nodes = [{"id": "User", "label": "User"}, {"id": "Client", "label": "Client"}, {"id": "App", "label": f"{framework} App"}, {"id": "Storage", "label": "Storage"}]
        edges = [{"from": "User", "to": "Client", "label": "interact"}, {"from": "Client", "to": "App", "label": "request"}, {"from": "App", "to": "Storage", "label": "query"}]
        return mermaid, plant, nodes, edges

    if diagram_type == "class":
        mermaid = (
            "classDiagram\n"
            f"    class {re.sub(r'[^A-Za-z]', '', repo.name) or 'Application'} {{\n"
            "        +run()\n        +configure()\n    }\n"
            "    class Service {\n        +execute()\n    }\n"
            "    class Repository {\n        +find()\n        +save()\n    }\n"
            f"    {re.sub(r'[^A-Za-z]', '', repo.name) or 'Application'} --> Service\n"
            "    Service --> Repository\n"
        )
        plant = "@startuml\nclass Application\nclass Service\nclass Repository\nApplication --> Service\nService --> Repository\n@enduml"
        nodes = [{"id": "Application", "label": "Application"}, {"id": "Service", "label": "Service"}, {"id": "Repository", "label": "Repository"}]
        edges = [{"from": "Application", "to": "Service", "label": "uses"}, {"from": "Service", "to": "Repository", "label": "uses"}]
        return mermaid, plant, nodes, edges

    if diagram_type == "dependency":
        lines = ["graph LR", f'    app["{_safe_label(repo.name)}"]']
        nodes = [{"id": "app", "label": _safe_label(repo.name)}]
        edges = []
        for index, dep in enumerate(deps, start=1):
            node_id = f"d{index}"
            lines.append(f'    {node_id}["{dep}"]')
            lines.append(f"    app --> {node_id}")
            nodes.append({"id": node_id, "label": dep})
            edges.append({"from": "app", "to": node_id, "label": ""})
        plant = "@startuml\n" + "\n".join(f'component "{n["label"]}" as {n["id"]}' for n in nodes) + "\n" + "\n".join(f'{e["from"]} --> {e["to"]}' for e in edges) + "\n@enduml"
        return "\n".join(lines), plant, nodes, edges

    direction = "LR" if diagram_type in {"component", "dataflow"} else "TB"
    mermaid = (
        f"graph {direction}\n"
        f'    subgraph Client\n        ui["User Interface"]\n    end\n'
        f'    subgraph Application\n        entry["{entry}"]\n        core["{framework} Core"]\n        svc["Service Layer"]\n    end\n'
        f'    subgraph Infrastructure\n        store["Data Store"]\n        ext["External APIs"]\n    end\n'
        "    ui --> entry\n    entry --> core\n    core --> svc\n    svc --> store\n    svc --> ext\n"
    )
    nodes = [
        {"id": "ui", "label": "User Interface"}, {"id": "entry", "label": entry},
        {"id": "core", "label": f"{framework} Core"}, {"id": "svc", "label": "Service Layer"},
        {"id": "store", "label": "Data Store"}, {"id": "ext", "label": "External APIs"},
    ]
    edges = [
        {"from": "ui", "to": "entry", "label": "requests"}, {"from": "entry", "to": "core", "label": "routes"},
        {"from": "core", "to": "svc", "label": "delegates"}, {"from": "svc", "to": "store", "label": "persists"},
        {"from": "svc", "to": "ext", "label": "calls"},
    ]
    plant = (
        "@startuml\nskinparam componentStyle rectangle\n"
        + "\n".join(f'component "{n["label"]}" as {n["id"]}' for n in nodes)
        + "\n" + "\n".join(f'{e["from"]} --> {e["to"]} : {e["label"]}' for e in edges)
        + f"\nnote right of core : {language} / {framework}\n@enduml"
    )
    return mermaid, plant, nodes, edges


class DiagramService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.diagrams = DiagramRepository(session)

    async def generate(
        self, repo: Repository, diagram_types: Sequence[str] | None = None, regenerate: bool = True
    ) -> list[Diagram]:
        types = [t for t in (diagram_types or DEFAULT_DIAGRAM_TYPES) if t in ALL_SPECS] or DEFAULT_DIAGRAM_TYPES
        provider = get_ai_provider()
        root = Path(repo.storage_path)
        context, bundle = "", ""
        if root.exists():
            analysis = await asyncio.to_thread(code_analyzer.analyze, root)
            context = analysis.as_context()
            bundle = await asyncio.to_thread(code_analyzer.select_code_bundle, root, analysis, 8)

        results: list[Diagram] = []
        for diagram_type in types:
            existing = await self.diagrams.get_by_type(repo.id, diagram_type)
            if existing and not regenerate:
                results.append(existing)
                continue
            title = ALL_SPECS[diagram_type]["title"]
            mermaid = plant = ""
            nodes: list[dict[str, Any]] = []
            edges: list[dict[str, Any]] = []
            ai_powered = False
            if provider.available and bundle and diagram_type != "structure":
                try:
                    payload = await provider.generate_json(
                        diagram_prompt(diagram_type, context, bundle), system=DIAGRAM_SYSTEM, temperature=0.3
                    )
                    mermaid = str(payload.get("mermaid") or "").strip()
                    plant = str(payload.get("plantuml") or "").strip()
                    title = str(payload.get("title") or title)[:200]
                    nodes = [n for n in (payload.get("nodes") or []) if isinstance(n, dict) and n.get("id")]
                    edges = [e for e in (payload.get("edges") or []) if isinstance(e, dict)]
                    ai_powered = bool(mermaid)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Diagram generation failed (%s): %s", diagram_type, str(exc)[:200])
            if not mermaid:
                mermaid, plant, nodes, edges = fallback_diagram(diagram_type, repo)
                ai_powered = False
            if not plant:
                plant = "@startuml\n' generated from mermaid source\n@enduml"
            if not nodes:
                nodes, edges = mermaid_to_graph(mermaid)
            xml = drawio_xml(title, nodes or [{"id": "n0", "label": repo.name}], edges)

            if existing:
                existing.title, existing.mermaid, existing.plantuml = title, mermaid, plant
                existing.drawio_xml, existing.ai_powered = xml, ai_powered
                results.append(existing)
            else:
                results.append(
                    await self.diagrams.create(
                        repository_id=repo.id, diagram_type=diagram_type, title=title,
                        mermaid=mermaid, plantuml=plant, drawio_xml=xml, ai_powered=ai_powered,
                    )
                )
        await self.session.commit()
        return results

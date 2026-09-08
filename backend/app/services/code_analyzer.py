"""Static code intelligence: language, framework, architecture and metrics detection."""
from __future__ import annotations

import ast
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

EXTENSION_LANGUAGE = {
    ".py": "Python", ".java": "Java", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".h": "C/C++ Header", ".c": "C", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go", ".rb": "Ruby",
    ".rs": "Rust", ".php": "PHP", ".cs": "C#", ".kt": "Kotlin", ".swift": "Swift", ".scala": "Scala",
    ".dart": "Dart", ".sh": "Shell", ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "CSS",
    ".vue": "Vue", ".svelte": "Svelte", ".md": "Markdown", ".yml": "YAML", ".yaml": "YAML",
    ".json": "JSON", ".xml": "XML", ".toml": "TOML",
}

CODE_LANGUAGES = {
    "Python", "Java", "C++", "C", "JavaScript", "TypeScript", "Go", "Ruby", "Rust", "PHP",
    "C#", "Kotlin", "Swift", "Scala", "Dart", "Vue", "Svelte",
}

IGNORED_DIRS = {
    ".git", ".svn", "node_modules", "__pycache__", ".venv", "venv", "env", "dist", "build",
    ".next", ".nuxt", "target", "out", "bin", "obj", ".idea", ".vscode", ".pytest_cache",
    ".mypy_cache", "coverage", ".gradle", "vendor", ".terraform", "__MACOSX", ".DS_Store",
    "site-packages", ".cache", ".turbo", "logs",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf", ".zip", ".tar", ".gz", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".class", ".jar", ".war", ".pyc", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mp3", ".wav", ".bin", ".db", ".sqlite", ".lock",
}

FRAMEWORK_SIGNATURES: list[tuple[str, str, str]] = [
    # (dependency/marker, framework, project type)
    ("fastapi", "FastAPI", "REST API Service"),
    ("django", "Django", "Web Application"),
    ("flask", "Flask", "Web Application"),
    ("next", "Next.js", "Full-stack Web Application"),
    ("nuxt", "Nuxt", "Full-stack Web Application"),
    ("react", "React", "Single Page Application"),
    ("vue", "Vue", "Single Page Application"),
    ("@angular/core", "Angular", "Single Page Application"),
    ("svelte", "Svelte", "Single Page Application"),
    ("express", "Express", "REST API Service"),
    ("nestjs", "NestJS", "REST API Service"),
    ("@nestjs/core", "NestJS", "REST API Service"),
    ("spring-boot", "Spring Boot", "REST API Service"),
    ("springframework", "Spring", "Web Application"),
    ("gin-gonic", "Gin", "REST API Service"),
    ("fiber", "Fiber", "REST API Service"),
    ("torch", "PyTorch", "Machine Learning Project"),
    ("tensorflow", "TensorFlow", "Machine Learning Project"),
    ("scikit-learn", "scikit-learn", "Machine Learning Project"),
    ("pandas", "Data Science Stack", "Data Analysis Project"),
    ("streamlit", "Streamlit", "Data Application"),
]

ENV_VAR_PATTERN = re.compile(r"(?:os\.environ(?:\.get)?\(?[\['\"]+|process\.env\.|getenv\(['\"])([A-Z][A-Z0-9_]{2,})")
SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"), "Hardcoded credential"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key id"),
    (re.compile(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Private key committed"),
]
RISKY_PATTERNS = [
    (re.compile(r"\beval\s*\("), "high", "Use of eval() enables arbitrary code execution"),
    (re.compile(r"\bexec\s*\("), "high", "Use of exec() enables arbitrary code execution"),
    (re.compile(r"subprocess\.[a-z]+\([^)]*shell\s*=\s*True"), "high", "Shell injection risk via shell=True"),
    (re.compile(r"pickle\.loads?\("), "medium", "Untrusted pickle deserialisation"),
    (re.compile(r"verify\s*=\s*False"), "medium", "TLS verification disabled"),
    (re.compile(r"(?i)select\s+.*\s+from\s+.*['\"]?\s*\+\s*"), "high", "Possible SQL injection via string concatenation"),
    (re.compile(r"innerHTML\s*="), "medium", "Potential XSS via innerHTML assignment"),
    (re.compile(r"dangerouslySetInnerHTML"), "medium", "Potential XSS via dangerouslySetInnerHTML"),
    (re.compile(r"document\.write\("), "low", "document.write can enable XSS"),
    (re.compile(r"(?i)cors.*allow_origins\s*=\s*\[\s*['\"]\*['\"]"), "medium", "Wildcard CORS origin"),
]


@dataclass
class FileInfo:
    path: str
    language: str
    lines: int
    size: int
    score: float = 0.0


@dataclass
class AnalysisResult:
    primary_language: str = "Unknown"
    languages: Dict[str, int] = field(default_factory=dict)
    framework: str = "Unknown"
    architecture: str = "Unknown"
    project_type: str = "Unknown"
    package_manager: str = "Unknown"
    build_tool: str = "Unknown"
    file_count: int = 0
    total_lines: int = 0
    size_bytes: int = 0
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    entrypoints: List[str] = field(default_factory=list)
    file_tree: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    files: List[FileInfo] = field(default_factory=list)
    static_findings: List[Dict[str, Any]] = field(default_factory=list)
    env_vars: List[str] = field(default_factory=list)
    duplicates: List[Dict[str, Any]] = field(default_factory=list)

    def as_context(self) -> str:
        deps = ", ".join(f"{d['name']}{('@' + d['version']) if d.get('version') else ''}" for d in self.dependencies[:35])
        top_files = ", ".join(f.path for f in self.files[:25])
        return (
            f"Primary language: {self.primary_language}\n"
            f"Language breakdown: {json.dumps(self.languages)}\n"
            f"Framework: {self.framework}\nArchitecture: {self.architecture}\n"
            f"Project type: {self.project_type}\nPackage manager: {self.package_manager}\n"
            f"Build tool: {self.build_tool}\n"
            f"Files: {self.file_count}, Lines of code: {self.total_lines}, Size: {self.size_bytes} bytes\n"
            f"Entrypoints: {', '.join(self.entrypoints) or 'not detected'}\n"
            f"Dependencies: {deps or 'none detected'}\n"
            f"Environment variables referenced: {', '.join(self.env_vars[:25]) or 'none'}\n"
            f"Key files: {top_files}\n"
            f"Static metrics: {json.dumps(self.metrics)}"
        )


def _is_ignored(path: Path, root: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.relative_to(root).parts)


def _read_text(path: Path, limit: int = 400_000) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _importance(rel_path: str, language: str, lines: int) -> float:
    score = 0.0
    lowered = rel_path.lower()
    name = lowered.rsplit("/", 1)[-1]
    if language in CODE_LANGUAGES:
        score += 30
    if any(k in name for k in ("main.", "app.", "index.", "server.", "__init__")):
        score += 25
    if any(k in lowered for k in ("service", "controller", "router", "api", "model", "repository", "core", "auth")):
        score += 20
    if any(k in lowered for k in ("test", "spec", "mock", "fixture", "migration", "__snapshots__")):
        score -= 25
    if any(k in lowered for k in ("config", "settings", "schema")):
        score += 12
    depth = lowered.count("/")
    score -= depth * 2
    score += min(lines / 25.0, 20)
    return score


def build_tree(root: Path, max_entries: int = 1500) -> Dict[str, Any]:
    counter = {"n": 0}

    def walk(directory: Path) -> Dict[str, Any]:
        node: Dict[str, Any] = {"name": directory.name or directory.as_posix(), "type": "dir", "children": []}
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return node
        for entry in entries:
            if counter["n"] >= max_entries:
                node["children"].append({"name": "... truncated", "type": "info"})
                break
            if entry.name in IGNORED_DIRS or entry.name.startswith(".git"):
                continue
            counter["n"] += 1
            if entry.is_dir():
                node["children"].append(walk(entry))
            else:
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                node["children"].append(
                    {
                        "name": entry.name,
                        "type": "file",
                        "size": size,
                        "path": entry.relative_to(root).as_posix(),
                        "language": EXTENSION_LANGUAGE.get(entry.suffix.lower(), "Other"),
                    }
                )
        return node

    tree = walk(root)
    tree["name"] = root.name
    return tree


def _parse_package_json(content: str) -> tuple[List[Dict[str, Any]], List[str]]:
    deps: List[Dict[str, Any]] = []
    scripts: List[str] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return deps, scripts
    for section, kind in (("dependencies", "runtime"), ("devDependencies", "dev")):
        for name, version in (data.get(section) or {}).items():
            deps.append({"name": name, "version": str(version), "kind": kind, "ecosystem": "npm"})
    scripts = list((data.get("scripts") or {}).keys())
    return deps, scripts


def _parse_requirements(content: str) -> List[Dict[str, Any]]:
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        match = re.match(r"^([A-Za-z0-9_.\-\[\]]+)\s*([=><~!]+)?\s*([0-9A-Za-z_.\-*]+)?", line)
        if match:
            deps.append(
                {
                    "name": match.group(1),
                    "version": (match.group(3) or "").strip(),
                    "kind": "runtime",
                    "ecosystem": "pypi",
                }
            )
    return deps


def _parse_pyproject(content: str) -> List[Dict[str, Any]]:
    deps = []
    for match in re.finditer(r'^\s*"?([A-Za-z0-9_.\-]+)"?\s*(?:=\s*"([^"]+)")?', content, re.MULTILINE):
        name = match.group(1)
        if name.lower() in {"name", "version", "description", "requires-python", "authors", "readme", "license"}:
            continue
        deps.append({"name": name, "version": match.group(2) or "", "kind": "runtime", "ecosystem": "pypi"})
    return deps[:60]


def _parse_pom(content: str) -> List[Dict[str, Any]]:
    deps = []
    for match in re.finditer(
        r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>\s*(?:<version>([^<]+)</version>)?",
        content,
        re.DOTALL,
    ):
        deps.append(
            {
                "name": f"{match.group(1)}:{match.group(2)}",
                "version": (match.group(3) or "").strip(),
                "kind": "runtime",
                "ecosystem": "maven",
            }
        )
    return deps


def _parse_gomod(content: str) -> List[Dict[str, Any]]:
    deps = []
    for match in re.finditer(r"^\s*([\w./\-]+)\s+(v[\w.\-+]+)", content, re.MULTILINE):
        deps.append({"name": match.group(1), "version": match.group(2), "kind": "runtime", "ecosystem": "go"})
    return deps


def _python_static_checks(rel_path: str, content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return findings
    imported: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[(alias.asname or alias.name).split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    imported[alias.asname or alias.name] = node.lineno
    body_source = content
    for name, lineno in imported.items():
        occurrences = len(re.findall(rf"\b{re.escape(name)}\b", body_source))
        if occurrences <= 1:
            findings.append(
                {
                    "kind": "import",
                    "symbol": name,
                    "file": rel_path,
                    "line": lineno,
                    "reason": "Imported but never referenced",
                }
            )
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1 + sum(
                1
                for child in ast.walk(node)
                if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.BoolOp, ast.IfExp, ast.ExceptHandler))
            )
            length = (getattr(node, "end_lineno", node.lineno) or node.lineno) - node.lineno
            if complexity >= 10 or length > 80:
                findings.append(
                    {
                        "kind": "complexity",
                        "symbol": node.name,
                        "file": rel_path,
                        "line": node.lineno,
                        "cyclomatic": complexity,
                        "length": length,
                        "reason": f"Function '{node.name}' has cyclomatic complexity {complexity} over {length} lines",
                    }
                )
        if isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if len(methods) > 20:
                findings.append(
                    {
                        "kind": "srp",
                        "symbol": node.name,
                        "file": rel_path,
                        "line": node.lineno,
                        "reason": f"Class '{node.name}' exposes {len(methods)} methods (God Object / SRP violation)",
                    }
                )
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(
                {
                    "kind": "smell",
                    "symbol": "bare except",
                    "file": rel_path,
                    "line": node.lineno,
                    "reason": "Bare except swallows all exceptions including KeyboardInterrupt",
                }
            )
    return findings


def _generic_static_checks(rel_path: str, content: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    lines = content.splitlines()
    for index, line in enumerate(lines, start=1):
        if len(line) > 200:
            findings.append({"kind": "smell", "symbol": "long line", "file": rel_path, "line": index,
                             "reason": f"Line exceeds 200 characters ({len(line)})"})
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append({"kind": "secret", "symbol": label, "file": rel_path, "line": index,
                                 "severity": "critical", "reason": f"{label} detected in source"})
        for pattern, severity, message in RISKY_PATTERNS:
            if pattern.search(line):
                findings.append({"kind": "security", "symbol": message, "file": rel_path, "line": index,
                                 "severity": severity, "reason": message})
        if re.search(r"(?i)\b(todo|fixme|hack|xxx)\b", line):
            findings.append({"kind": "debt", "symbol": "TODO marker", "file": rel_path, "line": index,
                             "reason": line.strip()[:160]})
        if re.search(r"^\s*(console\.log|print)\s*\(", line) and "test" not in rel_path.lower():
            findings.append({"kind": "smell", "symbol": "debug output", "file": rel_path, "line": index,
                             "reason": "Debug logging statement left in production code"})
    if len(lines) > 600:
        findings.append({"kind": "smell", "symbol": "large file", "file": rel_path, "line": 1,
                         "reason": f"File has {len(lines)} lines; consider splitting responsibilities"})
    return findings


def _detect_duplicates(samples: dict[str, str]) -> List[Dict[str, Any]]:
    """Detect duplicated 8-line normalised blocks across files."""
    block_map: dict[int, list[tuple[str, int]]] = {}
    for path, content in samples.items():
        lines = [re.sub(r"\s+", " ", line).strip() for line in content.splitlines()]
        lines = [line for line in lines if len(line) > 12 and not line.startswith(("#", "//", "*", "/*"))]
        for index in range(0, max(len(lines) - 8, 0), 4):
            block = " ".join(lines[index : index + 8])
            if len(block) < 120:
                continue
            block_map.setdefault(hash(block), []).append((path, index + 1))
    duplicates: List[Dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for locations in block_map.values():
        files = sorted({loc[0] for loc in locations})
        if len(locations) < 2 or len(files) < 1:
            continue
        key = tuple(files)
        if key in seen or len(duplicates) >= 12:
            continue
        seen.add(key)
        duplicates.append(
            {
                "files": files,
                "lines": 8,
                "similarity": 1.0,
                "occurrences": len(locations),
                "description": f"Identical 8-line block repeated {len(locations)} times",
                "recommendation": "Extract the duplicated block into a shared helper or base class",
            }
        )
    return duplicates


def detect_architecture(paths: List[str], framework: str) -> str:
    lowered = [p.lower() for p in paths]
    joined = " ".join(lowered)
    signals: list[str] = []
    if any("/domain/" in p or p.startswith("domain/") for p in lowered) and "usecase" in joined:
        signals.append("Clean Architecture")
    if all(token in joined for token in ("service", "repositor")):
        signals.append("Layered (Service + Repository)")
    if "controller" in joined and "model" in joined and ("view" in joined or "template" in joined):
        signals.append("MVC")
    if joined.count("services/") > 3 and ("docker-compose" in joined or "kubernetes" in joined):
        signals.append("Microservices")
    if "hooks/" in joined and "components/" in joined:
        signals.append("Component-based SPA")
    if "handler" in joined and "lambda" in joined:
        signals.append("Serverless")
    if "middleware" in joined and "router" in joined:
        signals.append("Modular Monolith")
    if not signals:
        if framework in {"React", "Vue", "Angular", "Svelte", "Next.js"}:
            return "Component-based SPA"
        return "Monolithic / Script-oriented"
    return " + ".join(dict.fromkeys(signals[:2]))


class CodeAnalyzer:
    """Walks an extracted repository and derives structural intelligence."""

    def analyze(self, root: Path) -> AnalysisResult:
        result = AnalysisResult()
        files: List[FileInfo] = []
        language_lines: Counter[str] = Counter()
        total_size = 0
        total_lines = 0
        marker_files: dict[str, str] = {}
        env_vars: set[str] = set()
        static_findings: List[Dict[str, Any]] = []
        samples: dict[str, str] = {}

        all_paths: List[str] = []
        for path in root.rglob("*"):
            if not path.is_file() or _is_ignored(path, root):
                continue
            rel = path.relative_to(root).as_posix()
            all_paths.append(rel)
            suffix = path.suffix.lower()
            try:
                size = path.stat().st_size
            except OSError:
                continue
            total_size += size
            if suffix in BINARY_EXTENSIONS or size > 2_000_000:
                continue
            language = EXTENSION_LANGUAGE.get(suffix, "Other")
            content = _read_text(path)
            if not content:
                continue
            line_count = content.count("\n") + 1
            total_lines += line_count
            if language in CODE_LANGUAGES:
                language_lines[language] += line_count
            files.append(
                FileInfo(path=rel, language=language, lines=line_count, size=size,
                         score=_importance(rel, language, line_count))
            )
            base_name = path.name.lower()
            if base_name in {
                "package.json", "requirements.txt", "pyproject.toml", "pom.xml", "build.gradle",
                "build.gradle.kts", "go.mod", "cargo.toml", "cmakelists.txt", "makefile", "gemfile",
                "composer.json", "dockerfile", "docker-compose.yml", "docker-compose.yaml",
                "pipfile", "setup.py", "yarn.lock", "package-lock.json", "pnpm-lock.yaml",
                "poetry.lock", "vite.config.ts", "vite.config.js", "webpack.config.js", "tsconfig.json",
                ".env.example", "alembic.ini",
            }:
                marker_files.setdefault(base_name, content)
            for match in ENV_VAR_PATTERN.finditer(content):
                env_vars.add(match.group(1))
            if len(samples) < 120 and language in CODE_LANGUAGES:
                samples[rel] = content[:60_000]
            if len(files) >= settings.MAX_FILES_PER_REPO:
                break

        files.sort(key=lambda f: f.score, reverse=True)
        for rel, content in list(samples.items())[:60]:
            if rel.endswith(".py"):
                static_findings.extend(_python_static_checks(rel, content))
            static_findings.extend(_generic_static_checks(rel, content))

        result.files = files
        result.file_count = len(files)
        result.total_lines = total_lines
        result.size_bytes = total_size
        result.languages = dict(language_lines.most_common())
        result.primary_language = (
            language_lines.most_common(1)[0][0] if language_lines else "Unknown"
        )
        result.env_vars = sorted(env_vars)
        result.static_findings = static_findings[:400]
        result.duplicates = _detect_duplicates(samples)  # type: ignore[attr-defined]

        deps: List[Dict[str, Any]] = []
        scripts: List[str] = []
        package_manager = "Unknown"
        build_tool = "Unknown"

        if "package.json" in marker_files:
            npm_deps, scripts = _parse_package_json(marker_files["package.json"])
            deps.extend(npm_deps)
            package_manager = "npm"
            if "yarn.lock" in marker_files:
                package_manager = "yarn"
            elif "pnpm-lock.yaml" in marker_files:
                package_manager = "pnpm"
            build_tool = "Vite" if any("vite.config" in k for k in marker_files) else "Webpack/Node scripts"
        if "requirements.txt" in marker_files:
            deps.extend(_parse_requirements(marker_files["requirements.txt"]))
            package_manager = "pip" if package_manager == "Unknown" else package_manager
        if "pyproject.toml" in marker_files:
            deps.extend(_parse_pyproject(marker_files["pyproject.toml"]))
            package_manager = "poetry/pip" if package_manager in {"Unknown", "pip"} else package_manager
            build_tool = build_tool if build_tool != "Unknown" else "setuptools/poetry"
        if "pom.xml" in marker_files:
            deps.extend(_parse_pom(marker_files["pom.xml"]))
            package_manager, build_tool = "Maven", "Maven"
        if any(k.startswith("build.gradle") for k in marker_files):
            package_manager, build_tool = "Gradle", "Gradle"
        if "go.mod" in marker_files:
            deps.extend(_parse_gomod(marker_files["go.mod"]))
            package_manager, build_tool = "Go Modules", "go build"
        if "cmakelists.txt" in marker_files:
            build_tool = "CMake"
            package_manager = package_manager if package_manager != "Unknown" else "CMake/vcpkg"
        if "makefile" in marker_files and build_tool == "Unknown":
            build_tool = "Make"
        if "cargo.toml" in marker_files:
            package_manager, build_tool = "Cargo", "Cargo"

        seen_dep: set[str] = set()
        unique_deps = []
        for dep in deps:
            if dep["name"].lower() in seen_dep:
                continue
            seen_dep.add(dep["name"].lower())
            unique_deps.append(dep)
        result.dependencies = unique_deps[:150]
        result.package_manager = package_manager
        result.build_tool = build_tool

        dep_names = " ".join(d["name"].lower() for d in unique_deps)
        marker_blob = " ".join(marker_files.keys()) + " " + " ".join(all_paths[:2000]).lower()
        framework, project_type = "Unknown", "Unknown"
        for marker, fw, ptype in FRAMEWORK_SIGNATURES:
            if marker in dep_names or marker in marker_blob:
                framework, project_type = fw, ptype
                break
        if framework == "Unknown":
            if result.primary_language == "Python":
                framework, project_type = "Standard Library / Scripts", "Python Application"
            elif result.primary_language in {"JavaScript", "TypeScript"}:
                framework, project_type = "Node.js", "JavaScript Application"
            elif result.primary_language == "Java":
                framework, project_type = "Java SE", "Java Application"
            elif result.primary_language in {"C++", "C"}:
                framework, project_type = "Native / STL", "Systems Application"
            elif result.primary_language == "Go":
                framework, project_type = "Go Standard Library", "Go Application"
        result.framework = framework
        result.project_type = project_type
        result.architecture = detect_architecture(all_paths, framework)

        entry_candidates = [
            p for p in all_paths
            if re.search(r"(^|/)(main|app|server|index|manage|cli)\.(py|js|ts|tsx|jsx|go|java|cpp)$", p)
        ]
        result.entrypoints = entry_candidates[:10]
        result.file_tree = build_tree(root)

        code_files = [f for f in files if f.language in CODE_LANGUAGES]
        code_lines = sum(f.lines for f in code_files) or 1
        comment_lines = sum(
            len([ln for ln in content.splitlines() if ln.strip().startswith(("#", "//", "*", "/*", "--"))])
            for content in samples.values()
        )
        sampled_lines = sum(content.count("\n") + 1 for content in samples.values()) or 1
        test_files = [f for f in files if re.search(r"(^|/)(tests?|spec)/|_test\.|\.test\.|\.spec\.", f.path.lower())]
        complexity_findings = [f for f in static_findings if f.get("kind") == "complexity"]
        result.metrics = {
            "code_files": len(code_files),
            "avg_file_lines": round(code_lines / max(len(code_files), 1), 1),
            "largest_file_lines": max((f.lines for f in code_files), default=0),
            "comment_density_pct": round(comment_lines / sampled_lines * 100, 2),
            "test_files": len(test_files),
            "test_ratio_pct": round(len(test_files) / max(len(code_files), 1) * 100, 2),
            "dependency_count": len(unique_deps),
            "high_complexity_functions": len(complexity_findings),
            "avg_cyclomatic": round(
                sum(f.get("cyclomatic", 0) for f in complexity_findings) / max(len(complexity_findings), 1), 2
            ),
            "todo_markers": len([f for f in static_findings if f.get("kind") == "debt"]),
            "secret_hits": len([f for f in static_findings if f.get("kind") == "secret"]),
            "security_hits": len([f for f in static_findings if f.get("kind") == "security"]),
            "unused_imports": len([f for f in static_findings if f.get("kind") == "import"]),
            "duplicate_blocks": len(getattr(result, "duplicates", [])),
            "has_dockerfile": "dockerfile" in marker_files,
            "has_ci": any("github/workflows" in p for p in all_paths),
            "has_readme": any(p.lower().startswith("readme") for p in all_paths),
            "has_env_example": ".env.example" in marker_files,
            "npm_scripts": scripts[:20],
        }
        return result

    def select_code_bundle(self, root: Path, result: AnalysisResult, max_files: int | None = None) -> str:
        """Builds a token-bounded bundle of the most important source files."""
        max_files = max_files or settings.MAX_ANALYZED_FILES_FOR_AI
        budget = settings.MAX_FILE_BYTES_FOR_AI * max_files
        chunks: List[str] = []
        used = 0
        for info in result.files:
            if len([c for c in chunks]) >= max_files or used >= budget:
                break
            if info.language not in CODE_LANGUAGES and info.language not in {"YAML", "JSON", "SQL"}:
                continue
            content = _read_text(root / info.path, settings.MAX_FILE_BYTES_FOR_AI)
            if not content.strip():
                continue
            truncated = content[: settings.MAX_FILE_BYTES_FOR_AI]
            used += len(truncated)
            chunks.append(f"### FILE: {info.path} ({info.language}, {info.lines} lines)\n```\n{truncated}\n```")
        return "\n\n".join(chunks) if chunks else "No readable source files were found."


code_analyzer = CodeAnalyzer()

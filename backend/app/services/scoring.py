"""Deterministic scoring and fallback findings derived from static analysis."""
from __future__ import annotations

from typing import Any, Dict, List

from app.services.code_analyzer import AnalysisResult

OWASP_MAP = {
    "Use of eval() enables arbitrary code execution": ("A03:2021-Injection", "CWE-95"),
    "Use of exec() enables arbitrary code execution": ("A03:2021-Injection", "CWE-95"),
    "Shell injection risk via shell=True": ("A03:2021-Injection", "CWE-78"),
    "Untrusted pickle deserialisation": ("A08:2021-Software and Data Integrity Failures", "CWE-502"),
    "TLS verification disabled": ("A02:2021-Cryptographic Failures", "CWE-295"),
    "Possible SQL injection via string concatenation": ("A03:2021-Injection", "CWE-89"),
    "Potential XSS via innerHTML assignment": ("A03:2021-Injection", "CWE-79"),
    "Potential XSS via dangerouslySetInnerHTML": ("A03:2021-Injection", "CWE-79"),
    "document.write can enable XSS": ("A03:2021-Injection", "CWE-79"),
    "Wildcard CORS origin": ("A05:2021-Security Misconfiguration", "CWE-942"),
}


def compute_static_scores(analysis: AnalysisResult) -> Dict[str, Any]:
    metrics = analysis.metrics
    findings: List[Dict[str, Any]] = []
    security: List[Dict[str, Any]] = []
    performance: List[Dict[str, Any]] = []
    smells: List[Dict[str, Any]] = []
    dead: List[Dict[str, Any]] = []
    unused: List[Dict[str, Any]] = []
    complexity: List[Dict[str, Any]] = []
    solid: List[Dict[str, Any]] = []

    for item in analysis.static_findings:
        kind = item.get("kind")
        file_path = item.get("file", "")
        line = item.get("line", 0)
        reason = item.get("reason", "")
        symbol = item.get("symbol", "")
        if kind == "secret":
            security.append(
                {
                    "title": symbol, "severity": "critical",
                    "owasp": "A07:2021-Identification and Authentication Failures", "cwe": "CWE-798",
                    "file": file_path, "line": line, "description": reason,
                    "remediation": "Move the value to an environment variable and rotate the exposed credential.",
                }
            )
            findings.append(
                {
                    "title": symbol, "severity": "critical", "category": "security", "file": file_path,
                    "line": line, "description": reason,
                    "impact": "Leaked credentials allow account takeover and data exfiltration.",
                    "recommendation": "Load secrets from environment variables and rotate the key.",
                    "source": "static",
                }
            )
        elif kind == "security":
            owasp, cwe = OWASP_MAP.get(symbol, ("A05:2021-Security Misconfiguration", "CWE-693"))
            security.append(
                {
                    "title": symbol, "severity": item.get("severity", "medium"), "owasp": owasp, "cwe": cwe,
                    "file": file_path, "line": line, "description": reason,
                    "remediation": "Replace the unsafe construct with a validated, parameterised alternative.",
                }
            )
            findings.append(
                {
                    "title": symbol, "severity": item.get("severity", "medium"), "category": "security",
                    "file": file_path, "line": line, "description": reason,
                    "impact": "Creates an exploitable attack surface.",
                    "recommendation": "Use a safe API and validate all untrusted input.",
                    "source": "static",
                }
            )
        elif kind == "complexity":
            complexity.append(
                {
                    "file": file_path, "function": symbol, "cyclomatic": item.get("cyclomatic", 0),
                    "time_complexity": "review required", "space_complexity": "review required",
                    "explanation": reason,
                    "recommendation": "Extract helper functions and flatten nested branches.",
                }
            )
            performance.append(
                {
                    "title": f"High complexity in {symbol}", "severity": "medium", "file": file_path,
                    "line": line, "description": reason,
                    "optimization": "Split the function and cache repeated computations.",
                    "expected_gain": "Lower latency and easier optimisation",
                }
            )
        elif kind == "import":
            unused.append({"file": file_path, "kind": "import", "symbol": symbol, "line": line})
            dead.append({"file": file_path, "symbol": symbol, "line": line, "reason": reason})
        elif kind == "srp":
            solid.append(
                {
                    "principle": "SRP", "file": file_path, "class_or_function": symbol,
                    "description": reason,
                    "fix": "Split the class into cohesive collaborators with a single responsibility each.",
                }
            )
        elif kind == "smell":
            smells.append(
                {
                    "name": symbol, "file": file_path, "line": line, "description": reason,
                    "refactoring": "Apply extract-method / remove-debug-code refactoring.",
                }
            )
        elif kind == "debt":
            smells.append(
                {
                    "name": "Unresolved TODO/FIXME", "file": file_path, "line": line, "description": reason,
                    "refactoring": "Convert the marker into a tracked issue and implement or remove it.",
                }
            )

    security_hits = metrics.get("security_hits", 0) + metrics.get("secret_hits", 0) * 3
    security_score = max(20.0, 100.0 - security_hits * 6)
    complexity_penalty = metrics.get("high_complexity_functions", 0) * 4
    complexity_score = max(20.0, 100.0 - complexity_penalty)
    doc_bonus = 8 if metrics.get("has_readme") else 0
    test_score = min(metrics.get("test_ratio_pct", 0) * 1.4, 30)
    comment_score = min(metrics.get("comment_density_pct", 0) * 1.2, 15)
    size_penalty = min(metrics.get("avg_file_lines", 0) / 30.0, 15)
    maintainability = max(20.0, 45 + test_score + comment_score + doc_bonus - size_penalty)
    debt_penalty = metrics.get("todo_markers", 0) * 1.5 + metrics.get("duplicate_blocks", 0) * 3 + metrics.get("unused_imports", 0)
    technical_debt = max(15.0, 100.0 - debt_penalty)
    performance_score = max(25.0, 92.0 - metrics.get("high_complexity_functions", 0) * 3.5)
    scalability = 60.0 + (10 if metrics.get("has_dockerfile") else 0) + (8 if metrics.get("has_ci") else 0)
    scalability = min(scalability + (6 if metrics.get("dependency_count", 0) > 5 else 0), 96.0)
    quality = round(
        (security_score * 0.25 + maintainability * 0.25 + complexity_score * 0.2 + technical_debt * 0.15 + performance_score * 0.15),
        1,
    )

    summary = (
        f"{analysis.primary_language} {analysis.project_type.lower()} built with {analysis.framework} "
        f"following a {analysis.architecture} structure. Scanned {analysis.file_count} files "
        f"({analysis.total_lines} lines) and {metrics.get('dependency_count', 0)} dependencies. "
        f"Static analysis surfaced {len(security)} security issues, {len(smells)} code smells, "
        f"{metrics.get('unused_imports', 0)} unused imports and {metrics.get('duplicate_blocks', 0)} duplicated blocks. "
        f"Test coverage signal is {metrics.get('test_ratio_pct', 0)}% of code files."
    )

    dependency_analysis = [
        {
            "name": dep.get("name", ""),
            "version": dep.get("version", ""),
            "risk": "medium" if not dep.get("version") else "low",
            "note": f"{dep.get('ecosystem', 'unknown')} {dep.get('kind', 'runtime')} dependency",
            "recommendation": "Pin an explicit version and monitor advisories"
            if not dep.get("version")
            else "Keep up to date with security releases",
        }
        for dep in analysis.dependencies[:40]
    ]

    best_practices = [
        {"area": "README", "status": "good" if metrics.get("has_readme") else "missing",
         "detail": "Project documentation entry point", "action": "Add a README.md with setup and usage"},
        {"area": "Automated tests", "status": "good" if metrics.get("test_files", 0) > 0 else "missing",
         "detail": f"{metrics.get('test_files', 0)} test files detected",
         "action": "Introduce unit tests for core modules"},
        {"area": "Containerisation", "status": "good" if metrics.get("has_dockerfile") else "missing",
         "detail": "Dockerfile presence", "action": "Add a Dockerfile for reproducible builds"},
        {"area": "CI pipeline", "status": "good" if metrics.get("has_ci") else "missing",
         "detail": "GitHub Actions workflow presence", "action": "Add CI running lint and tests on push"},
        {"area": "Secret management", "status": "good" if metrics.get("secret_hits", 0) == 0 else "needs_improvement",
         "detail": f"{metrics.get('secret_hits', 0)} potential hardcoded secrets",
         "action": "Move secrets to environment variables"},
        {"area": "Environment template", "status": "good" if metrics.get("has_env_example") else "missing",
         "detail": ".env.example presence", "action": "Provide a .env.example for onboarding"},
    ]

    refactoring = [
        {
            "title": f"Reduce complexity of {item['function']}",
            "file": item["file"],
            "before": f"cyclomatic complexity {item.get('cyclomatic', 0)}",
            "after": "extracted helpers with complexity < 10",
            "benefit": "Easier testing and lower defect rate",
        }
        for item in complexity[:8]
    ]
    optimizations = [
        {
            "title": "Remove unused imports",
            "file": unused[0]["file"] if unused else "",
            "description": f"{len(unused)} unused imports increase load time and confusion",
            "expected_gain": "Faster module import, cleaner static analysis",
        }
    ] if unused else []

    generated_tests = [
        {
            "kind": "unit",
            "target_file": analysis.entrypoints[0] if analysis.entrypoints else "",
            "framework": "pytest" if analysis.primary_language == "Python" else "jest",
            "file_name": "test_smoke.py" if analysis.primary_language == "Python" else "smoke.test.js",
            "code": (
                "def test_module_imports():\n    import importlib\n\n"
                "    module = importlib.import_module('__main__')\n    assert module is not None\n"
                if analysis.primary_language == "Python"
                else "test('module loads', () => {\n  expect(true).toBe(true);\n});\n"
            ),
            "description": "Smoke test placeholder generated by static analysis (enable AI for full suites).",
        }
    ]

    clean_architecture = {
        "assessment": f"Detected {analysis.architecture}. Layer separation inferred from folder structure.",
        "layer_violations": [item["file"] for item in solid[:5]],
        "score": round(min(95.0, maintainability), 1),
        "boundaries": list(analysis.languages.keys())[:5],
        "recommendations": [
            "Keep framework code at the edges and domain logic framework-free",
            "Depend on abstractions between layers",
        ],
    }

    return {
        "scores": {
            "quality": quality,
            "maintainability": round(maintainability, 1),
            "security": round(security_score, 1),
            "performance": round(performance_score, 1),
            "complexity": round(complexity_score, 1),
            "technical_debt": round(technical_debt, 1),
            "scalability": round(scalability, 1),
        },
        "summary": summary,
        "findings": findings[:60],
        "security_findings": security[:30],
        "performance_findings": performance[:20],
        "code_smells": smells[:30],
        "dead_code": dead[:20],
        "unused_symbols": unused[:30],
        "complexity_analysis": complexity[:20],
        "solid_violations": solid[:15],
        "design_patterns": [
            {"pattern": "Repository", "file": "", "usage": "inferred from folder naming", "assessment": "present"}
        ] if any("repositor" in f.path.lower() for f in analysis.files) else [],
        "dependency_analysis": dependency_analysis,
        "refactoring": refactoring,
        "optimizations": optimizations,
        "generated_tests": generated_tests,
        "clean_architecture": clean_architecture,
        "best_practices": best_practices,
    }

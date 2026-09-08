from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.common import ORMModel


class GithubImportRequest(BaseModel):
    url: str = Field(min_length=8, max_length=500)
    branch: Optional[str] = Field(default=None, max_length=120)
    name: Optional[str] = Field(default=None, max_length=200)
    description: str = Field(default="", max_length=500)

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("Repository URL must start with http:// or https://")
        if not value.endswith(".git"):
            value = value.rstrip("/")
        return value


class RepositoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)


class RepositoryOut(ORMModel):
    id: int
    name: str
    description: str
    source_type: str
    source_url: str
    branch: str
    status: str
    error_message: str
    primary_language: str
    framework: str
    architecture: str
    project_type: str
    package_manager: str
    build_tool: str
    file_count: int
    total_lines: int
    size_bytes: int
    languages: Dict[str, Any] = {}
    dependencies: List[Any] = []
    entrypoints: List[Any] = []
    metrics: Dict[str, Any] = {}
    indexed_chunks: int = 0
    created_at: datetime
    updated_at: datetime

    @field_validator("source_type", "status", mode="before")
    @classmethod
    def enum_to_str(cls, value: Any) -> str:
        return getattr(value, "value", value)


class RepositoryDetail(RepositoryOut):
    file_tree: Dict[str, Any] = {}
    review_count: int = 0
    document_count: int = 0
    diagram_count: int = 0
    report_count: int = 0
    latest_review_id: Optional[int] = None


class FileContentOut(BaseModel):
    path: str
    language: str
    lines: int
    size_bytes: int
    content: str
    truncated: bool


class ReviewCreate(BaseModel):
    depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")
    focus: List[str] = Field(default_factory=list)


class ReviewOut(ORMModel):
    id: int
    repository_id: int
    user_id: int
    status: str
    depth: str
    provider: str
    model: str
    ai_powered: bool
    summary: str
    error_message: str
    quality_score: float
    maintainability_score: float
    security_score: float
    performance_score: float
    complexity_score: float
    technical_debt_score: float
    scalability_score: float
    stats: Dict[str, Any] = {}
    created_at: datetime
    completed_at: Optional[datetime] = None

    @field_validator("status", mode="before")
    @classmethod
    def enum_to_str(cls, value: Any) -> str:
        return getattr(value, "value", value)


class ReviewDetail(ReviewOut):
    findings: List[Any] = []
    security_findings: List[Any] = []
    performance_findings: List[Any] = []
    code_smells: List[Any] = []
    dead_code: List[Any] = []
    duplicate_code: List[Any] = []
    unused_symbols: List[Any] = []
    complexity_analysis: List[Any] = []
    solid_violations: List[Any] = []
    design_patterns: List[Any] = []
    dependency_analysis: List[Any] = []
    refactoring_suggestions: List[Any] = []
    optimization_suggestions: List[Any] = []
    auto_fixes: List[Any] = []
    generated_tests: List[Any] = []
    clean_architecture: Dict[str, Any] = {}
    best_practices: List[Any] = []
    repository_name: Optional[str] = None


class DocumentOut(ORMModel):
    id: int
    repository_id: int
    doc_type: str
    title: str
    content: str
    ai_powered: bool
    created_at: datetime


class DocumentGenerateRequest(BaseModel):
    doc_types: List[str] = Field(default_factory=list)
    regenerate: bool = True


class DiagramOut(ORMModel):
    id: int
    repository_id: int
    diagram_type: str
    title: str
    mermaid: str
    plantuml: str
    drawio_xml: str
    ai_powered: bool
    created_at: datetime


class DiagramGenerateRequest(BaseModel):
    diagram_types: List[str] = Field(default_factory=list)
    regenerate: bool = True


class DiagramUpdate(BaseModel):
    mermaid: Optional[str] = None
    plantuml: Optional[str] = None
    drawio_xml: Optional[str] = None


class ReportOut(ORMModel):
    id: int
    repository_id: int
    review_id: Optional[int]
    title: str
    file_name: str
    size_bytes: int
    sections: List[Any] = []
    created_at: datetime
    repository_name: Optional[str] = None


class ReportCreate(BaseModel):
    review_id: Optional[int] = None
    include_documentation: bool = True
    include_diagrams: bool = True


class ChatAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[int] = None


class ChatCitation(BaseModel):
    path: str
    snippet: str
    score: Optional[float] = None


class ChatMessageOut(ORMModel):
    id: int
    session_id: int
    role: str
    content: str
    citations: List[Any] = []
    created_at: datetime


class ChatSessionOut(ORMModel):
    id: int
    repository_id: int
    title: str
    created_at: datetime
    message_count: int = 0


class ChatAnswer(BaseModel):
    session_id: int
    answer: ChatMessageOut
    citations: List[Any] = []
    chunks_used: int = 0
    ai_powered: bool = True


class DashboardStats(BaseModel):
    total_repositories: int
    total_reviews: int
    total_reports: int
    total_documents: int
    total_diagrams: int
    total_findings: int
    critical_findings: int
    avg_quality_score: float
    avg_security_score: float
    avg_maintainability_score: float
    avg_performance_score: float
    avg_complexity_score: float
    avg_technical_debt_score: float
    language_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]
    score_trend: List[Dict[str, Any]]
    recent_repositories: List[RepositoryOut]
    recent_reviews: List[ReviewOut]
    ai_enabled: bool
    ai_model: str

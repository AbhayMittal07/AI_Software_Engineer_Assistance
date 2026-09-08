export type Role = "admin" | "reviewer" | "developer";

export interface UserSettings {
  theme: string;
  ai_model: string;
  review_depth: string;
  auto_generate_docs: boolean;
  auto_generate_diagrams: boolean;
  email_notifications: boolean;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  bio: string;
  company: string;
  created_at: string;
  last_login_at: string | null;
  settings?: UserSettings | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
}

export interface Dependency {
  name: string;
  version: string;
  kind: string;
  ecosystem: string;
}

export interface Repository {
  id: number;
  name: string;
  description: string;
  source_type: "zip" | "github";
  source_url: string;
  branch: string;
  status: "pending" | "analyzing" | "ready" | "failed";
  error_message: string;
  primary_language: string;
  framework: string;
  architecture: string;
  project_type: string;
  package_manager: string;
  build_tool: string;
  file_count: number;
  total_lines: number;
  size_bytes: number;
  languages: Record<string, number>;
  dependencies: Dependency[];
  entrypoints: string[];
  metrics: Record<string, any>;
  indexed_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface TreeNode {
  name: string;
  type: "dir" | "file" | "info";
  size?: number;
  path?: string;
  language?: string;
  children?: TreeNode[];
}

export interface RepositoryDetail extends Repository {
  file_tree: TreeNode;
  review_count: number;
  document_count: number;
  diagram_count: number;
  report_count: number;
  latest_review_id: number | null;
}

export interface Finding {
  title?: string;
  severity?: string;
  category?: string;
  file?: string;
  line?: number;
  description?: string;
  impact?: string;
  recommendation?: string;
  code_snippet?: string;
  suggested_fix?: string;
  source?: string;
  [key: string]: any;
}

export interface Review {
  id: number;
  repository_id: number;
  user_id: number;
  status: "pending" | "running" | "completed" | "failed";
  depth: string;
  provider: string;
  model: string;
  ai_powered: boolean;
  summary: string;
  error_message: string;
  quality_score: number;
  maintainability_score: number;
  security_score: number;
  performance_score: number;
  complexity_score: number;
  technical_debt_score: number;
  scalability_score: number;
  stats: Record<string, any>;
  created_at: string;
  completed_at: string | null;
}

export interface ReviewDetail extends Review {
  findings: Finding[];
  security_findings: Finding[];
  performance_findings: Finding[];
  code_smells: Finding[];
  dead_code: Finding[];
  duplicate_code: Finding[];
  unused_symbols: Finding[];
  complexity_analysis: Finding[];
  solid_violations: Finding[];
  design_patterns: Finding[];
  dependency_analysis: Finding[];
  refactoring_suggestions: Finding[];
  optimization_suggestions: Finding[];
  auto_fixes: Finding[];
  generated_tests: Finding[];
  clean_architecture: Record<string, any>;
  best_practices: Finding[];
  repository_name?: string | null;
}

export interface DocumentItem {
  id: number;
  repository_id: number;
  doc_type: string;
  title: string;
  content: string;
  ai_powered: boolean;
  created_at: string;
}

export interface DiagramItem {
  id: number;
  repository_id: number;
  diagram_type: string;
  title: string;
  mermaid: string;
  plantuml: string;
  drawio_xml: string;
  ai_powered: boolean;
  created_at: string;
}

export interface ReportItem {
  id: number;
  repository_id: number;
  review_id: number | null;
  title: string;
  file_name: string;
  size_bytes: number;
  sections: string[];
  created_at: string;
  repository_name?: string | null;
}

export interface Citation {
  path: string;
  snippet: string;
  score?: number | null;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface ChatSession {
  id: number;
  repository_id: number;
  title: string;
  created_at: string;
  message_count: number;
}

export interface ChatAnswer {
  session_id: number;
  answer: ChatMessage;
  citations: Citation[];
  chunks_used: number;
  ai_powered: boolean;
}

export interface DashboardStats {
  total_repositories: number;
  total_reviews: number;
  total_reports: number;
  total_documents: number;
  total_diagrams: number;
  total_findings: number;
  critical_findings: number;
  avg_quality_score: number;
  avg_security_score: number;
  avg_maintainability_score: number;
  avg_performance_score: number;
  avg_complexity_score: number;
  avg_technical_debt_score: number;
  language_distribution: Record<string, number>;
  severity_distribution: Record<string, number>;
  score_trend: Array<Record<string, any>>;
  recent_repositories: Repository[];
  recent_reviews: Review[];
  ai_enabled: boolean;
  ai_model: string;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

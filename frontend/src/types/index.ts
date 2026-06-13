export interface User {
  id: string
  github_login: string
  name: string | null
  email: string | null
  avatar_url: string | null
  career_track: string | null
  current_difficulty: string
  total_score: number
  issues_resolved: number
}

export interface Problem {
  id: string
  slug: string
  title: string
  description: string
  difficulty: 'junior' | 'mid' | 'senior'
  category: string
  track?: string
  language: string
  files: Record<string, string>
}

export interface Session {
  id: string
  problem_id: string
  status: string
  started_at: string
}

export interface TestCase {
  name: string
  status: 'passed' | 'failed' | 'error'
  duration_ms: number
  error: string | null
}

export interface TestRun {
  status: 'completed' | 'timeout' | 'error'
  passed: number
  failed: number
  total: number
  duration_ms: number
  tests: TestCase[]
}

export interface Submission {
  submission_id: string
  status: string
  score: number | null
  review_id: string | null
  submitted_at: string
  completed_at: string | null
}

export interface ScoreBreakdown {
  correctness: number
  code_quality: number
  performance: number
  security: number
  tests: number
}

export interface InlineComment {
  file: string
  line: number
  severity: 'praise' | 'info' | 'warning' | 'error'
  comment: string
}

export interface Resource {
  title: string
  url: string
  why: string
}

export interface Review {
  verdict: 'accept' | 'minor_revisions' | 'major_revisions'
  overall_score: number
  score_breakdown: ScoreBreakdown
  summary: string
  inline_comments: InlineComment[]
  learning_resources: Resource[]
  architectural_note: string | null
  code_snapshot: Record<string, string>
  ast_score: number | null
  security_score: number | null
  test_score: number | null
  pipeline_duration_ms: number | null
}

export interface ResolutionEntry {
  problem_title: string
  difficulty: string
  score: number
  time_taken_mins: number | null
  solved_at: string
}

export interface PortfolioHighlight {
  metric: string
  value: string
}

export interface PortfolioUser {
  github_login: string
  name: string | null
  avatar_url: string | null
  career_track: string | null
}

export interface PortfolioCard {
  user: PortfolioUser
  issues_resolved: number
  avg_score: number
  skill_percentile: number
  skill_radar: Record<string, number>
  highlights: PortfolioHighlight[]
  resolution_log: ResolutionEntry[]
  signature: string | null
}

export interface CurrentProblemResponse {
  problem: Problem
  session_id: string
}

export interface ProblemProgress {
  id: string
  slug: string
  title: string
  difficulty: string
  category: string
  track: string
  points: number
  solved: boolean
  best_score: number | null
  attempts: number
}

export interface GenerateProblemRequest {
  topic: string
}

export interface ActivityDay {
  date: string
  count: number
}

export interface ActivityResponse {
  days: ActivityDay[]
  total_active_days: number
  total_activity: number
  current_streak: number
  longest_streak: number
  max_in_one_day: number
}

export interface RecentSubmission {
  id: string
  problem_title: string
  difficulty: string
  status: string
  score: number | null
  submitted_at: string
  completed_at: string | null
}

export interface ProgressResponse {
  problems: ProblemProgress[]
  recent_submissions: RecentSubmission[]
}

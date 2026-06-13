import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Award,
  CheckCircle,
  ChevronRight,
  Circle,
  Loader,
  Play,
  Sparkles,
} from 'lucide-react'
import { api } from '../lib/api'
import AppHeader from '../components/AppHeader'
import type { User, ProgressResponse } from '../types'

const TRACKS = ['fullstack', 'backend', 'frontend', 'devops']
const TRACK_LABELS: Record<string, string> = {
  fullstack: 'Full-Stack',
  backend: 'Backend',
  frontend: 'Frontend',
  devops: 'DevOps',
}
const DIFFICULTY_COLORS: Record<string, string> = {
  junior: 'bg-[#1a4731] text-[#3fb950]',
  mid: 'bg-[#3d2f00] text-[#d29922]',
  senior: 'bg-[#3d0c09] text-[#f85149]',
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [progress, setProgress] = useState<ProgressResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSelectingTrack, setIsSelectingTrack] = useState(false)
  const [showTrackPicker, setShowTrackPicker] = useState(false)

  // ── Generate modal state ────────────────────────────────────────────────────
  const [showGenerateModal, setShowGenerateModal] = useState(false)
  const [generateTopic, setGenerateTopic] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [u, p] = await Promise.all([api.getMe(), api.getProgress()])
      setUser(u)
      setProgress(p)
      if (!u.career_track) setShowTrackPicker(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleSelectTrack = async (track: string) => {
    setIsSelectingTrack(true)
    try {
      const updated = await api.updateTrack(track)
      setUser(updated)
      setShowTrackPicker(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to set track')
    } finally {
      setIsSelectingTrack(false)
    }
  }

  const handleGenerate = async () => {
    if (!generateTopic.trim()) return
    setIsGenerating(true)
    setGenerateError(null)
    try {
      const result = await api.generateProblem({ topic: generateTopic.trim() })
      setShowGenerateModal(false)
      setGenerateTopic('')
      navigate(`/workspace/${result.problem.slug}`)
    } catch (err: unknown) {
      setGenerateError(
        err instanceof Error ? err.message : 'Generation failed — please try again',
      )
    } finally {
      setIsGenerating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center gap-3 text-[#8b949e]">
        <Loader size={24} className="animate-spin" />
        <span>Loading dashboard...</span>
      </div>
    )
  }

  if (error || !user || !progress) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="bg-[#161b22] border border-[#da3633] rounded-xl p-8 max-w-md text-center">
          <AlertCircle size={40} className="text-[#f85149] mx-auto mb-4" />
          <h2 className="text-[#e6edf3] font-semibold text-lg mb-2">Failed to load dashboard</h2>
          <p className="text-[#8b949e] text-sm mb-6">{error}</p>
          <button
            onClick={() => load()}
            className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Separate curated problems from user-generated ones
  const curatedProblems = progress.problems.filter((p) => !p.slug.startsWith('gen-'))
  const generatedProblems = progress.problems.filter((p) => p.slug.startsWith('gen-'))

  const solvedCount = curatedProblems.filter((p) => p.solved).length
  const totalCount = curatedProblems.length

  // Group curated problems by track, user's own track first
  const problemsByTrack = curatedProblems.reduce<Record<string, typeof curatedProblems>>(
    (acc, p) => {
      const track = p.track ?? 'backend'
      ;(acc[track] ??= []).push(p)
      return acc
    },
    {},
  )
  const trackOrder = [
    ...(user.career_track ? [user.career_track] : []),
    ...TRACKS.filter((t) => t !== user.career_track),
    ...Object.keys(problemsByTrack).filter((t) => !TRACKS.includes(t)),
  ]
  const scores = progress.problems
    .map((p) => p.best_score)
    .filter((s): s is number => s !== null)
  const avgScore = scores.length
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    : null

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <AppHeader user={user} />

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Greeting + actions */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-xl font-semibold">
              Welcome back, {user.name ?? user.github_login}
            </h1>
            <p className="text-sm text-[#8b949e] mt-1">
              Track:{' '}
              <span className="text-[#e6edf3]">
                {user.career_track ? TRACK_LABELS[user.career_track] ?? user.career_track : 'not chosen'}
              </span>
              {user.career_track && (
                <button
                  onClick={() => setShowTrackPicker(true)}
                  className="ml-2 text-xs text-[#58a6ff] hover:underline"
                >
                  change
                </button>
              )}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to={`/p/${user.github_login}`}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c2128] hover:bg-[#30363d] border border-[#30363d] rounded text-xs font-medium transition-colors"
            >
              <Award size={13} />
              View Portfolio
            </Link>
            <button
              onClick={() => setShowGenerateModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c2128] hover:bg-[#30363d] border border-[#30363d] rounded text-xs font-medium transition-colors"
            >
              <Sparkles size={13} />
              Create for me
            </button>
            <button
              onClick={() => navigate('/workspace')}
              disabled={!user.career_track}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#238636] hover:bg-[#2ea043] rounded text-xs font-medium text-white transition-colors disabled:opacity-50"
            >
              <Play size={13} />
              {solvedCount > 0 ? 'Continue Solving' : 'Start Solving'}
            </button>
          </div>
        </div>

        {/* Track picker (first login or change) */}
        {showTrackPicker && (
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6">
            <h2 className="text-base font-semibold mb-1">Choose your track</h2>
            <p className="text-[#8b949e] text-sm mb-4">
              This determines which problems and skills are highlighted in your portfolio.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {TRACKS.map((track) => (
                <button
                  key={track}
                  disabled={isSelectingTrack}
                  onClick={() => handleSelectTrack(track)}
                  className={`py-3 px-4 bg-[#1c2128] border rounded-lg text-sm font-medium transition-all disabled:opacity-50 ${
                    user.career_track === track
                      ? 'border-[#58a6ff] bg-[#0d2e4d]'
                      : 'border-[#30363d] hover:border-[#58a6ff] hover:bg-[#0d2e4d]'
                  }`}
                >
                  {TRACK_LABELS[track]}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-4 mt-4">
              {isSelectingTrack && (
                <span className="flex items-center gap-2 text-[#8b949e] text-sm">
                  <Loader size={14} className="animate-spin" />
                  Saving...
                </span>
              )}
              {user.career_track && !isSelectingTrack && (
                <button
                  onClick={() => setShowTrackPicker(false)}
                  className="text-xs text-[#8b949e] hover:text-[#e6edf3]"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Problems Solved', value: `${solvedCount}/${totalCount}` },
            { label: 'Issues Resolved', value: String(user.issues_resolved) },
            { label: 'Total Score', value: String(user.total_score) },
            { label: 'Avg Score', value: avgScore !== null ? String(avgScore) : '—' },
          ].map((s) => (
            <div key={s.label} className="bg-[#161b22] border border-[#30363d] rounded-xl p-4">
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-xs text-[#8b949e] mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Problem bank, grouped by track */}
        <section>
          <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-3">
            Problems
          </h2>
          {curatedProblems.length === 0 && (
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl">
              <p className="p-4 text-sm text-[#8b949e]">No problems available yet.</p>
            </div>
          )}
          <div className="space-y-6">
            {trackOrder
              .filter((track) => problemsByTrack[track]?.length)
              .map((track) => (
                <div key={track}>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-xs font-semibold text-[#e6edf3] uppercase tracking-wider">
                      {TRACK_LABELS[track] ?? track}
                    </h3>
                    <span className="text-xs text-[#8b949e]">
                      {problemsByTrack[track].filter((p) => p.solved).length}/
                      {problemsByTrack[track].length} solved
                    </span>
                    {track === user.career_track && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#0d2e4d] text-[#58a6ff] font-medium">
                        your track
                      </span>
                    )}
                  </div>
                  <div className="bg-[#161b22] border border-[#30363d] rounded-xl divide-y divide-[#21262d]">
                    {problemsByTrack[track].map((p) => (
                      <Link
                        key={p.id}
                        to={`/workspace/${p.slug}`}
                        className="flex items-center gap-3 px-4 py-3 hover:bg-[#1c2128] transition-colors group"
                      >
                        {p.solved ? (
                          <CheckCircle size={16} className="text-[#3fb950] shrink-0" />
                        ) : (
                          <Circle size={16} className="text-[#30363d] shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate group-hover:text-[#58a6ff] transition-colors">
                            {p.title}
                          </p>
                          <p className="text-xs text-[#8b949e]">
                            {p.category}
                            {p.attempts > 0 && ` · ${p.attempts} attempt${p.attempts > 1 ? 's' : ''}`}
                          </p>
                        </div>
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded font-medium shrink-0 ${DIFFICULTY_COLORS[p.difficulty] ?? 'bg-[#1c2128] text-[#8b949e]'}`}
                        >
                          {p.difficulty}
                        </span>
                        <span className="text-xs text-[#8b949e] w-16 text-right shrink-0">
                          {p.best_score !== null ? `${p.best_score}/100` : '—'}
                        </span>
                        <ChevronRight
                          size={14}
                          className="text-[#30363d] group-hover:text-[#8b949e] shrink-0"
                        />
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        </section>

        {/* Your Custom Problems (AI-generated, user-specific) */}
        {generatedProblems.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider">
                Your Custom Problems
              </h2>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#2d1f4e] text-[#a371f7] font-medium flex items-center gap-1">
                <Sparkles size={9} />
                AI-generated
              </span>
            </div>
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl divide-y divide-[#21262d]">
              {generatedProblems.map((p) => (
                <Link
                  key={p.id}
                  to={`/workspace/${p.slug}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-[#1c2128] transition-colors group"
                >
                  {p.solved ? (
                    <CheckCircle size={16} className="text-[#3fb950] shrink-0" />
                  ) : (
                    <Circle size={16} className="text-[#30363d] shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate group-hover:text-[#58a6ff] transition-colors">
                      {p.title}
                    </p>
                    <p className="text-xs text-[#8b949e]">
                      {p.category}
                      {p.attempts > 0 && ` · ${p.attempts} attempt${p.attempts > 1 ? 's' : ''}`}
                    </p>
                  </div>
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded font-medium shrink-0 ${DIFFICULTY_COLORS[p.difficulty] ?? 'bg-[#1c2128] text-[#8b949e]'}`}
                  >
                    {p.difficulty}
                  </span>
                  <span className="text-xs text-[#8b949e] w-16 text-right shrink-0">
                    {p.best_score !== null ? `${p.best_score}/100` : '—'}
                  </span>
                  <ChevronRight
                    size={14}
                    className="text-[#30363d] group-hover:text-[#8b949e] shrink-0"
                  />
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Recent submissions */}
        <section>
          <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-3">
            Recent Submissions
          </h2>
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl divide-y divide-[#21262d]">
            {progress.recent_submissions.length === 0 && (
              <p className="p-4 text-sm text-[#8b949e]">
                No submissions yet — open the workspace to get started.
              </p>
            )}
            {progress.recent_submissions.map((s) => {
              const row = (
                <>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{s.problem_title}</p>
                    <p className="text-xs text-[#8b949e]">
                      {new Date(s.submitted_at).toLocaleString()} · {s.status}
                    </p>
                  </div>
                  <span className="text-xs text-[#8b949e] shrink-0">
                    {s.score !== null ? `${s.score}/100` : '—'}
                  </span>
                  {s.status === 'completed' && (
                    <ChevronRight size={14} className="text-[#8b949e] shrink-0" />
                  )}
                </>
              )
              return s.status === 'completed' ? (
                <Link
                  key={s.id}
                  to={`/review/${s.id}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-[#1c2128] transition-colors"
                >
                  {row}
                </Link>
              ) : (
                <div key={s.id} className="flex items-center gap-3 px-4 py-3">
                  {row}
                </div>
              )
            })}
          </div>
        </section>
      </div>

      {/* ── Generate-problem modal (portal-style fixed overlay) ── */}
      {showGenerateModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 w-full max-w-md">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles size={16} className="text-[#a371f7]" />
              <h2 className="text-base font-semibold">Create a custom problem</h2>
            </div>
            <p className="text-[#8b949e] text-sm mb-4">
              Describe what you want to practice. AI will design a broken FastAPI
              codebase with pytest tests — yours to fix, submit, and add to your portfolio.
            </p>
            <input
              type="text"
              placeholder="e.g. rate limiting, JWT auth, database connection pooling…"
              value={generateTopic}
              onChange={(e) => setGenerateTopic(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !isGenerating) void handleGenerate()
              }}
              disabled={isGenerating}
              autoFocus
              className="w-full px-3 py-2 bg-[#0d1117] border border-[#30363d] rounded-lg text-sm text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-[#58a6ff] disabled:opacity-50"
            />
            {generateError && (
              <p className="text-[#f85149] text-xs mt-2 flex items-center gap-1">
                <AlertCircle size={11} />
                {generateError}
              </p>
            )}
            <div className="flex items-center justify-end gap-3 mt-4">
              <button
                onClick={() => {
                  setShowGenerateModal(false)
                  setGenerateTopic('')
                  setGenerateError(null)
                }}
                disabled={isGenerating}
                className="text-xs text-[#8b949e] hover:text-[#e6edf3] disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => void handleGenerate()}
                disabled={isGenerating || !generateTopic.trim()}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
              >
                {isGenerating ? (
                  <>
                    <Loader size={13} className="animate-spin" />
                    Generating… (10–20 s)
                  </>
                ) : (
                  <>
                    <Sparkles size={13} />
                    Generate problem
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

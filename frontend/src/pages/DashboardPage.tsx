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

  const solvedCount = progress.problems.filter((p) => p.solved).length
  const totalCount = progress.problems.length
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

        {/* Problem progress */}
        <section>
          <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-3">
            Problems
          </h2>
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl divide-y divide-[#21262d]">
            {progress.problems.length === 0 && (
              <p className="p-4 text-sm text-[#8b949e]">No problems available yet.</p>
            )}
            {progress.problems.map((p) => (
              <div key={p.id} className="flex items-center gap-3 px-4 py-3">
                {p.solved ? (
                  <CheckCircle size={16} className="text-[#3fb950] shrink-0" />
                ) : (
                  <Circle size={16} className="text-[#30363d] shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{p.title}</p>
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
              </div>
            ))}
          </div>
        </section>

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
    </div>
  )
}

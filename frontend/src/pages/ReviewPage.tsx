import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Lock,
  Loader,
} from 'lucide-react'
import { api } from '../lib/api'
import ReviewPanel from '../components/ReviewPanel'
import type { Review, User } from '../types'

const VERDICT_CONFIG = {
  accept: {
    icon: <CheckCircle size={20} />,
    label: '✓ ACCEPTED',
    bg: 'bg-[#1a4731]',
    border: 'border-[#238636]',
    text: 'text-[#3fb950]',
    badge: 'bg-[#238636]',
  },
  minor_revisions: {
    icon: <AlertTriangle size={20} />,
    label: '⚠ NEEDS MINOR REVISIONS',
    bg: 'bg-[#3d2f00]',
    border: 'border-[#9e6a03]',
    text: 'text-[#d29922]',
    badge: 'bg-[#d29922]',
  },
  major_revisions: {
    icon: <XCircle size={20} />,
    label: '✗ NEEDS MAJOR REVISIONS',
    bg: 'bg-[#3d0c09]',
    border: 'border-[#da3633]',
    text: 'text-[#f85149]',
    badge: 'bg-[#f85149]',
  },
}

function scoreColor(score: number): string {
  if (score >= 85) return 'text-[#3fb950]'
  if (score >= 60) return 'text-[#d29922]'
  return 'text-[#f85149]'
}

function ScoreBar({
  label,
  value,
  max,
}: {
  label: string
  value: number
  max: number
}) {
  const pct = Math.round((value / max) * 100)
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-[#8b949e] w-28 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-[#21262d] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#58a6ff] rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-[#e6edf3] w-12 text-right shrink-0">
        {value}/{max}
      </span>
    </div>
  )
}

export default function ReviewPage() {
  const { submissionId } = useParams<{ submissionId: string }>()
  const [review, setReview] = useState<Review | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!submissionId) return
    setIsLoading(true)
    api
      .getReview(submissionId)
      .then(setReview)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to load review')
      })
      .finally(() => setIsLoading(false))
    // Needed for the "View Portfolio" link (portfolio URLs are per github login)
    api.getMe().then(setUser).catch(() => {})
  }, [submissionId])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center gap-3 text-[#8b949e]">
        <Loader size={24} className="animate-spin" />
        <span>Loading review...</span>
      </div>
    )
  }

  if (error || !review) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#f85149] mb-4">{error ?? 'Review not found'}</p>
          <Link to="/workspace" className="text-[#58a6ff] hover:underline text-sm">
            ← Back to workspace
          </Link>
        </div>
      </div>
    )
  }

  const verdict = VERDICT_CONFIG[review.verdict]
  const sb = review.score_breakdown

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      {/* Top bar */}
      <div className="sticky top-0 z-10 bg-[#161b22] border-b border-[#30363d]">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center gap-4">
          <Link
            to="/workspace"
            className="flex items-center gap-1 text-[#8b949e] hover:text-[#e6edf3] text-sm transition-colors"
          >
            <ArrowLeft size={16} />
            Back to workspace
          </Link>
          <Link
            to="/dashboard"
            className="text-[#8b949e] hover:text-[#e6edf3] text-sm transition-colors"
          >
            Dashboard
          </Link>
          <div className="flex-1" />
          <div className={`text-2xl font-bold ${scoreColor(review.overall_score)}`}>
            {review.overall_score}
            <span className="text-base font-normal text-[#8b949e]">/100</span>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Verdict banner */}
        <div
          className={`${verdict.bg} border ${verdict.border} rounded-xl p-5`}
        >
          <div className={`flex items-center gap-2 ${verdict.text} font-bold text-lg mb-2`}>
            {verdict.icon}
            {verdict.label}
          </div>
          <p className="text-[#e6edf3] text-sm leading-relaxed">{review.summary}</p>
        </div>

        {/* Score breakdown */}
        <section>
          <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-4">
            Score Breakdown
          </h2>
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 space-y-3">
            <ScoreBar label="Correctness" value={sb.correctness} max={30} />
            <ScoreBar label="Code Quality" value={sb.code_quality} max={25} />
            <ScoreBar label="Performance" value={sb.performance} max={20} />
            <ScoreBar label="Security" value={sb.security} max={15} />
            <ScoreBar label="Tests" value={sb.tests} max={10} />
          </div>
        </section>

        {/* Code review */}
        {review.inline_comments.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-4">
              Code Review
            </h2>
            <ReviewPanel review={review} />
          </section>
        )}

        {/* Learning resources */}
        {review.learning_resources.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-4">
              Learning Resources
            </h2>
            <div className="space-y-3">
              {review.learning_resources.slice(0, 3).map((r, i) => (
                <div
                  key={i}
                  className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 flex items-start justify-between gap-4"
                >
                  <div>
                    <p className="text-sm font-medium text-[#e6edf3] mb-1">{r.title}</p>
                    <p className="text-xs text-[#8b949e]">{r.why}</p>
                  </div>
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-[#58a6ff] hover:underline shrink-0"
                  >
                    Read →
                    <ExternalLink size={11} />
                  </a>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Architectural note */}
        {review.architectural_note && (
          <section>
            <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-3">
              Architectural Note
            </h2>
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4">
              <p className="text-sm text-[#e6edf3] leading-relaxed">
                {review.architectural_note}
              </p>
            </div>
          </section>
        )}

        {/* Footer */}
        <div className="pt-4 border-t border-[#30363d] flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-[#8b949e]">
            <Lock size={12} />
            Reviewed by ProofForge AI
          </div>
          {user && (
            <Link
              to={`/p/${user.github_login}`}
              className="text-sm text-[#58a6ff] hover:underline"
            >
              View Portfolio →
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

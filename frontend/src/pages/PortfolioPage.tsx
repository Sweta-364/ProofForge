import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Lock, ExternalLink, Loader, AlertCircle, Award } from 'lucide-react'
import { api } from '../lib/api'
import SkillRadar from '../components/SkillRadar'
import type { PortfolioCard } from '../types'

const DIFFICULTY_COLORS: Record<string, string> = {
  junior: 'bg-[#1a4731] text-[#3fb950]',
  mid: 'bg-[#3d2f00] text-[#d29922]',
  senior: 'bg-[#3d0c09] text-[#f85149]',
}

const TRACK_LABELS: Record<string, string> = {
  fullstack: 'Full-Stack',
  backend: 'Backend',
  frontend: 'Frontend',
  devops: 'DevOps',
}

export default function PortfolioPage() {
  const { githubLogin } = useParams<{ githubLogin: string }>()
  const [portfolio, setPortfolio] = useState<PortfolioCard | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!githubLogin) return
    api
      .getPortfolio(githubLogin)
      .then(setPortfolio)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Portfolio not found')
      })
      .finally(() => setIsLoading(false))
  }, [githubLogin])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center gap-3 text-[#8b949e]">
        <Loader size={24} className="animate-spin" />
        <span>Loading portfolio...</span>
      </div>
    )
  }

  if (error || !portfolio) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="bg-[#161b22] border border-[#da3633] rounded-xl p-8 max-w-md text-center">
          <AlertCircle size={40} className="text-[#f85149] mx-auto mb-4" />
          <h2 className="text-[#e6edf3] font-semibold text-lg mb-2">Portfolio Not Found</h2>
          <p className="text-[#8b949e] text-sm">{error ?? 'This portfolio does not exist yet.'}</p>
        </div>
      </div>
    )
  }

  const { user } = portfolio

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <div className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {/* Back link — only for signed-in visitors (the page itself is public) */}
        {localStorage.getItem('pf_token') && (
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1 text-sm text-[#8b949e] hover:text-[#e6edf3] transition-colors"
          >
            <ArrowLeft size={14} />
            Back to dashboard
          </Link>
        )}
        {/* Header */}
        <header className="flex items-start gap-5">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.github_login}
              className="w-20 h-20 rounded-full border-2 border-[#30363d]"
            />
          ) : (
            <div className="w-20 h-20 rounded-full bg-[#30363d] flex items-center justify-center text-2xl font-bold text-[#8b949e]">
              {(user.name ?? user.github_login)[0].toUpperCase()}
            </div>
          )}
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-[#e6edf3]">
              {user.name ?? user.github_login}
            </h1>
            <p className="text-[#8b949e] text-sm mt-0.5">@{user.github_login}</p>
            {user.career_track && (
              <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-[#0d2e4d] text-[#58a6ff] border border-[#1f6feb] rounded">
                {TRACK_LABELS[user.career_track] ?? user.career_track}
              </span>
            )}
            <div className="flex items-center gap-4 mt-3 text-sm text-[#8b949e]">
              <span>
                <strong className="text-[#e6edf3]">{portfolio.issues_resolved}</strong> issues resolved
              </span>
              <span>
                Avg score: <strong className="text-[#e6edf3]">{portfolio.avg_score.toFixed(1)}</strong>
              </span>
              <span>
                Top <strong className="text-[#58a6ff]">{portfolio.skill_percentile}%</strong>
              </span>
            </div>
          </div>
        </header>

        {/* Skill radar */}
        <section>
          <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-4">
            Skill Radar
          </h2>
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4">
            <SkillRadar skillRadar={portfolio.skill_radar} />
          </div>
        </section>

        {/* Highlights */}
        {portfolio.highlights.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-4">
              Highlights
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {portfolio.highlights.slice(0, 3).map((h, i) => (
                <div
                  key={i}
                  className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 text-center"
                >
                  <p className="text-xl font-bold text-[#58a6ff]">{h.value}</p>
                  <p className="text-xs text-[#8b949e] mt-1">{h.metric}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Resolution log */}
        {portfolio.resolution_log.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-[#8b949e] uppercase tracking-wider mb-4">
              Resolution Log
            </h2>
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#30363d]">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b949e] uppercase tracking-wider">
                      Problem
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b949e] uppercase tracking-wider">
                      Difficulty
                    </th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-[#8b949e] uppercase tracking-wider">
                      Score
                    </th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-[#8b949e] uppercase tracking-wider">
                      Time
                    </th>
                    <th className="text-right px-4 py-3 text-xs font-semibold text-[#8b949e] uppercase tracking-wider">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.resolution_log.map((entry, i) => (
                    <tr key={i} className="border-b border-[#21262d] last:border-0 hover:bg-[#1c2128]">
                      <td className="px-4 py-3 text-[#e6edf3]">{entry.problem_title}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded font-medium ${DIFFICULTY_COLORS[entry.difficulty] ?? 'bg-[#1c2128] text-[#8b949e]'}`}
                        >
                          {entry.difficulty}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-[#3fb950]">
                        {entry.score}
                      </td>
                      <td className="px-4 py-3 text-right text-[#8b949e] text-xs">
                        {entry.time_taken_mins != null ? `${entry.time_taken_mins}m` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-[#8b949e] text-xs">
                        {new Date(entry.solved_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Verification badge */}
        <section>
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#1a4731] border border-[#238636] flex items-center justify-center">
                <Lock size={18} className="text-[#3fb950]" />
              </div>
              <div>
                <p className="text-sm font-medium text-[#e6edf3]">Cryptographically Verified</p>
                <p className="text-xs text-[#8b949e]">
                  {portfolio.signature
                    ? 'Signed by ProofForge · Ed25519'
                    : 'Signature pending'}
                </p>
              </div>
            </div>
            <a
              href={`/api/v1/portfolio/${githubLogin}/verify`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-[#58a6ff] hover:underline"
            >
              Verify →
              <ExternalLink size={11} />
            </a>
          </div>

          {portfolio.signature && (
            <div className="mt-3 bg-[#161b22] border border-[#30363d] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Award size={14} className="text-[#d29922]" />
                <span className="text-xs text-[#8b949e]">Signature</span>
              </div>
              <code className="text-xs text-[#8b949e] break-all font-mono">
                {portfolio.signature}
              </code>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, Award, Flame, Loader, Zap } from 'lucide-react'
import { api } from '../lib/api'
import AppHeader from '../components/AppHeader'
import ActivityHeatmap from '../components/ActivityHeatmap'
import type { User, ActivityResponse, ProgressResponse } from '../types'

const TRACK_LABELS: Record<string, string> = {
  fullstack: 'Full-Stack',
  backend: 'Backend',
  frontend: 'Frontend',
  devops: 'DevOps',
}

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null)
  const [activity, setActivity] = useState<ActivityResponse | null>(null)
  const [progress, setProgress] = useState<ProgressResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [u, a, p] = await Promise.all([
        api.getMe(),
        api.getActivity(),
        api.getProgress(),
      ])
      setUser(u)
      setActivity(a)
      setProgress(p)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load profile')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center gap-3 text-[#8b949e]">
        <Loader size={24} className="animate-spin" />
        <span>Loading profile...</span>
      </div>
    )
  }

  if (error || !user || !activity || !progress) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="bg-[#161b22] border border-[#da3633] rounded-xl p-8 max-w-md text-center">
          <AlertCircle size={40} className="text-[#f85149] mx-auto mb-4" />
          <h2 className="text-[#e6edf3] font-semibold text-lg mb-2">Failed to load profile</h2>
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

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <AppHeader user={user} backTo={{ to: '/dashboard', label: 'Dashboard' }} />

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Identity card */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-6 flex items-center gap-5 flex-wrap">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt=""
              className="w-20 h-20 rounded-full border border-[#30363d]"
            />
          ) : (
            <div className="w-20 h-20 rounded-full bg-[#1c2128] border border-[#30363d]" />
          )}
          <div className="flex-1 min-w-[200px]">
            <h1 className="text-xl font-semibold">{user.name ?? user.github_login}</h1>
            <p className="text-sm text-[#8b949e]">@{user.github_login}</p>
            <p className="text-sm text-[#8b949e] mt-1">
              Track:{' '}
              <span className="text-[#e6edf3]">
                {user.career_track
                  ? TRACK_LABELS[user.career_track] ?? user.career_track
                  : 'not chosen'}
              </span>
            </p>
          </div>
          <Link
            to={`/p/${user.github_login}`}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c2128] hover:bg-[#30363d] border border-[#30363d] rounded text-xs font-medium transition-colors"
          >
            <Award size={13} />
            Public Portfolio
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Problems Solved', value: `${solvedCount}/${progress.problems.length}` },
            { label: 'Total Score', value: String(user.total_score) },
            {
              label: 'Current Streak',
              value: `${activity.current_streak} day${activity.current_streak === 1 ? '' : 's'}`,
              icon: <Flame size={16} className="text-[#f0883e]" />,
            },
            {
              label: 'Longest Streak',
              value: `${activity.longest_streak} day${activity.longest_streak === 1 ? '' : 's'}`,
              icon: <Zap size={16} className="text-[#d29922]" />,
            },
          ].map((s) => (
            <div key={s.label} className="bg-[#161b22] border border-[#30363d] rounded-xl p-4">
              <div className="flex items-center gap-2">
                {s.icon}
                <p className="text-2xl font-bold">{s.value}</p>
              </div>
              <p className="text-xs text-[#8b949e] mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Heatmap */}
        <section className="bg-[#161b22] border border-[#30363d] rounded-xl p-5">
          <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
            <h2 className="text-sm font-semibold">
              {activity.total_activity} activities in the past year
            </h2>
            <p className="text-xs text-[#8b949e]">
              Active days: {activity.total_active_days} · Max in one day:{' '}
              {activity.max_in_one_day}
            </p>
          </div>
          <ActivityHeatmap days={activity.days} />
        </section>
      </div>
    </div>
  )
}

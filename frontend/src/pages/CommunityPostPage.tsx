import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Loader, AlertCircle, Send } from 'lucide-react'
import { api, communityImageUrl } from '../lib/api'
import AppHeader from '../components/AppHeader'
import VoteButtons from '../components/VoteButtons'
import type { User, CommunityPost, CommunityAnswer } from '../types'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

function AuthorLine({ post }: { post: CommunityPost }) {
  return (
    <div className="flex items-center gap-2 text-xs text-[#8b949e]">
      {post.author.avatar_url ? (
        <img src={post.author.avatar_url} alt="" className="w-5 h-5 rounded-full" />
      ) : (
        <div className="w-5 h-5 rounded-full bg-[#30363d]" />
      )}
      <span>@{post.author.github_login}</span>
      <span>·</span>
      <span>{timeAgo(post.created_at)}</span>
    </div>
  )
}

export default function CommunityPostPage() {
  const { postId } = useParams<{ postId: string }>()
  const [user, setUser] = useState<User | null>(null)
  const [post, setPost] = useState<CommunityPost | null>(null)
  const [answers, setAnswers] = useState<CommunityAnswer[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [answerBody, setAnswerBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [answerError, setAnswerError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!postId) return
    setIsLoading(true)
    setError(null)
    try {
      const detail = await api.getCommunityPost(postId)
      setPost(detail.post)
      setAnswers(detail.answers)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load post')
    } finally {
      setIsLoading(false)
    }
  }, [postId])

  useEffect(() => {
    api.getMe().then(setUser).catch(() => setUser(null))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const submitAnswer = async () => {
    if (!postId || !answerBody.trim() || submitting) return
    setSubmitting(true)
    setAnswerError(null)
    try {
      const created = await api.addAnswer(postId, answerBody.trim())
      setAnswers((prev) => [...prev, created])
      setAnswerBody('')
    } catch (err: unknown) {
      setAnswerError(err instanceof Error ? err.message : 'Failed to add answer')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <AppHeader user={user} backTo={{ to: '/community', label: 'Community' }} />

      <main className="max-w-2xl mx-auto px-4 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center gap-3 py-12 text-[#8b949e]">
            <Loader size={22} className="animate-spin" />
            <span>Loading post...</span>
          </div>
        ) : error || !post ? (
          <div className="bg-[#161b22] border border-[#da3633] rounded-xl p-6 text-center">
            <AlertCircle size={32} className="text-[#f85149] mx-auto mb-3" />
            <p className="text-[#8b949e] text-sm mb-4">{error ?? 'Post not found'}</p>
            <button
              type="button"
              onClick={() => load()}
              className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-sm font-medium transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-5">
            {/* Post */}
            <div className="flex gap-3 bg-[#161b22] border border-[#30363d] rounded-xl p-4">
              <VoteButtons
                score={post.score}
                myVote={post.my_vote}
                onVote={(v) => api.votePost(post.id, v)}
              />
              <div className="min-w-0 flex-1">
                <AuthorLine post={post} />
                <h1 className="text-lg font-semibold mt-2 break-words">{post.title}</h1>
                {post.body && (
                  <p className="text-sm text-[#c9d1d9] mt-2 whitespace-pre-wrap break-words">
                    {post.body}
                  </p>
                )}
                {post.has_image && (
                  <img
                    src={communityImageUrl(post.id)}
                    alt=""
                    className="mt-3 max-h-96 rounded-lg border border-[#30363d]"
                  />
                )}
              </div>
            </div>

            {/* Answer composer */}
            <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 space-y-3">
              <h2 className="text-sm font-semibold">Your answer</h2>
              <textarea
                value={answerBody}
                onChange={(e) => setAnswerBody(e.target.value)}
                maxLength={2000}
                rows={3}
                placeholder="Share what you know..."
                className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#58a6ff] transition-colors resize-y placeholder:text-[#6e7681]"
              />
              {answerError && <p className="text-xs text-[#f85149]">{answerError}</p>}
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={submitAnswer}
                  disabled={!answerBody.trim() || submitting}
                  className="flex items-center gap-1.5 px-4 py-1.5 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <Loader size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                  {submitting ? 'Posting...' : 'Answer'}
                </button>
              </div>
            </div>

            {/* Answers */}
            <div>
              <h2 className="text-sm font-semibold text-[#8b949e] mb-3">
                {answers.length} {answers.length === 1 ? 'Answer' : 'Answers'}
              </h2>
              <div className="space-y-3">
                {answers.map((a) => (
                  <div
                    key={a.id}
                    className="flex gap-3 bg-[#161b22] border border-[#30363d] rounded-xl p-4"
                  >
                    <VoteButtons
                      score={a.score}
                      myVote={a.my_vote}
                      onVote={(v) => api.voteAnswer(a.id, v)}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-xs text-[#8b949e]">
                        {a.author.avatar_url ? (
                          <img
                            src={a.author.avatar_url}
                            alt=""
                            className="w-5 h-5 rounded-full"
                          />
                        ) : (
                          <div className="w-5 h-5 rounded-full bg-[#30363d]" />
                        )}
                        <span>@{a.author.github_login}</span>
                        <span>·</span>
                        <span>{timeAgo(a.created_at)}</span>
                      </div>
                      <p className="text-sm text-[#c9d1d9] mt-2 whitespace-pre-wrap break-words">
                        {a.body}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

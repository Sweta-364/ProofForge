import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Loader,
  AlertCircle,
  Search,
  ImagePlus,
  X,
  RefreshCw,
  MessageCircle,
  Send,
} from 'lucide-react'
import { api, communityImageUrl } from '../lib/api'
import AppHeader from '../components/AppHeader'
import VoteButtons from '../components/VoteButtons'
import type { User, CommunityPost, CommunityUserResult } from '../types'

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

export default function CommunityPage() {
  const [user, setUser] = useState<User | null>(null)
  const [posts, setPosts] = useState<CommunityPost[]>([])
  const [sort, setSort] = useState<'new' | 'top'>('new')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // composer state
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [posting, setPosting] = useState(false)
  const [composerError, setComposerError] = useState<string | null>(null)

  // user search state
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<CommunityUserResult[]>([])
  const [searching, setSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await api.listCommunityPosts(sort, 1)
      setPosts(res.posts)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load community')
    } finally {
      setIsLoading(false)
    }
  }, [sort])

  useEffect(() => {
    api.getMe().then(setUser).catch(() => setUser(null))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Debounced user search
  useEffect(() => {
    const q = query.trim()
    if (!q) {
      setResults([])
      setSearching(false)
      return
    }
    setSearching(true)
    const timer = setTimeout(async () => {
      try {
        const res = await api.searchCommunityUsers(q)
        setResults(res.users)
        setShowResults(true)
      } catch {
        setResults([])
      } finally {
        setSearching(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  // Close search dropdown on outside click
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const onPickImage = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setComposerError('Only image files are allowed')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setComposerError('Image too large (max 5 MB)')
      return
    }
    setComposerError(null)
    setImageFile(file)
    setImagePreview(URL.createObjectURL(file))
  }

  const clearImage = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImageFile(null)
    setImagePreview(null)
  }

  const submitPost = async () => {
    if (!title.trim() || posting) return
    setPosting(true)
    setComposerError(null)
    try {
      let imageKey: string | undefined
      let imageType: string | undefined
      if (imageFile) {
        const up = await api.uploadCommunityImage(imageFile)
        imageKey = up.image_key
        imageType = up.image_type
      }
      await api.createCommunityPost({
        title: title.trim(),
        body: body.trim(),
        image_key: imageKey,
        image_type: imageType,
      })
      setTitle('')
      setBody('')
      clearImage()
      await load()
    } catch (err: unknown) {
      setComposerError(err instanceof Error ? err.message : 'Failed to post')
    } finally {
      setPosting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <AppHeader user={user} />

      <main className="max-w-2xl mx-auto px-4 py-6 space-y-5">
        {/* User search */}
        <div className="relative" ref={searchRef}>
          <div className="flex items-center gap-2 bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-2 focus-within:border-[#58a6ff] transition-colors">
            <Search size={15} className="text-[#8b949e] shrink-0" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => results.length > 0 && setShowResults(true)}
              placeholder="Search people by GitHub username..."
              className="bg-transparent text-sm w-full outline-none placeholder:text-[#6e7681]"
            />
            {searching && <Loader size={14} className="animate-spin text-[#8b949e]" />}
          </div>
          {showResults && results.length > 0 && (
            <div className="absolute z-40 mt-1 w-full bg-[#1c2128] border border-[#30363d] rounded-lg shadow-lg py-1 max-h-72 overflow-auto">
              {results.map((u) => (
                <Link
                  key={u.github_login}
                  to={`/p/${u.github_login}`}
                  className="flex items-center gap-3 px-3 py-2 hover:bg-[#30363d] transition-colors"
                >
                  {u.avatar_url ? (
                    <img src={u.avatar_url} alt="" className="w-7 h-7 rounded-full" />
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-[#30363d]" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm truncate">{u.name ?? u.github_login}</p>
                    <p className="text-xs text-[#8b949e] truncate">@{u.github_login}</p>
                  </div>
                  <span className="text-xs text-[#8b949e] shrink-0">
                    {u.issues_resolved} solved
                  </span>
                </Link>
              ))}
            </div>
          )}
          {showResults && !searching && query.trim() && results.length === 0 && (
            <div className="absolute z-40 mt-1 w-full bg-[#1c2128] border border-[#30363d] rounded-lg shadow-lg px-3 py-2 text-sm text-[#8b949e]">
              No users found.
            </div>
          )}
        </div>

        {/* Composer */}
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-4 space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={300}
            placeholder="Ask a question or share a doubt..."
            className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#58a6ff] transition-colors placeholder:text-[#6e7681]"
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={5000}
            rows={3}
            placeholder="Add details (optional)..."
            className="w-full bg-[#0d1117] border border-[#30363d] rounded-lg px-3 py-2 text-sm outline-none focus:border-[#58a6ff] transition-colors resize-y placeholder:text-[#6e7681]"
          />
          {imagePreview && (
            <div className="relative inline-block">
              <img
                src={imagePreview}
                alt="preview"
                className="max-h-48 rounded-lg border border-[#30363d]"
              />
              <button
                type="button"
                onClick={clearImage}
                className="absolute top-1 right-1 bg-[#0d1117]/80 rounded-full p-1 hover:bg-[#0d1117]"
                aria-label="Remove image"
              >
                <X size={14} />
              </button>
            </div>
          )}
          {composerError && (
            <p className="text-xs text-[#f85149]">{composerError}</p>
          )}
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-[#e6edf3] cursor-pointer transition-colors">
              <ImagePlus size={15} />
              Add image
              <input type="file" accept="image/*" className="hidden" onChange={onPickImage} />
            </label>
            <button
              type="button"
              onClick={submitPost}
              disabled={!title.trim() || posting}
              className="flex items-center gap-1.5 px-4 py-1.5 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {posting ? <Loader size={14} className="animate-spin" /> : <Send size={14} />}
              {posting ? 'Posting...' : 'Post'}
            </button>
          </div>
        </div>

        {/* Sort + refresh */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 bg-[#161b22] border border-[#30363d] rounded-lg p-0.5">
            {(['new', 'top'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSort(s)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  sort === s
                    ? 'bg-[#30363d] text-[#e6edf3]'
                    : 'text-[#8b949e] hover:text-[#e6edf3]'
                }`}
              >
                {s === 'new' ? 'Newest' : 'Top'}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => load()}
            className="flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors"
          >
            <RefreshCw size={13} /> Refresh
          </button>
        </div>

        {/* Feed */}
        {isLoading ? (
          <div className="flex items-center justify-center gap-3 py-12 text-[#8b949e]">
            <Loader size={22} className="animate-spin" />
            <span>Loading community...</span>
          </div>
        ) : error ? (
          <div className="bg-[#161b22] border border-[#da3633] rounded-xl p-6 text-center">
            <AlertCircle size={32} className="text-[#f85149] mx-auto mb-3" />
            <p className="text-[#8b949e] text-sm mb-4">{error}</p>
            <button
              type="button"
              onClick={() => load()}
              className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-sm font-medium transition-colors"
            >
              Retry
            </button>
          </div>
        ) : posts.length === 0 ? (
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-8 text-center text-[#8b949e] text-sm">
            No posts yet. Be the first to ask something!
          </div>
        ) : (
          <div className="space-y-3">
            {posts.map((post) => (
              <div
                key={post.id}
                className="flex gap-3 bg-[#161b22] border border-[#30363d] rounded-xl p-4 hover:border-[#8b949e] transition-colors"
              >
                <VoteButtons
                  score={post.score}
                  myVote={post.my_vote}
                  onVote={(v) => api.votePost(post.id, v)}
                />
                <Link to={`/community/posts/${post.id}`} className="min-w-0 flex-1 group">
                  <div className="flex items-center gap-2 text-xs text-[#8b949e]">
                    {post.author.avatar_url ? (
                      <img
                        src={post.author.avatar_url}
                        alt=""
                        className="w-5 h-5 rounded-full"
                      />
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-[#30363d]" />
                    )}
                    <span>@{post.author.github_login}</span>
                    <span>·</span>
                    <span>{timeAgo(post.created_at)}</span>
                  </div>
                  <h3 className="text-sm font-semibold mt-1.5 group-hover:text-[#58a6ff] transition-colors break-words">
                    {post.title}
                  </h3>
                  {post.body && (
                    <p className="text-sm text-[#8b949e] mt-1 line-clamp-2 break-words">
                      {post.body}
                    </p>
                  )}
                  {post.has_image && (
                    <img
                      src={communityImageUrl(post.id)}
                      alt=""
                      className="mt-2 max-h-56 rounded-lg border border-[#30363d]"
                    />
                  )}
                  <div className="flex items-center gap-1.5 mt-2 text-xs text-[#8b949e]">
                    <MessageCircle size={13} />
                    {post.answer_count} {post.answer_count === 1 ? 'answer' : 'answers'}
                  </div>
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

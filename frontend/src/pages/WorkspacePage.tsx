import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import { Play, Send, Loader, AlertCircle, TerminalSquare } from 'lucide-react'
import { api } from '../lib/api'
import { submissionSocket } from '../lib/ws'
import AppHeader from '../components/AppHeader'
import FileTree from '../components/FileTree'
import TestOutput from '../components/TestOutput'
import TerminalPanel from '../components/TerminalPanel'
import type { User, Problem, TestRun } from '../types'

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

type RightTab = 'tests' | 'details'

const EXTENSION_LANGUAGES: Record<string, string> = {
  py: 'python',
  js: 'javascript',
  jsx: 'javascript',
  ts: 'typescript',
  tsx: 'typescript',
  html: 'html',
  css: 'css',
  json: 'json',
  yml: 'yaml',
  yaml: 'yaml',
  toml: 'ini',
  ini: 'ini',
  cfg: 'ini',
  conf: 'ini',
  sh: 'shell',
  sql: 'sql',
  md: 'markdown',
  txt: 'plaintext',
}

function languageForFile(path: string): string {
  const name = path.split('/').pop() ?? path
  if (name === 'Dockerfile') return 'dockerfile'
  const ext = name.includes('.') ? name.split('.').pop()!.toLowerCase() : ''
  return EXTENSION_LANGUAGES[ext] ?? 'plaintext'
}

function pickInitialFile(paths: string[]): string {
  const editable = paths.filter(
    (k) => !k.includes('test') && !k.includes('hidden') && !k.endsWith('__init__.py')
      && !k.endsWith('requirements.txt'),
  )
  return editable[0] ?? paths[0] ?? ''
}

const TERMINAL_MIN_H = 100
const TERMINAL_DEFAULT_H = 240

export default function WorkspacePage() {
  const navigate = useNavigate()
  const { slug } = useParams<{ slug: string }>()

  const [user, setUser] = useState<User | null>(null)
  const [problem, setProblem] = useState<Problem | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [files, setFiles] = useState<Map<string, string>>(new Map())
  const [activeFile, setActiveFile] = useState<string>('')
  const [isLoadingProblem, setIsLoadingProblem] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [testResults, setTestResults] = useState<TestRun | null>(null)
  const [isRunningTests, setIsRunningTests] = useState(false)

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submissionStatus, setSubmissionStatus] = useState<string>('')
  const [submitError, setSubmitError] = useState<string | null>(null)

  const [rightTab, setRightTab] = useState<RightTab>('tests')
  const [showTrackModal, setShowTrackModal] = useState(false)
  const [isSelectingTrack, setIsSelectingTrack] = useState(false)

  // ── Terminal state ──────────────────────────────────────────────────────────
  const [isTerminalOpen, setIsTerminalOpen] = useState(false)
  const [terminalHeight, setTerminalHeight] = useState(TERMINAL_DEFAULT_H)
  const isResizing = useRef(false)
  const resizeStartY = useRef(0)
  const resizeStartH = useRef(0)

  const token = localStorage.getItem('pf_token') ?? ''

  const handleResizeMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    isResizing.current = true
    resizeStartY.current = e.clientY
    resizeStartH.current = terminalHeight

    const onMove = (ev: MouseEvent) => {
      if (!isResizing.current) return
      // Dragging UP increases terminal height (delta is negative clientY diff)
      const delta = resizeStartY.current - ev.clientY
      const maxH = window.innerHeight * 0.75
      setTerminalHeight(Math.max(TERMINAL_MIN_H, Math.min(maxH, resizeStartH.current + delta)))
    }
    const onUp = () => {
      isResizing.current = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  const loadProblem = useCallback(async () => {
    setIsLoadingProblem(true)
    setLoadError(null)
    try {
      const { problem: p, session_id } = slug
        ? await api.getProblem(slug)
        : await api.getCurrentProblem()
      setProblem(p)
      setSessionId(session_id)
      const fileMap = new Map(Object.entries(p.files))
      setFiles(fileMap)
      setActiveFile(pickInitialFile([...fileMap.keys()]))
    } catch (err: unknown) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load problem')
    } finally {
      setIsLoadingProblem(false)
    }
  }, [slug])

  useEffect(() => {
    api.getMe()
      .then((u) => {
        setUser(u)
        if (!u.career_track) {
          setShowTrackModal(true)
          setIsLoadingProblem(false)
        } else {
          loadProblem()
        }
      })
      .catch(() => {
        navigate('/login', { replace: true })
      })
  }, [navigate, loadProblem])

  const handleSelectTrack = async (track: string) => {
    setIsSelectingTrack(true)
    try {
      const updated = await api.updateTrack(track)
      setUser(updated)
      setShowTrackModal(false)
      loadProblem()
    } catch {
      // ignore — user can retry
    } finally {
      setIsSelectingTrack(false)
    }
  }

  const handleRunTests = async () => {
    if (!sessionId) return
    setIsRunningTests(true)
    setRightTab('tests')
    try {
      const results = await api.runTests(sessionId, Object.fromEntries(files))
      setTestResults(results)
    } catch {
      setTestResults({
        status: 'error',
        passed: 0,
        failed: 0,
        total: 0,
        duration_ms: 0,
        tests: [],
      })
    } finally {
      setIsRunningTests(false)
    }
  }

  const handleSubmit = async () => {
    if (!sessionId) return
    const confirmed = window.confirm('Submit your solution for AI review?')
    if (!confirmed) return

    setIsSubmitting(true)
    setSubmitError(null)
    setSubmissionStatus('Submitting...')

    try {
      const { submission_id } = await api.submitSolution(sessionId, Object.fromEntries(files))

      submissionSocket.connect(submission_id, token, {
        onStatusUpdate: (_status, message) => {
          setSubmissionStatus(message)
        },
        onReviewComplete: (id) => {
          navigate(`/review/${id}`)
        },
        onError: (message) => {
          setIsSubmitting(false)
          setSubmitError(message)
          setSubmissionStatus('')
        },
      })
    } catch (err: unknown) {
      setIsSubmitting(false)
      setSubmitError(err instanceof Error ? err.message : 'Submission failed')
      setSubmissionStatus('')
    }
  }

  const handleEditorChange = (value: string | undefined) => {
    if (activeFile && value !== undefined) {
      setFiles((prev) => new Map(prev).set(activeFile, value))
    }
  }

  // ── Track selection modal ───────────────────────────────────────────────────
  if (showTrackModal) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center p-4">
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-8 max-w-md w-full">
          <h2 className="text-xl font-semibold text-[#e6edf3] mb-2">Choose your track</h2>
          <p className="text-[#8b949e] text-sm mb-6">
            This determines which problems and skills are highlighted in your portfolio.
          </p>
          <div className="grid grid-cols-2 gap-3">
            {TRACKS.map((track) => (
              <button
                key={track}
                disabled={isSelectingTrack}
                onClick={() => handleSelectTrack(track)}
                className="py-3 px-4 bg-[#1c2128] border border-[#30363d] hover:border-[#58a6ff] hover:bg-[#0d2e4d] rounded-lg text-[#e6edf3] text-sm font-medium transition-all disabled:opacity-50"
              >
                {TRACK_LABELS[track]}
              </button>
            ))}
          </div>
          {isSelectingTrack && (
            <div className="flex items-center justify-center gap-2 mt-4 text-[#8b949e] text-sm">
              <Loader size={14} className="animate-spin" />
              Saving...
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Loading / error ─────────────────────────────────────────────────────────
  if (isLoadingProblem) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center gap-3 text-[#8b949e]">
        <Loader size={24} className="animate-spin" />
        <span>Loading problem...</span>
      </div>
    )
  }

  if (loadError || !problem) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="bg-[#161b22] border border-[#da3633] rounded-xl p-8 max-w-md text-center">
          <AlertCircle size={40} className="text-[#f85149] mx-auto mb-4" />
          <h2 className="text-[#e6edf3] font-semibold text-lg mb-2">Failed to load problem</h2>
          <p className="text-[#8b949e] text-sm mb-6">{loadError}</p>
          <button
            onClick={() => loadProblem()}
            className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-sm font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // ── Main layout ─────────────────────────────────────────────────────────────
  return (
    <div className="h-screen flex flex-col bg-[#0d1117] text-[#e6edf3] overflow-hidden">
      {/* Header */}
      <AppHeader
        user={user}
        backTo={{ to: '/dashboard', label: 'Dashboard' }}
        center={
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-[#8b949e] text-xs truncate">{problem.title}</span>
            <span
              className={`text-xs px-1.5 py-0.5 rounded font-medium shrink-0 ${DIFFICULTY_COLORS[problem.difficulty] ?? 'bg-[#1c2128] text-[#8b949e]'}`}
            >
              {problem.difficulty}
            </span>
          </div>
        }
      />

      {/* 3-column workspace — shrinks when terminal is open */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left panel */}
        <aside className="w-[280px] shrink-0 bg-[#161b22] border-r border-[#30363d] flex flex-col overflow-hidden">
          <div className="px-3 py-2 text-xs font-semibold text-[#8b949e] uppercase tracking-wider border-b border-[#21262d]">
            Files
          </div>
          <div className="flex-1 overflow-y-auto min-h-0">
            <FileTree files={files} activeFile={activeFile} onSelect={setActiveFile} />
          </div>
          <div className="border-t border-[#30363d] p-3 overflow-y-auto" style={{ maxHeight: '40%' }}>
            <p className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider mb-2">
              Issue Description
            </p>
            <pre className="text-xs text-[#e6edf3] whitespace-pre-wrap break-words leading-relaxed">
              {problem.description}
            </pre>
          </div>
        </aside>

        {/* Center — editor only, no action bar */}
        <main className="flex-1 overflow-hidden" data-testid="editor-container">
          {activeFile ? (
            <Editor
              height="100%"
              path={activeFile}
              language={languageForFile(activeFile)}
              value={files.get(activeFile) ?? ''}
              onChange={handleEditorChange}
              theme="vs-dark"
              options={{
                fontSize: 14,
                minimap: { enabled: false },
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'off',
                tabSize: 4,
                insertSpaces: true,
                renderWhitespace: 'selection',
                padding: { top: 12 },
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-[#8b949e] text-sm">
              No file selected
            </div>
          )}
        </main>

        {/* Right panel */}
        <aside className="w-[320px] shrink-0 bg-[#161b22] border-l border-[#30363d] flex flex-col overflow-hidden">
          <div className="flex border-b border-[#30363d] shrink-0">
            {(['tests', 'details'] as RightTab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setRightTab(tab)}
                className={`flex-1 py-2.5 text-xs font-medium capitalize transition-colors ${
                  rightTab === tab
                    ? 'text-[#e6edf3] border-b-2 border-[#58a6ff]'
                    : 'text-[#8b949e] hover:text-[#e6edf3]'
                }`}
              >
                {tab === 'tests' ? 'Tests' : 'Issue Details'}
              </button>
            ))}
          </div>
          <div className="flex-1 overflow-hidden flex flex-col">
            {rightTab === 'tests' ? (
              <TestOutput results={testResults} isRunning={isRunningTests} />
            ) : (
              <div className="flex-1 overflow-y-auto p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${DIFFICULTY_COLORS[problem.difficulty] ?? 'bg-[#1c2128] text-[#8b949e]'}`}
                  >
                    {problem.difficulty}
                  </span>
                  <span className="text-xs text-[#8b949e]">{problem.category}</span>
                </div>
                <h3 className="text-sm font-semibold text-[#e6edf3] mb-2">{problem.title}</h3>
                <pre className="text-xs text-[#8b949e] whitespace-pre-wrap break-words leading-relaxed">
                  {problem.description}
                </pre>
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Drag-to-resize handle (only when terminal is open) */}
      {isTerminalOpen && (
        <div
          onMouseDown={handleResizeMouseDown}
          className="h-1.5 bg-[#21262d] hover:bg-[#58a6ff] cursor-ns-resize shrink-0 transition-colors"
          title="Drag to resize terminal"
        />
      )}

      {/* Terminal panel */}
      {isTerminalOpen && sessionId && (
        <div
          className="shrink-0 border-t border-[#30363d] overflow-hidden"
          style={{ height: terminalHeight }}
        >
          <TerminalPanel sessionId={sessionId} token={token} files={files} />
        </div>
      )}

      {/* Action bar — always at very bottom */}
      <div className="h-12 bg-[#161b22] border-t border-[#30363d] flex items-center gap-3 px-4 shrink-0">
        <button
          onClick={handleRunTests}
          disabled={isRunningTests || isSubmitting}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1c2128] hover:bg-[#30363d] border border-[#30363d] rounded text-xs font-medium text-[#e6edf3] transition-colors disabled:opacity-50"
        >
          {isRunningTests ? <Loader size={13} className="animate-spin" /> : <Play size={13} />}
          Run Tests
        </button>

        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#238636] hover:bg-[#2ea043] rounded text-xs font-medium text-white transition-colors disabled:opacity-50"
        >
          {isSubmitting ? <Loader size={13} className="animate-spin" /> : <Send size={13} />}
          Submit PR ↗
        </button>

        {isSubmitting && submissionStatus && (
          <span className="text-xs text-[#8b949e] flex items-center gap-1">
            <Loader size={11} className="animate-spin" />
            {submissionStatus}
          </span>
        )}

        {submitError && (
          <span className="text-xs text-[#f85149] flex items-center gap-1">
            <AlertCircle size={11} />
            {submitError}
          </span>
        )}

        <div className="flex-1" />

        {/* Terminal toggle */}
        <button
          onClick={() => setIsTerminalOpen((v) => !v)}
          disabled={!sessionId}
          title={isTerminalOpen ? 'Close terminal' : 'Open terminal'}
          className={`flex items-center gap-1.5 px-3 py-1.5 border rounded text-xs font-medium transition-colors disabled:opacity-40 ${
            isTerminalOpen
              ? 'bg-[#1c2128] border-[#58a6ff] text-[#58a6ff]'
              : 'bg-[#1c2128] border-[#30363d] text-[#8b949e] hover:text-[#e6edf3] hover:border-[#58a6ff]'
          }`}
        >
          <TerminalSquare size={13} />
          Terminal
        </button>
      </div>
    </div>
  )
}

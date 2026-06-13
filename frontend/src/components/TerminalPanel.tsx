import { useEffect, useRef, useState } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { RefreshCw, Github } from 'lucide-react'
import { TerminalWebSocket, type TerminalReadyInfo } from '../lib/terminal-ws'

interface Props {
  sessionId: string
  token: string
  files: Map<string, string>
}

type Status = 'connecting' | 'ready' | 'error' | 'closed'

const STATUS_DOT: Record<Status, string> = {
  connecting: 'bg-[#d29922]',
  ready:      'bg-[#3fb950]',
  error:      'bg-[#f85149]',
  closed:     'bg-[#6e7681]',
}

export default function TerminalPanel({ sessionId, token, files }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef      = useRef<Terminal | null>(null)
  const fitRef       = useRef<FitAddon | null>(null)
  const wsRef        = useRef<TerminalWebSocket | null>(null)
  const filesRef     = useRef(files)

  const [status, setStatus]           = useState<Status>('connecting')
  const [readyInfo, setReadyInfo]     = useState<TerminalReadyInfo | null>(null)

  // Keep files ref current so sync button always has latest
  useEffect(() => { filesRef.current = files }, [files])

  useEffect(() => {
    if (!containerRef.current) return

    const term = new Terminal({
      cursorBlink:  true,
      convertEol:   false,
      scrollback:   5000,
      theme: {
        background:         '#0d1117',
        foreground:         '#e6edf3',
        cursor:             '#58a6ff',
        selectionBackground:'#264f78',
        black:              '#0d1117',
        red:                '#f85149',
        green:              '#3fb950',
        yellow:             '#d29922',
        blue:               '#58a6ff',
        magenta:            '#bc8cff',
        cyan:               '#39c5cf',
        white:              '#b1bac4',
        brightBlack:        '#6e7681',
        brightRed:          '#ff7b72',
        brightGreen:        '#56d364',
        brightYellow:       '#e3b341',
        brightBlue:         '#79c0ff',
        brightMagenta:      '#d2a8ff',
        brightCyan:         '#56d4dd',
        brightWhite:        '#ffffff',
      },
      fontFamily: '"Cascadia Code","Fira Code",Menlo,"Courier New",monospace',
      fontSize:    13,
      lineHeight:  1.2,
    })

    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(containerRef.current)
    fit.fit()

    termRef.current = term
    fitRef.current  = fit

    const ws = new TerminalWebSocket()
    wsRef.current = ws

    ws.connect(sessionId, token, {
      onReady: (info) => {
        setStatus('ready')
        setReadyInfo(info)
        // Fit after status bar re-renders
        requestAnimationFrame(() => {
          try {
            fit.fit()
            ws.sendResize(term.cols, term.rows)
          } catch { /* disposed */ }
        })
      },
      onOutput:  (data) => term.write(data),
      onError:   (msg)  => {
        setStatus('error')
        term.writeln(`\r\n\x1b[31mError: ${msg}\x1b[0m`)
      },
      onClose:   ()     => setStatus('closed'),
    })

    // Seed workspace with current editor files
    ws.sync(Object.fromEntries(filesRef.current))

    // Bridge keystrokes → WebSocket
    const disposable = term.onData((data) => ws.sendInput(data))

    // Resize terminal when the panel size changes
    const ro = new ResizeObserver(() => {
      try {
        fit.fit()
        ws.sendResize(term.cols, term.rows)
      } catch { /* disposed */ }
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      disposable.dispose()
      ws.disconnect()
      term.dispose()
      termRef.current = null
      fitRef.current  = null
      wsRef.current   = null
    }
  }, [sessionId, token]) // reconnect only when session/token changes

  const handleSync = () => {
    if (!wsRef.current) return
    wsRef.current.sync(Object.fromEntries(filesRef.current))
    termRef.current?.writeln('\r\n\x1b[32m[Files synced from editor]\x1b[0m')
  }

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Tab / status bar */}
      <div className="flex items-center gap-2 h-8 px-3 bg-[#161b22] border-b border-[#30363d] shrink-0">
        <span className="text-xs font-medium text-[#e6edf3]">Terminal</span>
        <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_DOT[status]}`} />

        {readyInfo?.gitConfigured && (
          <span className="flex items-center gap-1 text-xs text-[#3fb950]">
            <Github size={11} />
            git ready ({readyInfo.githubLogin})
          </span>
        )}
        {readyInfo && !readyInfo.gitConfigured && (
          <span className="text-xs text-[#8b949e]">git not configured (re-login to enable)</span>
        )}

        <div className="flex-1" />

        {status === 'closed' || status === 'error' ? (
          <span className="text-xs text-[#f85149]">
            {status === 'closed' ? 'Disconnected' : 'Error'}
          </span>
        ) : null}

        <button
          onClick={handleSync}
          disabled={status !== 'ready'}
          title="Sync editor files into terminal workspace"
          className="flex items-center gap-1 text-xs text-[#8b949e] hover:text-[#e6edf3] disabled:opacity-40 transition-colors"
        >
          <RefreshCw size={11} />
          Sync files
        </button>
      </div>

      {/* xterm.js mount point */}
      <div
        ref={containerRef}
        className="flex-1 min-h-0 overflow-hidden"
        style={{ padding: '4px 2px' }}
      />
    </div>
  )
}

const WS_BASE =
  (import.meta.env.VITE_API_WS_URL as string | undefined) ?? 'ws://localhost:8000'

export interface TerminalReadyInfo {
  githubLogin: string
  gitConfigured: boolean
  cwd: string
}

export interface TerminalCallbacks {
  onReady: (info: TerminalReadyInfo) => void
  onOutput: (data: string) => void
  onError: (message: string) => void
  onClose: () => void
}

export class TerminalWebSocket {
  private ws: WebSocket | null = null
  private callbacks: TerminalCallbacks | null = null
  private pendingSync: Record<string, string> | null = null

  connect(sessionId: string, token: string, callbacks: TerminalCallbacks): void {
    this.callbacks = callbacks
    const url = `${WS_BASE}/api/v1/ws/terminal/${encodeURIComponent(sessionId)}?token=${encodeURIComponent(token)}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      if (this.pendingSync !== null) {
        this._sendRaw({ type: 'sync', files: this.pendingSync })
        this.pendingSync = null
      }
    }

    this.ws.onmessage = (ev) => {
      let msg: Record<string, unknown>
      try {
        msg = JSON.parse(ev.data as string) as Record<string, unknown>
      } catch {
        return
      }
      switch (msg.type) {
        case 'ready':
          this.callbacks?.onReady({
            githubLogin: String(msg.github_login ?? ''),
            gitConfigured: Boolean(msg.git_configured),
            cwd: String(msg.cwd ?? ''),
          })
          break
        case 'output':
          this.callbacks?.onOutput(String(msg.data ?? ''))
          break
        case 'error':
          this.callbacks?.onError(String(msg.message ?? 'Unknown error'))
          break
      }
    }

    this.ws.onclose = () => this.callbacks?.onClose()
    this.ws.onerror = () => this.callbacks?.onError('WebSocket connection failed')
  }

  /** Send current editor files to seed / refresh the server workspace. */
  sync(files: Record<string, string>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this._sendRaw({ type: 'sync', files })
    } else {
      this.pendingSync = files
    }
  }

  sendInput(data: string): void {
    this._sendRaw({ type: 'input', data })
  }

  sendResize(cols: number, rows: number): void {
    this._sendRaw({ type: 'resize', cols, rows })
  }

  disconnect(): void {
    this.ws?.close()
    this.ws = null
    this.callbacks = null
    this.pendingSync = null
  }

  private _sendRaw(obj: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj))
    }
  }
}

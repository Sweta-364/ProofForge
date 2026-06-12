interface WsCallbacks {
  onStatusUpdate: (status: string, message: string) => void
  onReviewComplete: (submissionId: string, score: number, verdict: string, reviewId: string) => void
  onError: (message: string, code: string) => void
}

interface WsMessage {
  type: 'status_update' | 'review_complete' | 'error'
  status?: string
  message?: string
  submission_id?: string
  score?: number
  verdict?: string
  review_id?: string
  code?: string
}

class SubmissionSocket {
  private ws: WebSocket | null = null
  private reconnectAttempted = false

  connect(submissionId: string, token: string, callbacks: WsCallbacks): void {
    this.disconnect()
    this.reconnectAttempted = false
    this._open(submissionId, token, callbacks)
  }

  private _open(submissionId: string, token: string, callbacks: WsCallbacks): void {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/v1/ws/submissions/${submissionId}?token=${encodeURIComponent(token)}`

    this.ws = new WebSocket(url)

    this.ws.onmessage = (event: MessageEvent<string>) => {
      let msg: WsMessage
      try {
        msg = JSON.parse(event.data) as WsMessage
      } catch {
        return
      }

      if (msg.type === 'status_update') {
        callbacks.onStatusUpdate(msg.status ?? '', msg.message ?? '')
      } else if (msg.type === 'review_complete') {
        callbacks.onReviewComplete(
          msg.submission_id ?? submissionId,
          msg.score ?? 0,
          msg.verdict ?? 'major_revisions',
          msg.review_id ?? '',
        )
      } else if (msg.type === 'error') {
        callbacks.onError(msg.message ?? 'Unknown error', msg.code ?? 'unknown')
      }
    }

    this.ws.onclose = (event: CloseEvent) => {
      // Auth/ownership errors — do not reconnect
      if (event.code === 4001 || event.code === 4003 || event.wasClean) return
      if (!this.reconnectAttempted) {
        this.reconnectAttempted = true
        setTimeout(() => this._open(submissionId, token, callbacks), 1500)
      }
    }

    this.ws.onerror = () => {
      // Connection errors surface via onclose
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.onclose = null
      this.ws.close()
      this.ws = null
    }
  }
}

export const submissionSocket = new SubmissionSocket()

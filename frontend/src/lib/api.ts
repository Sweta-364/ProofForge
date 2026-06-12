import type {
  User,
  CurrentProblemResponse,
  TestRun,
  Submission,
  Review,
  PortfolioCard,
  ProgressResponse,
  ActivityResponse,
} from '../types'

class ApiClient {
  private readonly baseUrl = '/api/v1'

  private getToken(): string | null {
    return localStorage.getItem('pf_token')
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }

    const res = await fetch(`${this.baseUrl}${path}`, { ...options, headers })

    if (res.status === 401) {
      localStorage.removeItem('pf_token')
      window.location.href = '/login'
      throw new Error('Unauthorized — redirecting to login')
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error((body as { detail?: string }).detail ?? res.statusText)
    }

    return res.json() as Promise<T>
  }

  /** DEV-ONLY: login bypass for local testing (backend returns 404 unless DEV_MODE=true). */
  devLogin(): Promise<{ access_token: string; token_type: string; github_login: string }> {
    return this.request<{ access_token: string; token_type: string; github_login: string }>(
      '/auth/dev-login',
      { method: 'POST' },
    )
  }

  getMe(): Promise<User> {
    return this.request<User>('/users/me')
  }

  getProgress(): Promise<ProgressResponse> {
    return this.request<ProgressResponse>('/users/me/progress')
  }

  logout(): Promise<{ message: string }> {
    return this.request<{ message: string }>('/auth/logout', { method: 'POST' })
  }

  updateTrack(track: string): Promise<User> {
    return this.request<User>('/users/me/track', {
      method: 'PUT',
      body: JSON.stringify({ track }),
    })
  }

  getCurrentProblem(): Promise<CurrentProblemResponse> {
    return this.request<CurrentProblemResponse>('/problems/current')
  }

  getProblem(slug: string): Promise<CurrentProblemResponse> {
    return this.request<CurrentProblemResponse>(`/problems/${encodeURIComponent(slug)}`)
  }

  getActivity(): Promise<ActivityResponse> {
    return this.request<ActivityResponse>('/users/me/activity')
  }

  runTests(sessionId: string, files: Record<string, string>): Promise<TestRun> {
    return this.request<TestRun>(`/sessions/${sessionId}/run-tests`, {
      method: 'POST',
      body: JSON.stringify({ files }),
    })
  }

  submitSolution(
    sessionId: string,
    files: Record<string, string>,
  ): Promise<{ submission_id: string; status: string }> {
    return this.request<{ submission_id: string; status: string }>('/submissions', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, files }),
    })
  }

  getSubmission(id: string): Promise<Submission> {
    return this.request<Submission>(`/submissions/${id}`)
  }

  getReview(submissionId: string): Promise<Review> {
    return this.request<Review>(`/submissions/${submissionId}/review`)
  }

  getPortfolio(githubLogin: string): Promise<PortfolioCard> {
    return this.request<PortfolioCard>(`/portfolio/${githubLogin}`)
  }
}

export const api = new ApiClient()

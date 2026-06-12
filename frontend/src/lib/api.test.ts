import { describe, it, expect, beforeEach, vi } from 'vitest'
import { api } from './api'

// Reset state between tests
beforeEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

// ── helpers ────────────────────────────────────────────────────────────────────

function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      status,
      ok: status >= 200 && status < 300,
      json: () => Promise.resolve(body),
      statusText: status === 200 ? 'OK' : 'Error',
    } as Response),
  )
}

// ── tests ──────────────────────────────────────────────────────────────────────

describe('api.getMe', () => {
  it('returns User when called with a valid token', async () => {
    localStorage.setItem('pf_token', 'valid-test-token')
    const mockUser = {
      id: 'abc123',
      github_login: 'testuser',
      name: 'Test User',
      email: 'test@example.com',
      avatar_url: null,
      career_track: 'backend',
      current_difficulty: 'junior',
      total_score: 0,
      issues_resolved: 0,
    }
    mockFetch(200, mockUser)

    const user = await api.getMe()
    expect(user.github_login).toBe('testuser')
    expect(user.career_track).toBe('backend')
  })

  it('sends the Authorization header when a token is present', async () => {
    const token = 'bearer-test-token'
    localStorage.setItem('pf_token', token)
    mockFetch(200, { id: '1', github_login: 'u', name: null, email: null, avatar_url: null, career_track: null, current_difficulty: 'junior', total_score: 0, issues_resolved: 0 })

    await api.getMe()

    const fetchMock = vi.mocked(globalThis.fetch)
    const [, options] = fetchMock.mock.calls[0]
    const headers = (options as RequestInit).headers as Record<string, string>
    expect(headers['Authorization']).toBe(`Bearer ${token}`)
  })
})

describe('api request — 401 handling', () => {
  it('clears pf_token from localStorage on 401 response', async () => {
    localStorage.setItem('pf_token', 'expired-token')
    mockFetch(401, { detail: 'Unauthorized' })

    // The handler also calls window.location.href = '/login' which throws in jsdom;
    // suppress the navigation error and just verify the token is cleared.
    try {
      await api.getMe()
    } catch {
      // expected
    }

    expect(localStorage.getItem('pf_token')).toBeNull()
  })
})

describe('api.runTests', () => {
  it('sends the correct payload to the run-tests endpoint', async () => {
    localStorage.setItem('pf_token', 'tok')
    const fakeResults = {
      status: 'completed',
      passed: 2,
      failed: 0,
      total: 2,
      duration_ms: 500,
      tests: [],
    }
    mockFetch(200, fakeResults)

    const files = { 'starter/__init__.py': '', 'starter/main.py': 'from fastapi import FastAPI\napp = FastAPI()\n' }
    const sessionId = 'session-uuid-001'

    const results = await api.runTests(sessionId, files)
    expect(results.passed).toBe(2)
    expect(results.status).toBe('completed')

    const fetchMock = vi.mocked(globalThis.fetch)
    const [url, options] = fetchMock.mock.calls[0]
    expect(String(url)).toContain(`/sessions/${sessionId}/run-tests`)
    expect((options as RequestInit).method).toBe('POST')

    const body = JSON.parse((options as RequestInit).body as string) as { files: Record<string, string> }
    expect(body.files).toEqual(files)
  })
})

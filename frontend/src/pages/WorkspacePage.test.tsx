import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import WorkspacePage from './WorkspacePage'

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('@monaco-editor/react', () => ({
  default: ({
    value,
    onChange,
  }: {
    value?: string
    onChange?: (val: string | undefined) => void
  }) => (
    <textarea
      data-testid="monaco-editor"
      value={value ?? ''}
      onChange={(e) => onChange?.(e.target.value)}
      readOnly={!onChange}
    />
  ),
}))

// Keep stable mock function references for assertions
const mockGetMe = vi.fn()
const mockGetCurrentProblem = vi.fn()
const mockRunTests = vi.fn()
const mockSubmitSolution = vi.fn()
const mockUpdateTrack = vi.fn()

vi.mock('../lib/api', () => ({
  api: {
    getMe: () => mockGetMe() as unknown,
    getCurrentProblem: () => mockGetCurrentProblem() as unknown,
    runTests: (sessionId: string, files: Record<string, string>) =>
      mockRunTests(sessionId, files) as unknown,
    submitSolution: (sessionId: string, files: Record<string, string>) =>
      mockSubmitSolution(sessionId, files) as unknown,
    updateTrack: (track: string) => mockUpdateTrack(track) as unknown,
  },
}))

vi.mock('../lib/ws', () => ({
  submissionSocket: { connect: vi.fn(), disconnect: vi.fn() },
}))

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_USER = {
  id: 'user-1',
  github_login: 'devuser',
  name: 'Dev User',
  email: 'dev@example.com',
  avatar_url: null,
  career_track: 'backend',
  current_difficulty: 'junior',
  total_score: 0,
  issues_resolved: 0,
}

const MOCK_PROBLEM_RESPONSE = {
  session_id: 'session-001',
  problem: {
    id: 'prob-1',
    slug: '001-cors-fix',
    title: 'Fix CORS',
    description: 'Add CORSMiddleware to the FastAPI app.',
    difficulty: 'junior' as const,
    category: 'api',
    language: 'python',
    files: {
      'starter/__init__.py': '',
      'starter/main.py': 'from fastapi import FastAPI\napp = FastAPI()\n',
    },
  },
}

const MOCK_TEST_RESULTS = {
  status: 'completed' as const,
  passed: 0,
  failed: 2,
  total: 2,
  duration_ms: 400,
  tests: [
    { name: 'test_cors_headers_present', status: 'failed' as const, duration_ms: 200, error: 'AssertionError' },
    { name: 'test_get_users_with_cors', status: 'failed' as const, duration_ms: 200, error: 'AssertionError' },
  ],
}

function renderWorkspace() {
  return render(
    <MemoryRouter>
      <WorkspacePage />
    </MemoryRouter>,
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  localStorage.setItem('pf_token', 'test-token')
  mockGetMe.mockResolvedValue(MOCK_USER)
  mockGetCurrentProblem.mockResolvedValue(MOCK_PROBLEM_RESPONSE)
  mockRunTests.mockResolvedValue(MOCK_TEST_RESULTS)
})

describe('WorkspacePage', () => {
  it('renders Monaco Editor after problem loads', async () => {
    renderWorkspace()

    // Initially shows loading indicator
    expect(screen.getByText(/loading problem/i)).toBeInTheDocument()

    // After data loads the editor renders
    await waitFor(() => {
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument()
    })
  })

  it('shows the problem title in the header after load', async () => {
    renderWorkspace()
    await waitFor(() => {
      expect(screen.getByText('Fix CORS')).toBeInTheDocument()
    })
  })

  it('Run Tests button calls api.runTests with current files', async () => {
    renderWorkspace()
    await waitFor(() => screen.getByTestId('monaco-editor'))

    const runBtn = screen.getByRole('button', { name: /run tests/i })
    fireEvent.click(runBtn)

    await waitFor(() => {
      expect(mockRunTests).toHaveBeenCalledWith(
        'session-001',
        expect.objectContaining({ 'starter/main.py': expect.any(String) }),
      )
    })
  })

  it('displays test results in right panel after run completes', async () => {
    renderWorkspace()
    await waitFor(() => screen.getByTestId('monaco-editor'))

    fireEvent.click(screen.getByRole('button', { name: /run tests/i }))

    await waitFor(() => {
      expect(screen.getByText(/0\/2 passed/i)).toBeInTheDocument()
    })
  })

  it('shows track selection modal when user has no career_track', async () => {
    mockGetMe.mockResolvedValue({ ...MOCK_USER, career_track: null })
    renderWorkspace()

    await waitFor(() => {
      expect(screen.getByText(/choose your track/i)).toBeInTheDocument()
    })
    expect(screen.getByText('Full-Stack')).toBeInTheDocument()
    expect(screen.getByText('Backend')).toBeInTheDocument()
  })
})

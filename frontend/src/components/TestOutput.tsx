import { useState } from 'react'
import { CheckCircle, XCircle, Clock, ChevronDown, ChevronRight, Loader } from 'lucide-react'
import type { TestRun, TestCase } from '../types'

interface TestCaseRowProps {
  test: TestCase
}

function TestCaseRow({ test }: TestCaseRowProps) {
  const [expanded, setExpanded] = useState(false)
  const passed = test.status === 'passed'

  return (
    <div className="border-b border-[#21262d] last:border-0">
      <button
        className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-[#1c2128] transition-colors"
        onClick={() => !passed && test.error && setExpanded(!expanded)}
      >
        {passed ? (
          <CheckCircle size={14} className="shrink-0 text-[#3fb950]" />
        ) : (
          <XCircle size={14} className="shrink-0 text-[#f85149]" />
        )}
        <span className={`flex-1 text-xs truncate ${passed ? 'text-[#e6edf3]' : 'text-[#f85149]'}`}>
          {test.name}
        </span>
        <span className="text-xs text-[#8b949e] shrink-0 flex items-center gap-1">
          <Clock size={11} />
          {test.duration_ms}ms
        </span>
        {!passed && test.error && (
          expanded ? <ChevronDown size={12} className="shrink-0 text-[#8b949e]" /> : <ChevronRight size={12} className="shrink-0 text-[#8b949e]" />
        )}
      </button>
      {expanded && test.error && (
        <div className="px-3 pb-2">
          <pre className="text-xs text-[#f85149] bg-[#1c2128] rounded p-2 overflow-x-auto truncate-3 whitespace-pre-wrap break-all">
            {test.error}
          </pre>
        </div>
      )}
    </div>
  )
}

interface TestOutputProps {
  results: TestRun | null
  isRunning: boolean
}

export default function TestOutput({ results, isRunning }: TestOutputProps) {
  if (isRunning) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-3 text-[#8b949e]">
        <Loader size={24} className="animate-spin" />
        <span className="text-sm">Running tests...</span>
      </div>
    )
  }

  if (!results) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-2 text-[#8b949e] px-4 text-center">
        <CheckCircle size={32} className="text-[#30363d]" />
        <p className="text-sm">Click <strong className="text-[#e6edf3]">Run Tests</strong> to see results</p>
        <p className="text-xs">Results will show which tests pass or fail</p>
      </div>
    )
  }

  const allPassed = results.failed === 0 && results.status === 'completed'
  const passColor = allPassed ? 'text-[#3fb950]' : results.failed > 0 ? 'text-[#f85149]' : 'text-[#8b949e]'

  if (results.status === 'timeout') {
    return (
      <div className="flex flex-col items-center justify-center flex-1 gap-2 px-4 text-center">
        <XCircle size={32} className="text-[#d29922]" />
        <p className="text-sm text-[#d29922] font-medium">Execution timed out</p>
        <p className="text-xs text-[#8b949e]">Code took longer than 30 seconds</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Summary bar */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#161b22] border-b border-[#30363d]">
        <span className={`text-sm font-semibold ${passColor}`}>
          {results.passed}/{results.total} passed
        </span>
        <div className="flex items-center gap-3 text-xs text-[#8b949e]">
          {results.failed > 0 && (
            <span className="text-[#f85149]">{results.failed} failed</span>
          )}
          <span className="flex items-center gap-1">
            <Clock size={11} />
            {results.duration_ms}ms
          </span>
        </div>
      </div>
      {/* Progress bar */}
      <div className="h-1 bg-[#21262d]">
        <div
          className={`h-full transition-all ${allPassed ? 'bg-[#238636]' : 'bg-[#f85149]'}`}
          style={{ width: `${results.total ? (results.passed / results.total) * 100 : 0}%` }}
        />
      </div>
      {/* Test list */}
      <div className="flex-1 overflow-y-auto">
        {results.tests.map((test, i) => (
          <TestCaseRow key={i} test={test} />
        ))}
      </div>
    </div>
  )
}

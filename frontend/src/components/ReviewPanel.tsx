import type { Review, InlineComment } from '../types'

interface SeverityBadgeProps {
  severity: InlineComment['severity']
}

function SeverityBadge({ severity }: SeverityBadgeProps) {
  const styles: Record<InlineComment['severity'], string> = {
    praise: 'bg-[#1a4731] text-[#3fb950] border border-[#238636]',
    info: 'bg-[#0d2e4d] text-[#58a6ff] border border-[#1f6feb]',
    warning: 'bg-[#3d2f00] text-[#d29922] border border-[#9e6a03]',
    error: 'bg-[#3d0c09] text-[#f85149] border border-[#da3633]',
  }
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium uppercase ${styles[severity]}`}>
      {severity}
    </span>
  )
}

interface CommentGroupProps {
  file: string
  comments: InlineComment[]
  codeSnapshot: Record<string, string>
}

function CommentGroup({ file, comments, codeSnapshot }: CommentGroupProps) {
  const fileContent = codeSnapshot[file] ?? ''
  const lines = fileContent.split('\n')

  // Determine which lines to show: commented lines ± 3 context lines
  const commentedLines = new Set(comments.map((c) => c.line))
  const visibleLines = new Set<number>()
  for (const lineNum of commentedLines) {
    for (let i = Math.max(1, lineNum - 2); i <= Math.min(lines.length, lineNum + 2); i++) {
      visibleLines.add(i)
    }
  }
  const sortedVisible = [...visibleLines].sort((a, b) => a - b)

  // Group comments by line for O(1) lookup
  const commentsByLine = new Map<number, InlineComment[]>()
  for (const c of comments) {
    const existing = commentsByLine.get(c.line) ?? []
    existing.push(c)
    commentsByLine.set(c.line, existing)
  }

  return (
    <div className="border border-[#30363d] rounded overflow-hidden">
      {/* File header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-[#161b22] border-b border-[#30363d]">
        <span className="text-xs font-mono text-[#58a6ff]">{file}</span>
        <span className="ml-auto text-xs text-[#8b949e]">{comments.length} comment{comments.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Code + comments */}
      <div className="bg-[#0d1117]">
        {sortedVisible.length === 0 ? (
          // No code snapshot — just show comments as a flat list
          <div className="divide-y divide-[#21262d]">
            {comments.map((c, i) => (
              <div key={i} className="px-3 py-2 flex gap-2">
                <span className="text-xs text-[#8b949e] w-8 shrink-0">L{c.line}</span>
                <SeverityBadge severity={c.severity} />
                <p className="text-xs text-[#e6edf3] flex-1">{c.comment}</p>
              </div>
            ))}
          </div>
        ) : (
          <>
            {sortedVisible.map((lineNum, idx) => {
              const prevLineNum = sortedVisible[idx - 1]
              const showEllipsis = prevLineNum !== undefined && lineNum > prevLineNum + 1
              const lineComments = commentsByLine.get(lineNum)
              const isCommentedLine = commentedLines.has(lineNum)
              return (
                <div key={lineNum}>
                  {showEllipsis && (
                    <div className="px-3 py-0.5 text-xs text-[#8b949e] bg-[#0d1117] font-mono">
                      ...
                    </div>
                  )}
                  <div className={`font-mono text-xs flex ${isCommentedLine ? 'bg-[#1c2128]' : ''}`}>
                    <span className="w-10 text-right pr-3 text-[#8b949e] select-none shrink-0 py-0.5">
                      {lineNum}
                    </span>
                    <span className="flex-1 py-0.5 pr-3 text-[#e6edf3] whitespace-pre overflow-x-auto">
                      {lines[lineNum - 1]}
                    </span>
                  </div>
                  {lineComments && lineComments.map((c, i) => (
                    <div key={i} className="flex gap-2 px-3 py-2 bg-[#0d1117] border-t border-[#30363d]">
                      <div className="w-10 shrink-0" />
                      <SeverityBadge severity={c.severity} />
                      <p className="text-xs text-[#e6edf3] flex-1 leading-relaxed">{c.comment}</p>
                    </div>
                  ))}
                </div>
              )
            })}
          </>
        )}
      </div>
    </div>
  )
}

interface ReviewPanelProps {
  review: Review
}

export default function ReviewPanel({ review }: ReviewPanelProps) {
  // Group inline comments by file
  const byFile = review.inline_comments.reduce<Record<string, InlineComment[]>>((acc, c) => {
    const key = c.file
    acc[key] = acc[key] ?? []
    acc[key].push(c)
    return acc
  }, {})

  return (
    <div className="space-y-4">
      {Object.entries(byFile).map(([file, comments]) => (
        <CommentGroup
          key={file}
          file={file}
          comments={comments}
          codeSnapshot={review.code_snapshot}
        />
      ))}
    </div>
  )
}

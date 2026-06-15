import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import type { VoteValue, VoteResult } from '../types'

interface VoteButtonsProps {
  score: number
  myVote: VoteValue
  /** Sends the desired absolute vote value (1, -1, or 0 to clear). */
  onVote: (value: VoteValue) => Promise<VoteResult>
}

/**
 * Reddit-style up/down voter. Optimistically updates, then reconciles with the
 * server response. Clicking the active arrow again clears the vote.
 */
export default function VoteButtons({ score, myVote, onVote }: VoteButtonsProps) {
  const [localScore, setLocalScore] = useState(score)
  const [localVote, setLocalVote] = useState<VoteValue>(myVote)
  const [busy, setBusy] = useState(false)

  const cast = async (direction: 1 | -1) => {
    if (busy) return
    const next: VoteValue = localVote === direction ? 0 : direction
    const prevScore = localScore
    const prevVote = localVote

    // Optimistic update
    setLocalVote(next)
    setLocalScore(prevScore - prevVote + next)
    setBusy(true)
    try {
      const result = await onVote(next)
      setLocalScore(result.score)
      setLocalVote(result.my_vote)
    } catch {
      // Revert on failure
      setLocalScore(prevScore)
      setLocalVote(prevVote)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-0.5 select-none">
      <button
        type="button"
        onClick={() => cast(1)}
        disabled={busy}
        aria-label="Upvote"
        className={`p-0.5 rounded hover:bg-[#30363d] transition-colors disabled:opacity-50 ${
          localVote === 1 ? 'text-[#3fb950]' : 'text-[#8b949e]'
        }`}
      >
        <ChevronUp size={18} />
      </button>
      <span
        className={`text-xs font-semibold tabular-nums ${
          localVote === 1
            ? 'text-[#3fb950]'
            : localVote === -1
              ? 'text-[#f85149]'
              : 'text-[#e6edf3]'
        }`}
      >
        {localScore}
      </span>
      <button
        type="button"
        onClick={() => cast(-1)}
        disabled={busy}
        aria-label="Downvote"
        className={`p-0.5 rounded hover:bg-[#30363d] transition-colors disabled:opacity-50 ${
          localVote === -1 ? 'text-[#f85149]' : 'text-[#8b949e]'
        }`}
      >
        <ChevronDown size={18} />
      </button>
    </div>
  )
}

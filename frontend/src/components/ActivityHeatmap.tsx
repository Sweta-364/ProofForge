import { useMemo } from 'react'
import type { ActivityDay } from '../types'

interface ActivityHeatmapProps {
  days: ActivityDay[]
}

interface Cell {
  date: string
  count: number
}

const LEVEL_COLORS = ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353']
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function isoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function levelFor(count: number, max: number): number {
  if (count <= 0) return 0
  if (max <= 1) return 3
  const ratio = count / max
  if (ratio <= 0.25) return 1
  if (ratio <= 0.5) return 2
  if (ratio <= 0.75) return 3
  return 4
}

/**
 * LeetCode/GitHub-style contribution heatmap: one column per week, 7 rows
 * (Sun-Sat), covering the trailing 12 months up to today.
 */
export default function ActivityHeatmap({ days }: ActivityHeatmapProps) {
  const { weeks, monthLabels, maxCount } = useMemo(() => {
    const countByDate = new Map(days.map((d) => [d.date, d.count]))

    const today = new Date()
    const start = new Date(today)
    start.setDate(start.getDate() - 364)
    // Align to the Sunday on/before start
    start.setDate(start.getDate() - start.getDay())

    const weekCols: Cell[][] = []
    const labels: { index: number; label: string }[] = []
    let lastMonth = -1
    const cursor = new Date(start)

    while (cursor <= today) {
      const week: Cell[] = []
      for (let i = 0; i < 7 && cursor <= today; i++) {
        const dateStr = isoDate(cursor)
        week.push({ date: dateStr, count: countByDate.get(dateStr) ?? 0 })
        cursor.setDate(cursor.getDate() + 1)
      }
      // Label the column where a new month starts (first cell's month)
      const firstDay = new Date(week[0].date)
      if (firstDay.getMonth() !== lastMonth) {
        lastMonth = firstDay.getMonth()
        labels.push({ index: weekCols.length, label: MONTH_NAMES[lastMonth] })
      }
      weekCols.push(week)
    }

    const max = Math.max(0, ...days.map((d) => d.count))
    return { weeks: weekCols, monthLabels: labels, maxCount: max }
  }, [days])

  return (
    <div className="overflow-x-auto pb-1">
      <div className="inline-block min-w-full">
        {/* Month labels */}
        <div className="relative h-4 ml-8 mb-1 text-[10px] text-[#8b949e]">
          {monthLabels.map((m) => (
            <span
              key={`${m.label}-${m.index}`}
              className="absolute"
              style={{ left: m.index * 13 }}
            >
              {m.label}
            </span>
          ))}
        </div>

        <div className="flex gap-[3px]">
          {/* Weekday labels */}
          <div className="flex flex-col gap-[3px] w-7 text-[9px] text-[#8b949e] shrink-0">
            {['', 'Mon', '', 'Wed', '', 'Fri', ''].map((d, i) => (
              <span key={i} className="h-[10px] leading-[10px]">
                {d}
              </span>
            ))}
          </div>

          {/* Weeks */}
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-[3px]">
              {week.map((cell) => (
                <div
                  key={cell.date}
                  title={`${cell.count} activit${cell.count === 1 ? 'y' : 'ies'} on ${cell.date}`}
                  className="w-[10px] h-[10px] rounded-[2px] border border-[#21262d]"
                  style={{ backgroundColor: LEVEL_COLORS[levelFor(cell.count, maxCount)] }}
                />
              ))}
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-1 mt-3 text-[10px] text-[#8b949e] justify-end">
          <span>Less</span>
          {LEVEL_COLORS.map((c) => (
            <div
              key={c}
              className="w-[10px] h-[10px] rounded-[2px] border border-[#21262d]"
              style={{ backgroundColor: c }}
            />
          ))}
          <span>More</span>
        </div>
      </div>
    </div>
  )
}

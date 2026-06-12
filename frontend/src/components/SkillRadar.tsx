import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

const SKILL_AXES = [
  'Debugging',
  'Optimization',
  'Security',
  'Architecture',
  'Testing',
  'Performance',
  'Concurrency',
  'Code Quality',
]

const KEY_MAP: Record<string, string> = {
  Debugging: 'debugging',
  Optimization: 'optimization',
  Security: 'security',
  Architecture: 'architecture',
  Testing: 'testing',
  Performance: 'performance',
  Concurrency: 'concurrency',
  'Code Quality': 'code_quality',
}

interface RadarDataPoint {
  skill: string
  value: number
}

interface SkillRadarProps {
  skillRadar: Record<string, number>
}

export default function SkillRadar({ skillRadar }: SkillRadarProps) {
  const data: RadarDataPoint[] = SKILL_AXES.map((skill) => ({
    skill,
    value: skillRadar[KEY_MAP[skill]] ?? 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={320}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
        <PolarGrid stroke="#30363d" />
        <PolarAngleAxis
          dataKey="skill"
          tick={{ fill: '#8b949e', fontSize: 11 }}
          tickLine={false}
        />
        <Radar
          name="Skills"
          dataKey="value"
          stroke="#58a6ff"
          fill="#58a6ff"
          fillOpacity={0.2}
          strokeWidth={2}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '6px',
            color: '#e6edf3',
            fontSize: '12px',
          }}
          formatter={(value) => [String(value), 'Score']}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}


interface ScoreBarProps {
  value: number
  color?: string
}

export function ScoreBar({ value, color = "bg-blue-500" }: ScoreBarProps) {
  const pct = Math.max(0, Math.min(1, value)) * 100
  return (
    <div className="w-40 h-3 bg-muted rounded">
      <div className={`${color} h-3 rounded`} style={{ width: `${pct}%` }} />
    </div>
  )
}
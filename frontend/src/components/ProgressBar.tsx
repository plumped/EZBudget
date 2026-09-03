export function ProgressBar({ percent, over }: { percent: number; over?: boolean }) {
  const width = Math.min(Math.max(percent, 0), 100)
  return (
    <div className="progress-track">
      <div className={over ? 'progress-fill over' : 'progress-fill'} style={{ width: `${width}%` }} />
    </div>
  )
}

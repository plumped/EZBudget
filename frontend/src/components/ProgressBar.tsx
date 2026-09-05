import { useEffect, useState } from 'react'

export function ProgressBar({ percent, over }: { percent: number; over?: boolean }) {
  const target = Math.min(Math.max(percent, 0), 100)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const frame = requestAnimationFrame(() => setWidth(target))
    return () => cancelAnimationFrame(frame)
  }, [target])

  return (
    <div className="progress-track">
      <div className={over ? 'progress-fill over' : 'progress-fill'} style={{ width: `${width}%` }} />
    </div>
  )
}

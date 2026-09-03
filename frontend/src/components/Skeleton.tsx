export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton skeleton-line"
          style={{ width: i === lines - 1 ? '55%' : '100%', marginBottom: 10 }}
        />
      ))}
    </div>
  )
}

export function SkeletonRows({ count = 4 }: { count?: number }) {
  return (
    <div className="row-list" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-row">
          <div className="skeleton" style={{ width: 34, height: 34, borderRadius: 8, flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="skeleton skeleton-line" style={{ width: '40%', height: 12, marginBottom: 8 }} />
            <div className="skeleton skeleton-line" style={{ width: '65%', height: 8 }} />
          </div>
          <div className="skeleton" style={{ width: 60, height: 16 }} />
        </div>
      ))}
    </div>
  )
}

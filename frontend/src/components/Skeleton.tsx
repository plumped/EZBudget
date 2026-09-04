export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="skeleton-text" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton skeleton-line" />
      ))}
    </div>
  )
}

export function SkeletonRows({ count = 4 }: { count?: number }) {
  return (
    <div className="row-list" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-row">
          <div className="skeleton skeleton-avatar" />
          <div className="skeleton-row-main">
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-line" />
          </div>
          <div className="skeleton skeleton-amount" />
        </div>
      ))}
    </div>
  )
}

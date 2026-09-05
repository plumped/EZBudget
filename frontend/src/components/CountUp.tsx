import { useLayoutEffect, useRef, useState } from 'react'

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

/** Animiert eine Zahl beim Einblenden (und bei jeder Änderung) von ihrem
 * bisherigen Wert auf den neuen hoch, statt sofort auf dem Endwert zu stehen.
 * Respektiert prefers-reduced-motion (springt dann direkt auf den Zielwert). */
export function CountUp({
  value,
  format = (n) => n.toFixed(2),
  duration = 900,
}: {
  value: number
  format?: (n: number) => string
  duration?: number
}) {
  const [display, setDisplay] = useState(0)
  const fromRef = useRef(0)

  useLayoutEffect(() => {
    const reduceMotion =
      typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) {
      fromRef.current = value
      setDisplay(value)
      return
    }

    const from = fromRef.current
    if (from === value) return
    const start = performance.now()
    let frame: number

    function tick(now: number) {
      const t = Math.min(1, (now - start) / duration)
      setDisplay(from + (value - from) * easeOutCubic(t))
      if (t < 1) {
        frame = requestAnimationFrame(tick)
      } else {
        fromRef.current = value
      }
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, duration])

  return <>{format(display)}</>
}

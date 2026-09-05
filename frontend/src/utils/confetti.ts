interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  color: string
  rotation: number
  rotationSpeed: number
  shape: 'rect' | 'circle'
}

const COLORS = ['#12513b', '#2f8f63', '#a9791a', '#a8432c', '#dcd8ce']

/** Kurzer Konfetti-Ausbruch (Canvas, ohne externe Bibliothek) — z.B. wenn ein
 * Schulden-Meilenstein erreicht wird. Räumt sich nach dem Ausklingen selbst auf. */
export function triggerConfetti() {
  if (typeof window === 'undefined') return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  const canvas = document.createElement('canvas')
  canvas.style.position = 'fixed'
  canvas.style.inset = '0'
  canvas.style.pointerEvents = 'none'
  canvas.style.zIndex = '300'
  document.body.appendChild(canvas)

  const dpr = window.devicePixelRatio || 1
  const width = window.innerWidth
  const height = window.innerHeight
  canvas.width = width * dpr
  canvas.height = height * dpr
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    canvas.remove()
    return
  }
  ctx.scale(dpr, dpr)

  const particles: Particle[] = Array.from({ length: 130 }, () => ({
    x: width / 2 + (Math.random() - 0.5) * 160,
    y: height * 0.3,
    vx: (Math.random() - 0.5) * 9,
    vy: -Math.random() * 9 - 4,
    size: 5 + Math.random() * 5,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    rotation: Math.random() * Math.PI * 2,
    rotationSpeed: (Math.random() - 0.5) * 0.3,
    shape: Math.random() < 0.5 ? 'rect' : 'circle',
  }))

  const gravity = 0.28
  const drag = 0.992
  const duration = 2200
  const start = performance.now()

  function frame(now: number) {
    const elapsed = now - start
    ctx!.clearRect(0, 0, width, height)
    const fade = Math.max(0, 1 - elapsed / duration)
    let anyOnScreen = false

    for (const p of particles) {
      p.vx *= drag
      p.vy = p.vy * drag + gravity
      p.x += p.vx
      p.y += p.vy
      p.rotation += p.rotationSpeed
      if (p.y < height + 20) anyOnScreen = true

      ctx!.save()
      ctx!.translate(p.x, p.y)
      ctx!.rotate(p.rotation)
      ctx!.globalAlpha = fade
      ctx!.fillStyle = p.color
      if (p.shape === 'rect') {
        ctx!.fillRect(-p.size / 2, -p.size / 3, p.size, p.size * 0.66)
      } else {
        ctx!.beginPath()
        ctx!.arc(0, 0, p.size / 2, 0, Math.PI * 2)
        ctx!.fill()
      }
      ctx!.restore()
    }

    if (elapsed < duration && anyOnScreen) {
      requestAnimationFrame(frame)
    } else {
      canvas.remove()
    }
  }

  requestAnimationFrame(frame)
}

import { Wallet } from '@phosphor-icons/react'
import { useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import { FieldError } from '../components/FieldError'
import { useAuth } from '../context/AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      const fieldErrors = extractFieldErrors(err)
      setErrors(fieldErrors)
      queueMicrotask(() => generalErrorRef.current?.focus())
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark">
            <Wallet size={16} weight="bold" />
          </span>
          ezbudget
        </div>
        <p className="lead">Melde dich mit deinem Login an.</p>
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="username">Benutzername</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              aria-invalid={errors.fields.username ? 'true' : undefined}
              aria-describedby={errors.fields.username ? 'username-error' : undefined}
            />
            {errors.fields.username && <FieldError id="username-error" message={errors.fields.username} />}
          </div>
          <div className="field">
            <label htmlFor="password">Passwort</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              aria-invalid={errors.fields.password ? 'true' : undefined}
              aria-describedby={errors.fields.password ? 'password-error' : undefined}
            />
            {errors.fields.password && <FieldError id="password-error" message={errors.fields.password} />}
          </div>
          {errors.general && (
            <p className="error-text" role="alert" tabIndex={-1} ref={generalErrorRef}>
              {errors.general}
            </p>
          )}
          <button type="submit" className="btn block" disabled={submitting}>
            {submitting ? 'Anmelden …' : 'Anmelden'}
          </button>
        </form>
        <p className="switch">
          Noch kein Konto? <Link to="/signup">Jetzt registrieren</Link>
        </p>
      </div>
    </div>
  )
}

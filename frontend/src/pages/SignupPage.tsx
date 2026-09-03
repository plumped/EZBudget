import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { extractErrorMessage } from '../api/errors'
import { useAuth } from '../context/AuthContext'

export function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await signup(username, password, email)
      navigate('/', { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="dot" />
          ezbudget
        </div>
        <p className="lead">Neues Login anlegen — z.B. für weitere Haushaltsmitglieder.</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="username">Benutzername</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="email">E-Mail (optional)</label>
            <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Passwort</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
            <p className="helptext">Mindestens 8 Zeichen.</p>
          </div>
          {error && <p className="error-text">{error}</p>}
          <button type="submit" className="btn block" disabled={submitting}>
            {submitting ? 'Konto anlegen …' : 'Konto anlegen'}
          </button>
        </form>
        <p className="switch">
          Bereits registriert? <Link to="/login">Anmelden</Link>
        </p>
      </div>
    </div>
  )
}

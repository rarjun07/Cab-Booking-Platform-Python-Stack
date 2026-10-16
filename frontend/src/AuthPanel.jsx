import { useEffect, useId, useState } from 'react'

async function authRequest(path, body, signal) {
  const response = await fetch(`/api/auth/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: signal ?? AbortSignal.timeout(10000),
  })
  if (response.status === 204) return null
  const data = await response.json()
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Check your inputs and try again.')
    error.status = response.status
    throw error
  }
  return data
}

export default function AuthPanel({ user, onUserChange }) {
  const formId = useId()
  const [mode, setMode] = useState('register')
  const setUser = onUserChange
  const [restoring, setRestoring] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 10000)
    let active = true
    authRequest('me', undefined, controller.signal)
      .then((data) => { if (active) setUser(data) })
      .catch((error) => {
        if (active && error.status !== 401) {
          setMessage('Could not check your session. Make sure the backend is running.')
          setIsError(true)
        }
      })
      .finally(() => { clearTimeout(timer); if (active) setRestoring(false) })
    return () => { active = false; clearTimeout(timer); controller.abort() }
  }, [onUserChange])

  async function submit(event) {
    event.preventDefault()
    const form = event.currentTarget
    const fields = new FormData(form)
    const body = { email: fields.get('email'), password: fields.get('password') }
    if (mode === 'register') {
      body.name = fields.get('name')
      body.role = fields.get('role')
    }
    setBusy(true)
    setMessage('')
    setIsError(false)
    try {
      const data = await authRequest(mode, body)
      form.reset()
      setUser(data)
      setMessage(mode === 'register' ? 'Account created. You are signed in.' : 'Welcome back. You are signed in.')
    } catch (error) {
      setIsError(true)
      setMessage(error.status ? error.message : 'Could not reach the backend. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  async function sessionAction(action) {
    setBusy(true)
    setIsError(false)
    setMessage('')
    try {
      const data = await authRequest(action, {})
      if (action === 'logout') {
        setUser(null)
        setMode('login')
        setMessage('You have been signed out.')
      } else {
        setUser(data)
        setMessage('Session verified by FastAPI and PostgreSQL.')
      }
    } catch (error) {
      if (error.status === 401) setUser(null)
      setIsError(true)
      setMessage(error.status ? error.message : 'Could not reach the backend. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-card" aria-labelledby="auth-title">
      <p className="eyebrow">YOUR ACCOUNT</p>
      <h2 id="auth-title">{user ? `Welcome, ${user.name}.` : 'Your journey, your account.'}</h2>
      <p className="auth-description">{user ? `${user.email} · ${user.role}` : 'Create an account or sign in to get started.'}</p>

      {restoring ? <p role="status">Checking your session…</p> : user ? (
        <div className="auth-actions">
          <button type="button" disabled={busy} onClick={() => sessionAction('session')}>Verify my session</button>
          <button className="secondary-button" type="button" disabled={busy} onClick={() => sessionAction('logout')}>Sign out</button>
        </div>
      ) : (
        <>
          <div className="auth-modes" role="group" aria-label="Choose account action">
            <button type="button" disabled={busy} aria-pressed={mode === 'register'} onClick={() => { setMode('register'); setMessage('') }}>Create account</button>
            <button type="button" disabled={busy} aria-pressed={mode === 'login'} onClick={() => { setMode('login'); setMessage('') }}>Sign in</button>
          </div>
          <form key={mode} onSubmit={submit} aria-busy={busy}>
            <fieldset disabled={busy}>
              {mode === 'register' && <div className="form-field"><label htmlFor={`${formId}-name`}>Name</label><input id={`${formId}-name`} name="name" autoComplete="name" maxLength={100} required /></div>}
              <div className="form-field"><label htmlFor={`${formId}-email`}>Email</label><input id={`${formId}-email`} name="email" type="email" autoComplete="email" maxLength={254} required /></div>
              <div className="form-field"><label htmlFor={`${formId}-password`}>Password</label><input id={`${formId}-password`} name="password" type="password" autoComplete={mode === 'register' ? 'new-password' : 'current-password'} minLength={mode === 'register' ? 12 : 1} maxLength={128} aria-describedby={mode === 'register' ? `${formId}-hint` : undefined} required />{mode === 'register' && <small id={`${formId}-hint`}>Use at least 12 characters.</small>}</div>
              {mode === 'register' && <div className="form-field"><label htmlFor={`${formId}-role`}>I’m joining as a</label><select id={`${formId}-role`} name="role" defaultValue="rider"><option value="rider">Rider</option><option value="driver">Driver</option></select></div>}
              <button className="submit-button" type="submit">{busy ? 'Please wait…' : mode === 'register' ? 'Create my account' : 'Sign in to my account'}</button>
            </fieldset>
          </form>
        </>
      )}
      <p className={`auth-message${isError ? ' auth-error' : ''}`} role="status" aria-live="polite" aria-atomic="true">{message}</p>
    </section>
  )
}

import { useEffect, useId, useRef, useState } from 'react'
import { authRequest } from './authRequest.js'

export default function ProfileMenu({ user, onNavigate, onHelp, onSignedOut }) {
  const panelId = useId()
  const root = useRef(null)
  const trigger = useRef(null)
  const feedback = useRef(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const initials = user.name.trim().split(/\s+/).slice(0, 2).map((name) => [...name][0]).join('')

  useEffect(() => {
    if (!open) return
    function outside(event) {
      if (!root.current?.contains(event.target)) setOpen(false)
    }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open])

  useEffect(() => { if (error) feedback.current?.focus() }, [error])

  function follow(event, id) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    setOpen(false)
    onNavigate(id)
  }

  async function signOut() {
    setBusy(true)
    setError('')
    try {
      await authRequest('logout', {})
      onSignedOut()
    } catch (failure) {
      setError(failure.status ? failure.message : 'Could not sign out. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return <div className="profile-menu" ref={root} onBlur={(event) => {
    if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) setOpen(false)
  }} onKeyDown={(event) => {
    if (event.key === 'Escape' && open) {
      event.preventDefault()
      setOpen(false)
      trigger.current?.focus()
    }
  }}>
    <button className="profile-trigger" type="button" aria-label="My account" aria-expanded={open} aria-controls={panelId} ref={trigger} onClick={() => setOpen((value) => !value)}>
      <span className="workspace-avatar" aria-hidden="true">{initials}</span>
      <span className="profile-trigger-name">{user.name}</span>
      <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true" focusable="false"><path d="m5 7 5 5 5-5" /></svg>
    </button>
    <section className="profile-dropdown" id={panelId} hidden={!open} aria-label="Account options" aria-busy={busy}>
      <div className="profile-summary">
        <span className="workspace-avatar" aria-hidden="true">{initials}</span>
        <div>
          <h2>{user.name}</h2>
          <span className="profile-role">{user.role === 'driver' ? 'Driver account' : 'Rider account'}</span>
          <p>{user.email}</p>
          <a className="profile-view" href="#account" onClick={(event) => follow(event, 'account')}>View profile <span aria-hidden="true">↗</span></a>
        </div>
      </div>
      <div className="profile-options">
        <a href="#account" aria-label="My account" onClick={(event) => follow(event, 'account')}><strong>My account</strong><span>View your account and session details.</span></a>
        <a href="#history" aria-label="Trips & receipts" onClick={(event) => follow(event, 'history')}><strong>Trips & receipts</strong><span>Find past trips, documents and payment details.</span></a>
        {user.role === 'rider' && <a href="#wallet" aria-label="Wallet" onClick={(event) => follow(event, 'wallet')}><strong>Wallet</strong><span>View your balance and test top-ups.</span></a>}
        <button type="button" aria-label="Help / connection" onClick={() => { setOpen(false); onHelp() }}><strong>Help / connection</strong><span>Check the app’s connection to its server.</span></button>
        <button className="profile-signout" type="button" aria-label={busy ? 'Signing out…' : 'Sign out'} disabled={busy} onClick={signOut}><strong>{busy ? 'Signing out…' : 'Sign out'}</strong><span>Sign out of this account.</span></button>
      </div>
      <p className="profile-error" role="alert" tabIndex={-1} ref={feedback}>{error}</p>
      <p className="profile-demo-label">Learning project · Test payments only</p>
    </section>
  </div>
}

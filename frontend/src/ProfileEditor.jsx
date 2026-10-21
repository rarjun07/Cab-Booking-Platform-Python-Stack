import { useId, useState } from 'react'
import { authRequest } from './authRequest.js'
import Avatar from './Avatar.jsx'

export default function ProfileEditor({ user, onUserChange }) {
  const id = useId()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState(false)
  async function save(event) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    setBusy(true); setMessage(''); setError(false)
    try {
      const saved = await authRequest('profile', { name: fields.get('name'), phone: fields.get('phone') || null,
        profile_pic: fields.get('profile_pic') || null })
      onUserChange(saved)
      setMessage('Profile saved.')
    } catch (failure) {
      if (failure.status === 401) onUserChange(null)
      setError(true)
      setMessage(failure.status ? failure.message : 'Could not save your profile. Your changes are still in the form.')
    } finally { setBusy(false) }
  }
  return <form className="profile-editor" onSubmit={save} aria-label="Edit profile" aria-busy={busy}>
    <Avatar user={user} />
    <fieldset disabled={busy}>
      <legend className="driver-section-title">Your profile details</legend>
      <div className="form-field"><label htmlFor={`${id}-name`}>Display name</label><input id={`${id}-name`} name="name" defaultValue={user.name} autoComplete="name" maxLength={100} required /></div>
      <div className="form-field"><label htmlFor={`${id}-phone`}>Phone number (optional)</label><input id={`${id}-phone`} name="phone" type="tel" defaultValue={user.phone ?? ''} autoComplete="tel" maxLength={32} aria-describedby={`${id}-phone-help`} /><small id={`${id}-phone-help`}>International format, for example +919876543210. Saved as contact information; this does not verify the number.</small></div>
      <div className="form-field"><label htmlFor={`${id}-photo`}>Profile picture URL (optional)</label><input id={`${id}-photo`} name="profile_pic" type="url" defaultValue={user.profile_pic ?? ''} maxLength={2048} aria-describedby={`${id}-photo-help`} /><small id={`${id}-photo-help`}>Use an HTTPS image link. After saving, your browser loads it from that host, which receives your IP address. Leave blank to use initials.</small></div>
      <button type="submit">{busy ? 'Saving profile…' : 'Save profile'}</button>
    </fieldset>
    <p className={`auth-message${error ? ' auth-error' : ''}`} role={error ? 'alert' : 'status'}>{message}</p>
  </form>
}

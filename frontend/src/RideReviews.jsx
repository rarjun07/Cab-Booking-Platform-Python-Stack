import { useEffect, useId, useRef, useState } from 'react'

async function request(path, signal, body) {
  const response = await fetch(`/api/${path}`, {
    method: body ? 'POST' : 'GET', credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
  })
  const data = await response.json()
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Choose a whole-number rating from 1 to 5 and a comment of at most 2,000 characters.')
    error.status = response.status
    throw error
  }
  return data
}

function Summary({ summary }) {
  return <span>{summary.count ? `${Number(summary.average).toFixed(2)} / 5 from ${summary.count} ${summary.count === 1 ? 'review' : 'reviews'}` : 'No ratings yet'}</span>
}

export function MyRating({ liveRevision, refresh, onSessionExpired }) {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    const abort = new AbortController()
    request('ratings/me', abort.signal).then((saved) => {
      if (abort.signal.aborted) return
      setSummary(saved)
      setError('')
    }).catch((failure) => {
      if (abort.signal.aborted) return
      if (failure.status === 401) onSessionExpired(null)
      setError('Your rating is unavailable. Try Refresh history.')
    })
    return () => abort.abort()
  }, [liveRevision, refresh, onSessionExpired])
  return <p className="rating-summary" aria-live="polite"><strong>Your rating:</strong> {error || (summary ? <Summary summary={summary} /> : 'Checking ratings…')}</p>
}

export default function RideReviews({ rideId, liveRevision, onSessionExpired, onSaved }) {
  const formId = useId()
  const [details, setDetails] = useState(null)
  const [rating, setRating] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [refresh, setRefresh] = useState(0)
  const operation = useRef(null)
  const path = `rides/${rideId}/reviews`
  useEffect(() => () => operation.current?.abort(), [])

  useEffect(() => {
    if (busy) return
    const abort = new AbortController()
    request(path, abort.signal).then((saved) => {
      if (!abort.signal.aborted) setDetails(saved)
    }).catch((failure) => {
      if (abort.signal.aborted) return
      if (failure.status === 401) onSessionExpired(null)
      setMessage(failure.status ? failure.message : 'Could not load trip reviews. Try Refresh reviews.')
    })
    return () => abort.abort()
  }, [path, liveRevision, refresh, busy, onSessionExpired])

  async function submit(event) {
    event.preventDefault()
    if (!rating || busy) return
    const abort = new AbortController()
    operation.current = abort
    setBusy(true)
    setMessage('')
    try {
      await request(path, abort.signal, { rating: Number(rating), comment: comment.trim() || null })
      const saved = await request(path, abort.signal)
      if (abort.signal.aborted) return
      setDetails(saved)
      setMessage('Your review has been saved. Thank you for sharing your trip feedback.')
      onSaved()
    } catch (failure) {
      if (abort.signal.aborted) return
      if (failure.status === 401) onSessionExpired(null)
      setMessage(failure.status ? failure.message : 'Could not confirm your review. Refresh reviews before retrying; identical retries do not create another review.')
    } finally { if (!abort.signal.aborted) setBusy(false) }
  }

  return <section className="review-panel" aria-labelledby={`${formId}-title`} aria-busy={busy}>
    <h4 id={`${formId}-title`}>Trip ratings and reviews</h4>
    {details?.counterpart && <p>{details.counterpart.name} · <Summary summary={details.counterpart} /></p>}
    {details?.submitted && <div className="saved-review"><strong>Your review: {details.submitted.rating} / 5</strong>
      {details.submitted.comment && <p className="review-comment">{details.submitted.comment}</p>}
      <p className="fare-note">One review per trip. Submitted reviews cannot be edited.</p>
    </div>}
    {details?.received && <div className="saved-review"><strong>Their review of you: {details.received.rating} / 5</strong>
      {details.received.comment && <p className="review-comment">{details.received.comment}</p>}
    </div>}
    {details?.reason && <p>{details.reason}</p>}
    {details?.can_review && <form onSubmit={submit}>
      <fieldset disabled={busy}>
        <legend>Rate your {details.counterpart.role}</legend>
        <div className="rating-options">{[1, 2, 3, 4, 5].map((value) => <label key={value}>
          <input type="radio" name={`${formId}-rating`} value={value} required checked={rating === String(value)} onChange={(event) => setRating(event.target.value)} /> {value} {value === 1 ? 'star' : 'stars'}
        </label>)}</div>
        <div className="form-field"><label htmlFor={`${formId}-comment`}>Comment (optional)</label>
          <textarea id={`${formId}-comment`} value={comment} maxLength={2000} rows={3} aria-describedby={`${formId}-comment-hint`} onChange={(event) => setComment(event.target.value)} />
          <small id={`${formId}-comment-hint`}>Up to 2,000 characters. Visible to the other trip participant.</small>
        </div>
        <button type="submit" disabled={!rating}>{busy ? 'Saving review…' : 'Submit review'}</button>
      </fieldset>
    </form>}
    {!details && !message && <p role="status">Loading reviews…</p>}
    <button className="secondary-button" type="button" disabled={busy} onClick={() => { setMessage(''); setRefresh((value) => value + 1) }}>Refresh reviews</button>
    <p className="auth-message" role="status" aria-live="polite">{message}</p>
  </section>
}

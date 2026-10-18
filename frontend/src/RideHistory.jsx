import { useEffect, useRef, useState } from 'react'
import RidePayment from './RidePayment.jsx'

const money = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value))

async function request(path, { post = false, signal, pdf = false } = {}) {
  const response = await fetch(`/api/${path}`, {
    method: post ? 'POST' : 'GET', credentials: 'same-origin',
    headers: post ? { 'Content-Type': 'application/json' } : {}, body: post ? '{}' : undefined,
    signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]),
  })
  if (!response.ok) {
    const data = await response.json()
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Could not load your ride history.')
    error.status = response.status
    throw error
  }
  return pdf ? response.blob() : response.json()
}

export default function RideHistory({ user, liveRevision, onSessionExpired }) {
  const [page, setPage] = useState(null)
  const [cursor, setCursor] = useState(null)
  const [previous, setPrevious] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [emailEnabled, setEmailEnabled] = useState(false)
  const [jobs, setJobs] = useState({})
  const [paymentRide, setPaymentRide] = useState(null)
  const [refresh, setRefresh] = useState(0)
  const operation = useRef(null)

  useEffect(() => () => operation.current?.abort(), [])

  useEffect(() => {
    const abort = new AbortController()
    setLoading(true)
    const query = new URLSearchParams({ limit: '5' })
    if (cursor) query.set('cursor', cursor)
    Promise.all([
      request(`rides/history?${query}`, { signal: abort.signal }),
      request('receipts/config', { signal: abort.signal }),
    ]).then(([saved, config]) => {
      if (abort.signal.aborted) return
      setPage(saved)
      setEmailEnabled(config.email_enabled)
    }).catch((error) => {
      if (abort.signal.aborted) return
      if (error.status === 401) onSessionExpired(null)
      setMessage(error.status ? error.message : 'Could not reach ride history. Try Refresh history.')
    }).finally(() => { if (!abort.signal.aborted) setLoading(false) })
    return () => abort.abort()
  }, [cursor, liveRevision, refresh, onSessionExpired])

  async function act(ride, action) {
    operation.current?.abort()
    const abort = new AbortController()
    operation.current = abort
    setBusy(true)
    setMessage('')
    try {
      if (action === 'download') {
        const blob = await request(`rides/${ride.id}/receipt.pdf`, { signal: abort.signal, pdf: true })
        if (abort.signal.aborted) return
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `ride-${ride.id}.pdf`
        document.body.appendChild(link)
        link.click()
        link.remove()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
        setMessage('Your trip document is ready to download.')
      } else {
        const job = await request(`rides/${ride.id}/receipt-email`, { post: action === 'email', signal: abort.signal })
        if (abort.signal.aborted) return
        setJobs((saved) => ({ ...saved, [ride.id]: job }))
        setMessage(!job ? 'No email request exists for the current receipt.' : job.status === 'sent'
          ? 'The email server accepted your trip document.' : job.status === 'failed'
            ? 'Delivery failed. Check the email setup, then retry after one minute. PDF download is still available.'
            : 'Email queued. The receipt worker must be running; check email status shortly.')
      }
    } catch (error) {
      if (abort.signal.aborted) return
      if (error.status === 401) onSessionExpired(null)
      setMessage(error.status ? error.message : 'Could not complete this action. You can retry safely.')
    } finally { if (!abort.signal.aborted) setBusy(false) }
  }

  return <section className="auth-card history-card" aria-labelledby="history-title" aria-busy={loading || busy}>
    <p className="eyebrow">YOUR PAST JOURNEYS</p>
    <h2 id="history-title">Ride history and trip documents</h2>
    <p className="auth-description">Your completed and cancelled trips. Trip documents show the recorded payment status.</p>
    <button className="secondary-button" type="button" disabled={busy || loading} onClick={() => { setMessage(''); setRefresh((v) => v + 1) }}>Refresh history</button>
    {loading && <p role="status">Loading your history…</p>}
    {!loading && page?.items.length === 0 && <p>No past trips on this page yet.</p>}
    {!loading && page && <ul className="history-list">{page.items.map((ride) => <li key={ride.id}>
      <div className="matching-title"><strong>{ride.status.replaceAll('_', ' ')}</strong><span>{new Date(ride.created_at).toLocaleDateString()}</span></div>
      <p className="ride-reference">Reference: {ride.id}</p>
      <p>Pickup: {ride.pickup.latitude}, {ride.pickup.longitude}<br />Destination: {ride.destination.latitude}, {ride.destination.longitude}</p>
      <p>{ride.payment_amount != null ? 'Invoice' : ride.fare_actual != null ? 'Final fare' : 'Estimated fare'}: {money(ride.payment_amount ?? ride.fare_actual ?? ride.fare_estimate)} · Payment: {ride.payment_status?.replaceAll('_', ' ') ?? 'not paid'}</p>
      {ride.receipt_available && <>
        <div className="auth-actions">
          <button type="button" disabled={busy} onClick={() => act(ride, 'download')}>Download PDF</button>
          <button className="secondary-button" type="button" disabled={busy || !emailEnabled} onClick={() => act(ride, 'email')}>Email to my account</button>
          <button className="secondary-button" type="button" disabled={busy} onClick={() => act(ride, 'status')}>Check email status</button>
          {user.role === 'rider' && <button className="secondary-button" type="button" onClick={() => setPaymentRide(paymentRide === ride.id ? null : ride.id)}>{paymentRide === ride.id ? 'Close payment details' : 'View payment details'}</button>}
        </div>
        {jobs[ride.id] && <p className="fare-note">Email request: {jobs[ride.id].status} · attempts: {jobs[ride.id].attempts}</p>}
        {paymentRide === ride.id && <RidePayment key={ride.id} rideId={ride.id} liveRevision={liveRevision} onSessionExpired={onSessionExpired} />}
      </>}
    </li>)}</ul>}
    {!emailEnabled && <p className="fare-note">Email delivery awaits local setup. Completed-trip PDFs remain available.</p>}
    <div className="auth-actions">
      <button className="secondary-button" type="button" disabled={busy || loading || !previous.length} onClick={() => { setCursor(previous.at(-1)); setPrevious((saved) => saved.slice(0, -1)); setPaymentRide(null) }}>Previous page</button>
      <button className="secondary-button" type="button" disabled={busy || loading || !page?.next_cursor} onClick={() => { setPrevious((saved) => [...saved, cursor]); setCursor(page.next_cursor); setPaymentRide(null) }}>Next page</button>
    </div>
    <p className="auth-message" role="status" aria-live="polite">{message}</p>
  </section>
}

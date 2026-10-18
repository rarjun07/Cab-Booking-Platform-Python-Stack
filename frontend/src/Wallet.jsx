import { useEffect, useRef, useState } from 'react'
import { Elements } from '@stripe/react-stripe-js'
import { stripeClient, TestCardForm } from './RidePayment.jsx'

const money = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value))

async function request(path, signal, body) {
  const response = await fetch(`/api/${path}`, {
    method: body ? 'POST' : 'GET', credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]),
  })
  const data = await response.json()
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Use an amount from INR 50 to INR 10,000, with at most two decimal places.')
    error.status = response.status
    throw error
  }
  return data
}

export default function Wallet({ liveRevision, onSessionExpired }) {
  const [saved, setSaved] = useState(null)
  const [config, setConfig] = useState(null)
  const [amount, setAmount] = useState('100.00')
  const [selectedId, setSelectedId] = useState(null)
  const [selected, setSelected] = useState(null)
  const [checkout, setCheckout] = useState(null)
  const [stripePromise, setStripePromise] = useState(null)
  const [awaiting, setAwaiting] = useState(false)
  const [busy, setBusy] = useState(false)
  const [revision, setRevision] = useState(0)
  const [message, setMessage] = useState('')
  const attempt = useRef(null)
  const operation = useRef(null)
  useEffect(() => () => operation.current?.abort(), [])

  useEffect(() => {
    if (busy) return
    const abort = new AbortController()
    Promise.all([
      request('wallet', abort.signal), request('payments/config', abort.signal),
      selectedId ? request(`wallet/topups/${selectedId}`, abort.signal) : Promise.resolve(null),
    ]).then(([wallet, available, topup]) => {
      if (abort.signal.aborted) return
      setSaved(wallet)
      setConfig(available)
      setSelected(topup)
      if (topup && ['succeeded', 'cancelled'].includes(topup.status)) { setCheckout(null); setAwaiting(false) }
      if (topup?.status === 'failed') setAwaiting(false)
    }).catch((error) => {
      if (abort.signal.aborted) return
      if (error.status === 401) onSessionExpired(null)
      setMessage(error.status ? error.message : 'Could not read your wallet. Try Refresh wallet.')
    })
    return () => abort.abort()
  }, [liveRevision, revision, selectedId, busy, onSessionExpired])

  async function prepare(id = null) {
    const abort = new AbortController()
    operation.current = abort
    setBusy(true)
    setMessage('')
    try {
      if (!id && !attempt.current) attempt.current = { amount, request_key: crypto.randomUUID() }
      const prepared = await request(id ? `wallet/topups/${id}/payment-intent` : 'wallet/topups', abort.signal, id ? {} : attempt.current)
      if (abort.signal.aborted) return
      setSelectedId(prepared.topup.id)
      setSelected(prepared.topup)
      setAwaiting(!prepared.client_secret && prepared.topup.status !== 'succeeded')
      if (prepared.client_secret && prepared.publishable_key.startsWith('pk_test_')) {
        const client = stripeClient(prepared.publishable_key)
        client.catch(() => { if (!abort.signal.aborted) setMessage('Stripe.js could not load. Check your connection and continue this top-up again.') })
        setStripePromise(client)
        setCheckout(prepared)
      } else setCheckout(null)
    } catch (error) {
      if (abort.signal.aborted) return
      if (error.status === 401) onSessionExpired(null)
      setMessage(error.status ? error.message : 'Could not confirm checkout. Retry the same request or refresh the wallet to continue its saved top-up.')
    } finally { if (!abort.signal.aborted) setBusy(false) }
  }

  function newTopup() {
    operation.current?.abort()
    attempt.current = null
    setSelectedId(null)
    setSelected(null)
    setCheckout(null)
    setAwaiting(false)
    setMessage('')
    setRevision((value) => value + 1)
  }

  return <section id="wallet" tabIndex={-1} className="auth-card wallet-card" aria-labelledby="wallet-title" aria-busy={busy}>
    <p className="eyebrow">YOUR TEST WALLET</p>
    <h2 id="wallet-title">Wallet balance</h2>
    <p className="fare-total" aria-live="polite" aria-atomic="true">{saved ? money(saved.balance) : 'Checking balance…'}</p>
    <p className="fare-note">Verified test credits only. No real money is added in this project’s test mode.</p>
    {config?.configured === false && <p>Test top-ups await Stripe configuration. Your recorded balance remains available.</p>}
    {!selectedId && <form onSubmit={(event) => { event.preventDefault(); prepare() }}>
      <div className="form-field"><label htmlFor="wallet-amount">Top-up amount (INR)</label>
        <input id="wallet-amount" type="number" min="50" max="10000" step="0.01" value={amount} required aria-describedby="wallet-amount-hint" disabled={busy || Boolean(attempt.current)} onChange={(event) => setAmount(event.target.value)} />
        <small id="wallet-amount-hint">INR 50–10,000, with up to two decimal places.</small>
      </div>
      <button type="submit" disabled={busy || !config?.configured}>{busy ? 'Preparing test top-up…' : attempt.current ? 'Retry this top-up' : 'Open test top-up'}</button>
    </form>}
    {selected && <p role="status">Selected top-up: {money(selected.amount)} · {selected.status}{selected.credited_at ? ' · wallet credited' : ''}</p>}
    {awaiting && <p role="status">Waiting for the signed top-up notification. Keep the Stripe listener running, then refresh the wallet.</p>}
    {checkout && !awaiting && <Elements key={checkout.topup.id} stripe={stripePromise} options={{ clientSecret: checkout.client_secret }}>
      <TestCardForm amount={checkout.topup.amount} label="Top up" onConfirmed={async () => { setAwaiting(true); setRevision((value) => value + 1) }} />
    </Elements>}
    <div className="auth-actions">
      <button className="secondary-button" type="button" disabled={busy} onClick={() => { setMessage(''); setRevision((value) => value + 1) }}>Refresh wallet</button>
      {(selectedId || attempt.current) && <button className="secondary-button" type="button" disabled={busy} onClick={newTopup}>Start another top-up</button>}
    </div>
    {saved?.topups.length > 0 && <><h3>Recent top-ups</h3><ul className="matching-list">{saved.topups.map((topup) => <li key={topup.id}>
      <p>{money(topup.amount)} · {topup.status} · {new Date(topup.created_at).toLocaleDateString()}</p>
      {!['succeeded', 'cancelled'].includes(topup.status) && <button className="secondary-button" type="button" disabled={busy || !config?.configured} onClick={() => prepare(topup.id)}>Continue test top-up</button>}
    </li>)}</ul></>}
    {saved?.entries.length > 0 && <><h3>Recent verified credits</h3><ul className="matching-list">{saved.entries.map((entry) => <li key={entry.id}>+ {money(entry.amount)} · {new Date(entry.created_at).toLocaleDateString()}</li>)}</ul></>}
    <p className="auth-message" role="status" aria-live="polite">{message}</p>
  </section>
}

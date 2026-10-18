import { useEffect, useId, useRef, useState } from 'react'
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js'
import { loadStripe } from '@stripe/stripe-js/pure'

const stripeClients = new Map()
const money = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value))

export function stripeClient(key) {
  if (!stripeClients.has(key)) stripeClients.set(key, loadStripe(key))
  return stripeClients.get(key)
}

async function paymentRequest(path, { post = false, signal, body } = {}) {
  const response = await fetch(`/api/${path}`, {
    method: post ? 'POST' : 'GET', credentials: 'same-origin',
    headers: post ? { 'Content-Type': 'application/json' } : {},
    body: post ? JSON.stringify(body ?? {}) : undefined,
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(20000)]) : AbortSignal.timeout(20000),
  })
  const data = await response.json()
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Could not load this test payment.')
    error.status = response.status
    throw error
  }
  return data
}

export function TestCardForm({ amount, onConfirmed, label = 'Pay' }) {
  const stripe = useStripe()
  const elements = useElements()
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState('')
  const [ready, setReady] = useState(false)
  const [unavailable, setUnavailable] = useState(false)
  const active = useRef(true)

  useEffect(() => {
    active.current = true
    const timer = setTimeout(() => { if (active.current) setUnavailable(true) }, 15000)
    return () => { active.current = false; clearTimeout(timer) }
  }, [])

  async function confirm(event) {
    event.preventDefault()
    if (!stripe || !elements || submitting) return
    setSubmitting(true)
    setMessage('')
    try {
      const result = await stripe.confirmPayment({ elements, redirect: 'if_required' })
      if (!active.current) return
      if (result.error) setMessage(result.error.message ?? 'The test payment could not be confirmed.')
      else if (result.paymentIntent?.status === 'succeeded' || result.paymentIntent?.status === 'processing') {
        await onConfirmed()
      } else setMessage('Follow the payment form instructions, then try again.')
    } catch {
      if (active.current) setMessage('Could not confirm the test payment. Refresh payment status before retrying.')
    } finally {
      if (active.current) setSubmitting(false)
    }
  }

  return <form className="stripe-form" onSubmit={confirm} aria-busy={submitting}>
    <PaymentElement options={{ layout: 'tabs' }} onReady={() => { setReady(true); setUnavailable(false) }} onLoadError={() => setUnavailable(true)} />
    {unavailable && !ready && <p role="status">The Stripe test form has not loaded. Check your connection, then reopen checkout.</p>}
    <button type="submit" disabled={!stripe || !elements || !ready || submitting}>{submitting ? 'Confirming test payment…' : `${label} ${money(amount)} in test mode`}</button>
    <p className="auth-message auth-error" role="status" aria-live="polite">{message}</p>
  </form>
}

export default function RidePayment({ rideId, liveRevision, onSessionExpired }) {
  const panelId = useId()
  const [config, setConfig] = useState(null)
  const [payment, setPayment] = useState(null)
  const [checkout, setCheckout] = useState(null)
  const [stripePromise, setStripePromise] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [awaitingWebhook, setAwaitingWebhook] = useState(false)
  const [message, setMessage] = useState('')
  const [promo, setPromo] = useState(null)
  const [promoCode, setPromoCode] = useState('')
  const mounted = useRef(true)
  const controller = useRef(null)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; controller.current?.abort() }
  }, [])

  function showError(error) {
    if (error.status === 401) onSessionExpired(null)
    setMessage(error.status ? error.message : 'Could not reach test payments. Refresh payment status to retry.')
  }

  useEffect(() => {
    if (busy) return
    const abort = new AbortController()
    async function read() {
      try {
        const [saved, available, discount] = await Promise.all([
          paymentRequest(`rides/${rideId}/payment`, { signal: abort.signal }),
          paymentRequest('payments/config', { signal: abort.signal }),
          paymentRequest(`rides/${rideId}/promo`, { signal: abort.signal }),
        ])
        if (abort.signal.aborted) return
        setPayment(saved)
        setConfig(available)
        setPromo(discount)
        if (saved?.status === 'succeeded') { setCheckout(null); setAwaitingWebhook(false) }
        if (['failed', 'cancelled', 'refunded'].includes(saved?.status)) setAwaitingWebhook(false)
      } catch (error) { if (!abort.signal.aborted) showError(error) }
      finally { if (!abort.signal.aborted) setLoading(false) }
    }
    read()
    return () => abort.abort()
  }, [rideId, liveRevision, busy, onSessionExpired])

  async function applyPromo(event) {
    event.preventDefault()
    const abort = new AbortController()
    controller.current = abort
    setBusy(true)
    setMessage('')
    try {
      const discount = await paymentRequest(`rides/${rideId}/promo`, { post: true, signal: abort.signal, body: { code: promoCode } })
      if (mounted.current && !abort.signal.aborted) { setPromo(discount); setMessage('Promo applied. Your discounted fare is fixed for this trip.') }
    } catch (error) { if (mounted.current && !abort.signal.aborted) showError(error) }
    finally { if (mounted.current) setBusy(false) }
  }

  async function refresh() {
    const saved = await paymentRequest(`rides/${rideId}/payment`)
    if (!mounted.current) return
    setPayment(saved)
    if (saved?.status === 'succeeded') { setCheckout(null); setAwaitingWebhook(false) }
    if (['failed', 'cancelled', 'refunded'].includes(saved?.status)) setAwaitingWebhook(false)
    return saved
  }

  async function openCheckout() {
    setBusy(true)
    setMessage('')
    const abort = new AbortController()
    controller.current = abort
    try {
      const prepared = await paymentRequest(`rides/${rideId}/payment-intent`, { post: true, signal: abort.signal })
      if (!mounted.current || abort.signal.aborted) return
      setPayment(prepared.payment)
      setAwaitingWebhook(!prepared.client_secret && prepared.payment.status !== 'succeeded')
      if (prepared.client_secret && prepared.publishable_key.startsWith('pk_test_')) {
        const client = stripeClient(prepared.publishable_key)
        // Surface Stripe.js load failures without logging checkout credentials.
        client.catch(() => { if (mounted.current) setMessage('Stripe.js could not load. Check your connection and reopen checkout.') })
        setStripePromise(client)
        setCheckout(prepared)
      }
    } catch (error) { if (!abort.signal.aborted && mounted.current) showError(error) }
    finally { if (mounted.current) setBusy(false) }
  }

  async function confirmed() {
    setAwaitingWebhook(true)
    await refresh()
  }

  async function manualRefresh() {
    setBusy(true)
    setMessage('')
    try {
      const [savedConfig] = await Promise.all([paymentRequest('payments/config'), refresh()])
      if (mounted.current) setConfig(savedConfig)
    } catch (error) { if (mounted.current) showError(error) }
    finally { if (mounted.current) setBusy(false) }
  }

  const paid = payment?.status === 'succeeded'
  const closed = ['cancelled', 'refunded'].includes(payment?.status)
  return <section className="payment-card" aria-labelledby={`${panelId}-title`} aria-busy={busy || loading}>
    <p className="eyebrow">STRIPE TEST PAYMENT</p>
    <h4 id={`${panelId}-title`}>{paid ? 'Test payment received' : 'Pay for your completed trip'}</h4>
    <p className="fare-note">Use Stripe test details only. No real money is charged in this project’s test mode.</p>
    {loading ? <p role="status">Checking payment status…</p> : <>
      {promo && <p className="fare-note">{promo.code}: {money(promo.base_amount)} − {money(promo.discount_amount)} = {money(promo.final_amount)}</p>}
      {!payment && !promo && <form onSubmit={applyPromo} className="promo-form">
        <label htmlFor={`${panelId}-promo`}>Promo code (optional, before checkout)</label>
        <div className="auth-actions"><input id={`${panelId}-promo`} value={promoCode} onChange={(event) => setPromoCode(event.target.value)} minLength={3} maxLength={20} pattern="[A-Za-z0-9]+" autoCapitalize="characters" spellCheck={false} required disabled={busy} /><button className="secondary-button" type="submit" disabled={busy || !promoCode.trim()}>Apply promo</button></div>
      </form>}
      {payment && <p role="status">Invoice: {money(payment.amount)} · {payment.status.replaceAll('_', ' ')}</p>}
      {paid && <p>Payment verified by the backend’s signed Stripe webhook.</p>}
      {!paid && config?.configured === false && <p>Stripe test payments are awaiting local configuration. Follow the Day 6 setup guide before opening checkout.</p>}
      {!paid && config?.configured && !closed && !awaitingWebhook && !checkout && <button type="button" disabled={busy} onClick={openCheckout}>Open test checkout</button>}
      {!paid && awaitingWebhook && <p role="status">Waiting for the signed payment notification. Keep the Stripe webhook listener running; refresh status if needed.</p>}
      {!paid && checkout && !awaitingWebhook && <>
        <Elements key={checkout.payment.id} stripe={stripePromise} options={{ clientSecret: checkout.client_secret, appearance: { theme: 'stripe', variables: { colorPrimary: '#172a28', borderRadius: '8px' } } }}>
          <TestCardForm amount={payment.amount} onConfirmed={confirmed} />
        </Elements>
        <button className="secondary-button" type="button" onClick={() => setCheckout(null)}>Close test checkout</button>
      </>}
      {closed && <p>This payment is closed. It cannot be submitted again.</p>}
      <button className="secondary-button" type="button" disabled={busy} onClick={manualRefresh}>Refresh payment status</button>
    </>}
    <p className="auth-message auth-error" role="status" aria-live="polite">{message}</p>
  </section>
}

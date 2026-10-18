import { useState } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import axe from 'axe-core'
import App from '../src/App.jsx'
import AuthPanel from '../src/AuthPanel.jsx'
import RidePayment from '../src/RidePayment.jsx'
import RideReviews from '../src/RideReviews.jsx'

// No browser, database, WebSocket, routing or payment provider is contacted.
vi.mock('../src/useRealtime.js', () => ({ default: () => ({ status: 'connected', revision: 0 }) }))

const rider = { id: 'rider-fixture', name: 'Test Rider', email: 'rider@example.com', role: 'rider' }
const driver = { ...rider, id: 'driver-fixture', name: 'Test Driver', role: 'driver' }
const trip = { id: 'trip-fixture', status: 'completed', driver_id: null, created_at: '2026-10-18T08:00:00Z',
  pickup: { latitude: 28.6, longitude: 77.2 }, destination: { latitude: 28.7, longitude: 77.3 },
  fare_estimate: '104.38', fare_actual: null, payment_amount: null, payment_status: null, receipt_available: true }
let account, currentRide, discount, submitted, unexpected

beforeEach(() => {
  account = null
  currentRide = null
  discount = null
  submitted = null
  unexpected = []
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url, 'http://localhost').pathname
    let data = null
    let status = 200
    if (path === '/api/auth/me') { data = account ?? { detail: 'Sign in required.' }; status = account ? 200 : 401 }
    else if (path === '/api/auth/login' || path === '/api/auth/register') { account = rider; data = rider }
    else if (path === '/api/auth/logout') { account = null; return new Response(null, { status: 204 }) }
    else if (path === '/api/rides/current') data = currentRide
    else if (path === '/api/rides/history') data = { items: [trip], next_cursor: null }
    else if (path === '/api/receipts/config') data = { email_enabled: false }
    else if (path === '/api/ratings/me') data = { average: null, count: 0 }
    else if (path === '/api/payments/config') data = { configured: false, test_mode: true }
    else if (path === '/api/wallet') data = { balance: '0.00', currency: 'inr', topups: [], entries: [] }
    else if (path === '/api/drivers/me') data = { status: 'offline', vehicle_info: { make: 'Test', model: 'Car', plate: 'TEST123' }, current_location: null, verified: false }
    else if (path === '/api/drivers/me/ride') data = null
    else if (path === '/api/drivers/me/offers') data = []
    else if (path.endsWith('/payment')) data = null
    else if (path.endsWith('/promo')) {
      if (options.method === 'POST') discount = { code: 'WELCOME10', base_amount: '104.38', discount_amount: '10.44', final_amount: '93.94' }
      data = discount
    } else if (path.endsWith('/reviews')) {
      if (options.method === 'POST') submitted = JSON.parse(options.body)
      data = { can_review: !submitted, counterpart: { name: 'Test Driver', role: 'driver', average: null, count: 0 }, submitted, received: null }
    } else { unexpected.push(`${options.method ?? 'GET'} ${path}`); throw new Error('Unexpected fixture request') }
    return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } })
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  expect(unexpected).toEqual([])
})

async function ready(role) {
  account = role === 'rider' ? rider : role === 'driver' ? driver : null
  const result = render(<App />)
  await screen.findByRole('button', { name: role ? 'Sign out' : 'Create my account' })
  await waitFor(() => expect(result.container.querySelector('[aria-busy="true"]')).toBeNull())
  return result
}

function checkReferences(container) {
  const ids = [...container.querySelectorAll('[id]')].map((element) => element.id)
  expect(new Set(ids).size).toBe(ids.length)
  for (const element of container.querySelectorAll('[aria-labelledby], [aria-describedby], [aria-controls]')) {
    for (const attribute of ['aria-labelledby', 'aria-describedby', 'aria-controls']) {
      for (const id of (element.getAttribute(attribute) ?? '').split(/\s+/).filter(Boolean)) expect(document.getElementById(id)).not.toBeNull()
    }
  }
  for (const label of container.querySelectorAll('label[for]')) expect(document.getElementById(label.htmlFor)).not.toBeNull()
}

test.each([null, 'rider', 'driver'])('%s workspace has named controls, valid references and no detected structural WCAG violations', async (role) => {
  const { container } = await ready(role)
  checkReferences(container)
  const links = within(screen.getByRole('navigation', { name: 'Workspace sections' })).getAllByRole('link')
  for (const link of links) expect(document.querySelector(link.getAttribute('href'))?.tabIndex).toBe(-1)
  expect(links.some((link) => link.textContent === 'Wallet')).toBe(role === 'rider')
  const audit = await axe.run(container, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
    // jsdom has no layout/painting engine. Contrast, reflow and focus visibility
    // need the manual browser checklist, not a simulated pass here.
    rules: { 'color-contrast': { enabled: false } },
  })
  expect(audit.violations.map(({ id, nodes }) => ({ id, count: nodes.length }))).toEqual([])
})

test('keyboard entry begins with the skip link and can activate the account mode buttons', async () => {
  await ready(null)
  const user = userEvent.setup()
  await user.tab()
  expect(document.activeElement).toBe(screen.getByRole('link', { name: 'Skip to content' }))
  const signIn = screen.getByRole('button', { name: 'Sign in', exact: true })
  signIn.focus()
  await user.keyboard('{Enter}')
  expect(signIn.getAttribute('aria-pressed')).toBe('true')
  expect(screen.queryByRole('combobox')).toBeNull()
  expect(screen.getByLabelText('Password').autocomplete).toBe('current-password')
})

function AccountHarness() {
  const [user, setUser] = useState(null)
  return <AuthPanel user={user} onUserChange={setUser} />
}

test('keyboard sign-in and sign-out return focus to the persistent account heading', async () => {
  render(<AccountHarness />)
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sign in', exact: true }))
  await user.type(screen.getByLabelText('Email'), 'rider@example.com')
  await user.type(screen.getByLabelText('Password'), 'fixture-password')
  await user.keyboard('{Enter}')
  const welcome = await screen.findByRole('heading', { name: 'Welcome, Test Rider.' })
  await waitFor(() => expect(document.activeElement).toBe(welcome))
  screen.getByRole('button', { name: 'Sign out' }).focus()
  await user.keyboard('{Enter}')
  const signedOut = await screen.findByRole('heading', { name: 'Your journey, your account.' })
  await waitFor(() => expect(document.activeElement).toBe(signedOut))
})

test('an explicit failed sign-in focuses its error feedback without discarding the email', async () => {
  render(<AccountHarness />)
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Sign in', exact: true }))
  await user.type(screen.getByLabelText('Email'), 'rider@example.com')
  await user.type(screen.getByLabelText('Password'), 'wrong-password')
  fetch.mockImplementationOnce(async () => new Response(JSON.stringify({ detail: 'Incorrect email or password.' }), { status: 401 }))
  await user.keyboard('{Enter}')
  const error = await screen.findByRole('alert')
  await waitFor(() => expect(document.activeElement).toBe(error))
  expect(error.textContent).toBe('Incorrect email or password.')
  expect(screen.getByLabelText('Email').value).toBe('rider@example.com')
})

test('the same trip can have current and history checkout panels without duplicate IDs or broken labels', async () => {
  currentRide = trip
  const { container } = await ready('rider')
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'View payment details' }))
  await waitFor(() => expect(screen.getAllByLabelText('Promo code (optional, before checkout)')).toHaveLength(2))
  checkReferences(container)
  const close = screen.getByRole('button', { name: 'Close payment details' })
  expect(close.getAttribute('aria-expanded')).toBe('true')
  await user.click(close)
  expect(screen.getByRole('button', { name: 'View payment details' }).getAttribute('aria-expanded')).toBe('false')
})

test('a promo can be applied with the keyboard while Stripe checkout is disabled', async () => {
  render(<RidePayment rideId={trip.id} liveRevision={0} onSessionExpired={vi.fn()} />)
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText('Promo code (optional, before checkout)'), 'WELCOME10')
  await user.keyboard('{Enter}')
  await screen.findByText('Promo applied. Your discounted fare is fixed for this trip.')
  expect(discount.final_amount).toBe('93.94')
  expect(screen.queryByRole('button', { name: 'Open test checkout' })).toBeNull()
})

test('native radio keyboard selection submits a numeric review and keeps an unsaved draft on background refresh', async () => {
  const onSessionExpired = vi.fn()
  const props = { rideId: trip.id, liveRevision: 0, onSessionExpired, onSaved: vi.fn() }
  const { rerender } = render(<RideReviews {...props} />)
  const user = userEvent.setup()
  const one = await screen.findByRole('radio', { name: '1 star', exact: true })
  one.focus()
  await user.keyboard('[Space][ArrowRight][ArrowRight][ArrowRight][ArrowRight]')
  expect(screen.getByRole('radio', { name: '5 stars' }).checked).toBe(true)
  await user.type(screen.getByLabelText('Comment (optional)'), 'Comfortable trip')
  rerender(<RideReviews {...props} liveRevision={1} />)
  await waitFor(() => expect(screen.getByLabelText('Comment (optional)').value).toBe('Comfortable trip'))
  screen.getByRole('button', { name: 'Submit review' }).focus()
  await user.keyboard('{Enter}')
  await screen.findByText('Your review: 5 / 5')
  expect(submitted).toEqual({ rating: 5, comment: 'Comfortable trip' })
})

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
let account, signInAccount, currentRide, discount, submitted, unexpected

beforeEach(() => {
  window.history.replaceState(null, '', '/')
  account = null
  signInAccount = rider
  currentRide = null
  discount = null
  submitted = null
  unexpected = []
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url, 'http://localhost').pathname
    let data = null
    let status = 200
    if (path === '/api/auth/me') { data = account ?? { detail: 'Sign in required.' }; status = account ? 200 : 401 }
    else if (path === '/api/auth/login' || path === '/api/auth/register') { account = signInAccount; data = signInAccount }
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
  if (role) await screen.findByRole('navigation', { name: 'Workspace sections' })
  else await screen.findByRole('button', { name: 'Create my account' })
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

async function auditStructure(container) {
  const audit = await axe.run(container, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
    // jsdom cannot check rendered contrast, reflow or visible keyboard focus.
    rules: { 'color-contrast': { enabled: false } },
  })
  expect(audit.violations.map(({ id, nodes }) => ({ id, count: nodes.length }))).toEqual([])
}

test.each([null, 'rider', 'driver'])('%s workspace has named controls, valid references and no detected structural WCAG violations', async (role) => {
  const { container } = await ready(role)
  checkReferences(container)
  const links = role ? within(screen.getByRole('navigation', { name: 'Workspace sections' })).getAllByRole('link') : []
  for (const link of links) expect(document.querySelector(link.getAttribute('href'))?.tabIndex).toBe(-1)
  expect(links.some((link) => link.textContent === 'Wallet')).toBe(role === 'rider')
  expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1)
  expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull()
  await auditStructure(container)
})

test.each(['rider', 'driver'])('%s account, history and allowed wallet views retain valid accessible structure', async (role) => {
  const { container } = await ready(role)
  const user = userEvent.setup()
  const navigation = within(screen.getByRole('navigation', { name: 'Workspace sections' }))
  for (const label of [...(role === 'rider' ? ['Wallet'] : []), 'Ride history', 'Account']) {
    await user.click(navigation.getByRole('link', { name: label, exact: true }))
    expect(navigation.getByRole('link', { name: label, exact: true }).getAttribute('aria-current')).toBe('page')
    checkReferences(container)
    await auditStructure(container)
  }
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

test('header Login, Register and account controls open and focus the matching existing form', async () => {
  await ready(null)
  const user = userEvent.setup()
  const navigation = within(screen.getByRole('navigation', { name: 'Account navigation' }))
  await user.click(navigation.getByRole('button', { name: 'Login', exact: true }))
  expect(screen.queryByLabelText('Name')).toBeNull()
  expect(screen.getByLabelText('Password').autocomplete).toBe('current-password')
  await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Email')))
  await user.click(navigation.getByRole('button', { name: 'Register', exact: true }))
  expect(screen.getByLabelText('Password').autocomplete).toBe('new-password')
  await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Name')))
  await user.click(navigation.getByRole('button', { name: 'Account', exact: true }))
  expect(document.activeElement).toBe(screen.getByLabelText('Name'))
  await user.click(navigation.getByRole('button', { name: 'Login', exact: true }))
  await user.click(navigation.getByRole('button', { name: 'Login', exact: true }))
  expect(document.activeElement).toBe(screen.getByLabelText('Email'))
})

test('a restored account gets profile navigation and guest header actions return after account logout', async () => {
  await ready('rider')
  const user = userEvent.setup()
  const navigation = within(screen.getByRole('navigation', { name: 'Account navigation' }))
  expect(navigation.queryByRole('button', { name: 'Login', exact: true })).toBeNull()
  expect(navigation.queryByRole('button', { name: 'Register', exact: true })).toBeNull()
  await user.click(navigation.getByRole('button', { name: 'My account', exact: true }))
  await user.click(within(screen.getByRole('region', { name: 'Account options' })).getByRole('link', { name: 'View profile' }))
  expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Welcome, Test Rider.' }))
  await user.click(screen.getByRole('button', { name: 'Sign out', exact: true }))
  await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Your journey, your account.' })))
  expect(navigation.getByRole('button', { name: 'Login', exact: true })).toBeTruthy()
  expect(navigation.getByRole('button', { name: 'Register', exact: true })).toBeTruthy()
})

test.each(['rider', 'driver'])('%s navigation lives in the header and the profile disclosure supports keyboard and outside dismissal', async (role) => {
  const { container } = await ready(role)
  const user = userEvent.setup()
  const trigger = screen.getByRole('button', { name: 'My account', exact: true })
  expect(screen.getByRole('banner').contains(screen.getByRole('navigation', { name: 'Workspace sections' }))).toBe(true)
  expect(container.querySelector('.dashboard-sidebar')).toBeNull()
  trigger.focus()
  await user.keyboard('{Enter}')
  expect(trigger.getAttribute('aria-expanded')).toBe('true')
  const panel = within(screen.getByRole('region', { name: 'Account options' }))
  expect(panel.getByRole('heading', { name: role === 'rider' ? rider.name : driver.name })).toBeTruthy()
  expect(panel.queryByRole('link', { name: 'Wallet', exact: true }) !== null).toBe(role === 'rider')
  checkReferences(container)
  await auditStructure(container)
  await user.tab()
  expect(document.activeElement).toBe(panel.getByRole('link', { name: 'View profile' }))
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('region', { name: 'Account options' })).toBeNull()
  expect(document.activeElement).toBe(trigger)
  await user.click(trigger)
  await user.click(screen.getByRole('heading', { level: 1 }))
  expect(trigger.getAttribute('aria-expanded')).toBe('false')
})

test('profile shortcuts open real wallet, trip documents and connection-help views', async () => {
  await ready('rider')
  const user = userEvent.setup()
  const trigger = screen.getByRole('button', { name: 'My account', exact: true })
  for (const [name, title] of [['Wallet', 'Your wallet'], ['Trips & receipts', 'Your ride history']]) {
    await user.click(trigger)
    await user.click(within(screen.getByRole('region', { name: 'Account options' })).getByRole('link', { name, exact: true }))
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(title)
    expect(trigger.getAttribute('aria-expanded')).toBe('false')
  }
  await user.click(trigger)
  await user.click(within(screen.getByRole('region', { name: 'Account options' })).getByRole('button', { name: 'Help / connection', exact: true }))
  const summary = screen.getByText('Check the app connection')
  expect(summary.parentElement.open).toBe(true)
  expect(document.activeElement).toBe(summary)
  expect(trigger.getAttribute('aria-expanded')).toBe('false')
})

test('failed header logout preserves the session and a successful retry returns to sign-in', async () => {
  await ready('driver')
  const user = userEvent.setup()
  const trigger = screen.getByRole('button', { name: 'My account', exact: true })
  await user.click(trigger)
  fetch.mockImplementationOnce(async () => new Response(JSON.stringify({ detail: 'Sign out temporarily unavailable.' }), { status: 503 }))
  await user.click(within(screen.getByRole('region', { name: 'Account options' })).getByRole('button', { name: 'Sign out', exact: true }))
  const failure = await screen.findByRole('alert')
  expect(failure.textContent).toBe('Sign out temporarily unavailable.')
  await waitFor(() => expect(document.activeElement).toBe(failure))
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Driver dashboard')
  expect(account).toBe(driver)
  await user.click(within(screen.getByRole('region', { name: 'Account options' })).getByRole('button', { name: 'Sign out', exact: true }))
  await screen.findByRole('button', { name: 'Login', exact: true })
  expect(account).toBeNull()
  expect(screen.queryByRole('navigation', { name: 'Workspace sections' })).toBeNull()
  expect(screen.getByText('You have been signed out.')).toBeTruthy()
  await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Email')))
  expect(screen.getByLabelText('Password').autocomplete).toBe('current-password')
  const call = fetch.mock.calls.filter(([url]) => url === '/api/auth/logout').at(-1)[1]
  expect(call.method).toBe('POST')
  expect(call.credentials).toBe('same-origin')
})

test('rider navigation separates booking, wallet and history while preserving an unfinished route', async () => {
  await ready('rider')
  const user = userEvent.setup()
  const navigation = within(screen.getByRole('navigation', { name: 'Workspace sections' }))
  expect(navigation.getByRole('link', { name: 'Book a ride' }).getAttribute('aria-current')).toBe('page')
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Book your next ride')
  await user.click(screen.getByRole('button', { name: 'Use Delhi sample' }))
  const pickup = screen.getByLabelText('Pickup latitude')
  await user.clear(pickup)
  await user.type(pickup, '28.62')
  await user.click(navigation.getByRole('link', { name: 'Wallet' }))
  expect(screen.queryByRole('button', { name: 'Get fare estimate' })).toBeNull()
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Your wallet')
  expect(document.activeElement).toBe(document.getElementById('wallet'))
  expect(window.location.hash).toBe('#wallet')
  await user.click(navigation.getByRole('link', { name: 'Ride history' }))
  expect(screen.getByRole('button', { name: 'Refresh history' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: 'Refresh wallet' })).toBeNull()
  await user.click(navigation.getByRole('link', { name: 'Book a ride' }))
  expect(screen.getByLabelText('Pickup latitude').value).toBe('28.62')
  expect(document.activeElement).toBe(document.getElementById('booking'))
})

test('driver navigation preserves vehicle edits and exposes only driver sections', async () => {
  await ready('driver')
  const user = userEvent.setup()
  const navigation = within(screen.getByRole('navigation', { name: 'Workspace sections' }))
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Driver dashboard')
  expect(navigation.queryByRole('link', { name: 'Wallet' })).toBeNull()
  expect(navigation.queryByRole('link', { name: 'Book a ride' })).toBeNull()
  await user.clear(screen.getByLabelText('Make'))
  await user.type(screen.getByLabelText('Make'), 'My vehicle draft')
  await user.click(navigation.getByRole('link', { name: 'Ride history' }))
  expect(screen.queryByRole('button', { name: 'Save vehicle profile' })).toBeNull()
  const dashboard = navigation.getByRole('link', { name: 'Driver dashboard' })
  dashboard.focus()
  await user.keyboard('{Enter}')
  expect(screen.getByLabelText('Make').value).toBe('My vehicle draft')
  expect(document.activeElement).toBe(document.getElementById('driver'))
})

test.each(['rider', 'driver'])('%s restores a bookmarked history view and handles browser navigation', async (role) => {
  window.history.replaceState(null, '', '/#history')
  await ready(role)
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Your ride history')
  expect(screen.getByRole('link', { name: 'Ride history' }).getAttribute('aria-current')).toBe('page')
  window.history.replaceState(null, '', role === 'driver' ? '/#wallet' : '/#booking')
  window.dispatchEvent(new PopStateEvent('popstate'))
  await waitFor(() => expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(role === 'driver' ? 'Driver dashboard' : 'Book your next ride'))
  expect(document.activeElement).toBe(screen.getByRole('heading', { level: 1 }))
})

test.each(['rider', 'driver'])('successful %s sign-in opens the correct workspace and focuses its visible heading', async (role) => {
  await ready(null)
  signInAccount = role === 'driver' ? driver : rider
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Login', exact: true }))
  await user.type(screen.getByLabelText('Email'), signInAccount.email)
  await user.type(screen.getByLabelText('Password'), 'fixture-password')
  await user.keyboard('{Enter}')
  const title = await screen.findByRole('heading', { level: 1, name: role === 'driver' ? 'Driver dashboard' : 'Book your next ride' })
  await waitFor(() => expect(document.activeElement).toBe(title))
  expect(window.location.hash).toBe(role === 'driver' ? '#driver' : '#booking')
  expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull()
  expect(screen.getByRole('navigation', { name: 'Workspace sections' })).toBeTruthy()
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
  await user.click(screen.getByRole('link', { name: 'Ride history', exact: true }))
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

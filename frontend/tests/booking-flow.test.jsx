import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RideBooking from '../src/RideBooking.jsx'

const rider = { id: 'rider-fixture', role: 'rider' }
let quote, ride, requests, unexpected, estimateFailure

beforeEach(() => {
  quote = { quote_token: 'signed-quote-fixture', expires_at: new Date(Date.now() + 60000).toISOString(),
    fare_estimate: '104.38', distance_meters: 3982, duration_secs: 396,
    pickup: { latitude: 28.6139, longitude: 77.209 }, destination: { latitude: 28.6129, longitude: 77.2295 },
    breakdown: { base_fare: '50.00', distance_charge: '47.78', time_charge: '6.60', minimum_adjustment: '0.00' } }
  ride = null
  requests = []
  unexpected = []
  estimateFailure = null
  vi.stubGlobal('fetch', vi.fn(async (input, options = {}) => {
    const url = new URL(input, 'http://localhost')
    let data = null
    if (url.pathname === '/api/rides/current') data = ride
    else if (url.pathname === '/api/rides/estimate') {
      expect(url.searchParams.get('origin')).toBe('28.6139,77.2090')
      if (estimateFailure) return new Response(JSON.stringify({ detail: estimateFailure.message }), { status: estimateFailure.status })
      data = quote
    } else if (url.pathname === '/api/rides/request') {
      requests.push(JSON.parse(options.body))
      ride ??= { ...quote, id: 'saved-ride-fixture', status: 'requested', driver_id: null, created_at: new Date().toISOString() }
      // The server saved it but the first response was lost. Retry must reuse
      // the signed quote, rather than send a price or request another estimate.
      if (requests.length === 1) throw new TypeError('Controlled response loss')
      data = ride
    } else if (url.pathname === '/api/rides/saved-ride-fixture/status') data = ride
    else if (url.pathname === '/api/payments/config') data = { configured: false }
    else if (url.pathname.endsWith('/payment') || url.pathname.endsWith('/promo')) data = null
    else { unexpected.push(url.pathname); throw new Error('Unexpected fixture request') }
    return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  expect(unexpected).toEqual([])
})

async function sample(onSessionExpired = vi.fn()) {
  render(<RideBooking user={rider} liveRevision={0} onSessionExpired={onSessionExpired} />)
  await waitFor(() => expect(screen.queryByText('Checking your latest open ride…')).toBeNull())
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Use Delhi sample' }))
  return user
}

test('sample booking keeps its quote through response loss and restores completed-trip payment controls', async () => {
  const user = await sample()
  await user.click(screen.getByRole('button', { name: 'Get fare estimate' }))
  await user.click(await screen.findByRole('button', { name: 'Request this ride' }))
  await screen.findByText('Could not complete the request. Please try again; retries keep the same ride request.')
  await user.click(screen.getByRole('button', { name: 'Request this ride' }))
  await screen.findByRole('heading', { name: 'Status: requested' })
  expect(requests).toEqual([{ quote_token: quote.quote_token }, { quote_token: quote.quote_token }])
  ride = { ...ride, status: 'completed', driver_id: 'driver-fixture' }
  await user.click(screen.getByRole('button', { name: 'Refresh ride status' }))
  await screen.findByRole('heading', { name: 'Status: completed' })
  await screen.findByLabelText('Promo code (optional, before checkout)')
  expect(screen.queryByRole('button', { name: 'Request this ride' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Open test checkout' })).toBeNull()
})

test('estimate quota errors preserve inputs and a later expired session asks the account owner to sign in', async () => {
  const onSessionExpired = vi.fn()
  const user = await sample(onSessionExpired)
  estimateFailure = { status: 429, message: 'Too many requests. Please wait before trying again.' }
  await user.click(screen.getByRole('button', { name: 'Get fare estimate' }))
  await screen.findByText(estimateFailure.message)
  expect(screen.getByLabelText('Pickup latitude').value).toBe('28.6139')
  expect(screen.queryByRole('button', { name: 'Request this ride' })).toBeNull()
  expect(onSessionExpired).not.toHaveBeenCalled()
  estimateFailure = { status: 401, message: 'Please sign in again.' }
  await user.click(screen.getByRole('button', { name: 'Get fare estimate' }))
  await screen.findByText(estimateFailure.message)
  expect(onSessionExpired).toHaveBeenCalledWith(null)
})

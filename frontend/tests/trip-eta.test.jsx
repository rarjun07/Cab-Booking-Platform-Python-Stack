import { afterEach, expect, test, vi } from 'vitest'
import { act, cleanup, renderHook } from '@testing-library/react'
import useTripETA from '../src/useTripETA.js'

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })

test('ETA expires locally and polling stops after trip completion', async () => {
  vi.useFakeTimers()
  const now = Date.now()
  const fetcher = vi.fn(async () => new Response(JSON.stringify({ available: true, target: 'pickup',
    duration_secs: 180, distance_meters: 1234, location_updated_at: new Date(now).toISOString(),
    expires_at: new Date(now + 10000).toISOString() }), { status: 200 }))
  vi.stubGlobal('fetch', fetcher)
  const onSessionExpired = vi.fn()
  const ride = { id: 'trip', driver_id: 'driver', status: 'accepted' }
  const view = renderHook(({ trip }) => useTripETA(trip, onSessionExpired), { initialProps: { trip: ride } })
  expect(view.result.current.loading).toBe(true)
  await act(async () => { await vi.advanceTimersByTimeAsync(1200) })
  expect(view.result.current.available).toBe(true)
  expect(fetcher).toHaveBeenCalledTimes(1)
  await act(async () => { await vi.advanceTimersByTimeAsync(8811) })
  expect(view.result.current.available).toBe(false)
  view.rerender({ trip: { ...ride, status: 'completed' } })
  expect(view.result.current).toBeNull()
  await act(async () => { await vi.advanceTimersByTimeAsync(60000) })
  expect(fetcher).toHaveBeenCalledTimes(1)
})

test('ETA retries route failures without inventing a time and expires unauthorized sessions', async () => {
  vi.useFakeTimers()
  const onSessionExpired = vi.fn()
  const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Unavailable' }), { status: 503 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: 'Sign in' }), { status: 401 }))
  vi.stubGlobal('fetch', fetcher)
  const { result } = renderHook(() => useTripETA({ id: 'trip', driver_id: 'driver', status: 'arriving' }, onSessionExpired))
  await act(async () => { await vi.advanceTimersByTimeAsync(1200) })
  expect(result.current.error).toContain('ETA temporarily unavailable')
  expect(result.current.duration_secs).toBeUndefined()
  await act(async () => { await vi.advanceTimersByTimeAsync(15000) })
  expect(onSessionExpired).toHaveBeenCalledWith(null)
})

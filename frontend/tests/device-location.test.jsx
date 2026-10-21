import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import DeviceLocationControls from '../src/DeviceLocationControls.jsx'

let gps, point, watcher
beforeEach(() => {
  point = { coords: { latitude: 28.614, longitude: 77.209 } }
  gps = { getCurrentPosition: vi.fn(), watchPosition: vi.fn((fn) => { watcher = fn; return 42 }), clearWatch: vi.fn() }
  vi.stubGlobal('navigator', Object.assign(Object.create(navigator), { geolocation: gps }))
})
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })

test('device selection needs a click and does not publish a location', () => {
  const onSelect = vi.fn(), onShare = vi.fn()
  render(<DeviceLocationControls online={false} onSelect={onSelect} onShare={onShare} />)
  expect(gps.getCurrentPosition).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Use my device location' }))
  act(() => gps.getCurrentPosition.mock.calls[0][0](point))
  expect(onSelect).toHaveBeenCalledWith({ latitude: 28.614, longitude: 77.209 })
  expect(onShare).not.toHaveBeenCalled()
  expect(gps.watchPosition).not.toHaveBeenCalled()
})

test('live GPS is opt-in, throttled, and stops when offline or unmounted', async () => {
  vi.useFakeTimers()
  const onSelect = vi.fn(), onShare = vi.fn(async () => {})
  const view = render(<DeviceLocationControls online onSelect={onSelect} onShare={onShare} />)
  expect(gps.watchPosition).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Start live GPS sharing' }))
  await act(async () => { await watcher(point) })
  await act(async () => { await watcher(point) })
  expect(onShare).toHaveBeenCalledTimes(1)
  vi.advanceTimersByTime(15000)
  await act(async () => { await watcher(point) })
  expect(onShare).toHaveBeenCalledTimes(2)
  view.rerender(<DeviceLocationControls online={false} onSelect={onSelect} onShare={onShare} />)
  expect(gps.clearWatch).toHaveBeenCalledWith(42)
  await act(async () => { await watcher(point) })
  expect(onShare).toHaveBeenCalledTimes(2)
  view.unmount()
})

test('permission denial keeps manual coordinates available and starts no watcher', () => {
  render(<DeviceLocationControls online={false} onSelect={vi.fn()} onShare={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Use my device location' }))
  act(() => gps.getCurrentPosition.mock.calls[0][1]({ code: 1 }))
  expect(screen.getByRole('status').textContent).toContain('Location permission denied')
  expect(gps.watchPosition).not.toHaveBeenCalled()
})

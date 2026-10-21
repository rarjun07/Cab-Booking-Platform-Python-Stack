import { StrictMode } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import JourneyMap, { validPoint } from '../src/JourneyMap.jsx'

const engine = vi.hoisted(() => ({ maps: [], markers: [], lines: [], tiles: [] }))
vi.mock('leaflet', () => ({ default: {
  map: () => {
    const map = { handlers: {}, setView: vi.fn(() => map), on: vi.fn((name, fn) => { map.handlers[name] = fn; return map }),
      fitBounds: vi.fn(), invalidateSize: vi.fn(), remove: vi.fn() }
    engine.maps.push(map)
    return map
  },
  layerGroup: () => { const group = { addTo: () => group, clearLayers: vi.fn() }; return group },
  tileLayer: (url, options) => {
    const tile = { url, options, on: (name, fn) => { tile[name] = fn; return tile }, addTo: () => tile }
    engine.tiles.push(tile)
    return tile
  },
  divIcon: (options) => options,
  marker: (point, options) => {
    const marker = { point, options, bindPopup: () => marker, addTo: () => marker }
    engine.markers.push(marker)
    return marker
  },
  polyline: (points) => { engine.lines.push(points); return { addTo: vi.fn() } },
} }))

beforeEach(() => { engine.maps = []; engine.markers = []; engine.lines = []; engine.tiles = [] })
afterEach(cleanup)

test('map shows a road route in Leaflet coordinate order and exposes keyboard location selection', async () => {
  const onPick = vi.fn(), onPickMode = vi.fn()
  const view = render(<JourneyMap pickup={{ latitude: 28.61, longitude: 77.2 }}
    destination={{ latitude: 28.62, longitude: 77.3 }} geometry={{ type: 'LineString', coordinates: [[77.2, 28.61], [77.25, 28.615], [77.3, 28.62]] }}
    onPick={onPick} pickMode="pickup" onPickMode={onPickMode} />)
  expect(engine.lines[0]).toEqual([[28.61, 77.2], [28.615, 77.25], [28.62, 77.3]])
  expect(engine.markers.map((marker) => marker.point)).toEqual([[28.61, 77.2], [28.62, 77.3]])
  expect(engine.tiles[0].url).toBe('https://tile.openstreetmap.org/{z}/{x}/{y}.png')
  expect(engine.tiles[0].options.attribution).toContain('OpenStreetMap contributors')
  expect(engine.tiles[0].options.referrerPolicy).toBe('strict-origin-when-cross-origin')
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Set destination' }))
  expect(onPickMode).toHaveBeenCalledWith('destination')
  engine.maps[0].handlers.click({ latlng: { lat: 28.61234567, lng: 77.23456789 } })
  expect(onPick).toHaveBeenCalledWith({ latitude: 28.612346, longitude: 77.234568 })
  await user.click(screen.getByRole('button', { name: 'Fit map' }))
  expect(engine.maps[0].fitBounds).toHaveBeenCalled()
  view.rerender(<JourneyMap onPick={onPick} disabled />)
  onPick.mockClear()
  engine.maps[0].handlers.click({ latlng: { lat: 28.6, lng: 77.2 } })
  expect(onPick).not.toHaveBeenCalled()
})

test('StrictMode unmount cleans maps and invalid coordinates never become markers', () => {
  const view = render(<StrictMode><JourneyMap pickup={{ latitude: '', longitude: '' }}
    destination={{ latitude: 91, longitude: 0 }} /></StrictMode>)
  expect(engine.maps).toHaveLength(2)
  expect(engine.maps[0].remove).toHaveBeenCalledOnce()
  expect(engine.markers).toHaveLength(0)
  expect(validPoint({ latitude: 0, longitude: 0 })).toBe(true)
  expect(validPoint({ latitude: Infinity, longitude: 0 })).toBe(false)
  view.unmount()
  expect(engine.maps[1].remove).toHaveBeenCalledOnce()
})

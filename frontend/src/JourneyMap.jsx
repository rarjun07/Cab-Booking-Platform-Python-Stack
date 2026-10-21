import { useEffect, useId, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export function validPoint(point) {
  return point && point.latitude !== '' && point.longitude !== '' &&
    point.latitude != null && point.longitude != null &&
    Number.isFinite(Number(point.latitude)) && Number.isFinite(Number(point.longitude)) &&
    Math.abs(Number(point.latitude)) <= 90 && Math.abs(Number(point.longitude)) <= 180
}

const latLng = (point) => [Number(point.latitude), Number(point.longitude)]

export default function JourneyMap({ pickup, destination, driver, selection, geometry, approachGeometry, onPick,
  pickMode, onPickMode, disabled = false, title = 'Journey map' }) {
  const id = useId()
  const container = useRef(null)
  const instance = useRef(null)
  const layers = useRef(null)
  const points = useRef([])
  const pick = useRef(null)
  pick.current = disabled ? null : onPick
  const [tileError, setTileError] = useState(false)
  const [mapError, setMapError] = useState(false)
  const focusKey = JSON.stringify([pickup, destination, selection, !pickup && !destination ? driver : null])

  useEffect(() => {
    let map, observer
    function resize() { map?.invalidateSize({ pan: false }) }
    try {
      map = L.map(container.current, { scrollWheelZoom: false }).setView([28.6139, 77.209], 12)
      instance.current = map
      layers.current = L.layerGroup().addTo(map)
      L.tileLayer(import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        referrerPolicy: 'strict-origin-when-cross-origin',
        attribution: import.meta.env.VITE_MAP_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
      }).on('tileerror', () => setTileError(true)).addTo(map)
      map.on('click', ({ latlng }) => pick.current?.({ latitude: Number(latlng.lat.toFixed(6)), longitude: Number(latlng.lng.toFixed(6)) }))
      if (typeof ResizeObserver !== 'undefined') {
        observer = new ResizeObserver(resize)
        observer.observe(container.current)
      }
      window.addEventListener('resize', resize)
    } catch {
      setMapError(true)
    }
    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', resize)
      map?.remove()
      instance.current = null
      layers.current = null
    }
  }, [])

  useEffect(() => {
    const group = layers.current
    if (!group) return
    group.clearLayers()
    points.current = []
    for (const [point, label, letter, kind] of [
      [pickup, 'Pickup', 'P', 'pickup'], [destination, 'Destination', 'A', 'destination'],
      [driver, 'Last shared driver location', 'D', 'driver'], [selection, 'Selected location (not shared yet)', 'S', 'selection'],
    ]) {
      if (!validPoint(point)) continue
      const coordinate = latLng(point)
      points.current.push(coordinate)
      const text = document.createElement('span')
      text.textContent = label
      L.marker(coordinate, { title: label, alt: label, icon: L.divIcon({
        className: `journey-marker journey-marker-${kind}`, html: `<span>${letter}</span>`, iconSize: [32, 32], iconAnchor: [16, 32],
      }) }).bindPopup(text).addTo(group)
    }
    if (geometry?.type === 'LineString' && geometry.coordinates?.length >= 2) {
      // GeoJSON longitude,latitude -> Leaflet latitude,longitude.
      L.polyline(geometry.coordinates.map(([lng, lat]) => [lat, lng]), { color: '#32543b', weight: 5, opacity: .9 }).addTo(group)
    }
    if (approachGeometry?.type === 'LineString' && approachGeometry.coordinates?.length >= 2) {
      L.polyline(approachGeometry.coordinates.map(([lng, lat]) => [lat, lng]), { color: '#172a28', weight: 4, dashArray: '8 8' }).addTo(group)
    }
  }, [pickup, destination, driver, selection, geometry, approachGeometry])

  function fit() {
    const map = instance.current
    if (!map || !points.current.length) return
    map.invalidateSize({ pan: false })
    const path = geometry?.coordinates?.map(([lng, lat]) => [lat, lng]) ?? []
    map.fitBounds([...points.current, ...path], { padding: [36, 36], maxZoom: 15, animate: false })
  }

  useEffect(() => { fit() }, [focusKey, geometry])

  return <section className="journey-map-card" aria-labelledby={`${id}-title`}>
    <div className="matching-title"><h4 id={`${id}-title`}>{title}</h4><button type="button" className="secondary-button" onClick={fit}>Fit map</button></div>
    {onPickMode && <div className="map-pick-controls" aria-label="Choose a location to set on the map">
      {['pickup', 'destination'].map((mode) => <button type="button" key={mode} disabled={disabled} aria-pressed={pickMode === mode} onClick={() => onPickMode(mode)}>Set {mode}</button>)}
    </div>}
    <p id={`${id}-help`} className="fare-note">{onPick ? `Click the map to set ${pickMode || 'your location'}, or use the coordinate fields. ` : ''}Use arrow keys to pan and + / − to zoom. Markers: P pickup · A destination · D last shared driver · S selected location. Dashed line: driver route to the next stop.</p>
    <div className="journey-map" ref={container} role="region" aria-label={title} aria-describedby={`${id}-help`} />
    {(mapError || tileError) && <p role="status" className="fare-note">{mapError ? 'Map unavailable.' : 'Some map tiles could not load.'} Coordinate fields and ride controls remain available.</p>}
    <p className="fare-note map-disclosure">Map tiles load from OpenStreetMap and reveal the viewed area to the tile provider. Delhi is the default view, not your device location. <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">Report a map issue</a>.</p>
  </section>
}

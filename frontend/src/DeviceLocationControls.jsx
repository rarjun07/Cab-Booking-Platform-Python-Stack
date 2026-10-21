import { useEffect, useRef, useState } from 'react'
import { validPoint } from './JourneyMap.jsx'

const options = { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }
const errorText = (error) => error?.code === 1 ? 'Location permission denied. You can still enter coordinates manually.'
  : 'Could not get a fresh device location. Try again outdoors, or enter coordinates manually.'

export default function DeviceLocationControls({ online, disabled, onSelect, onShare }) {
  const [tracking, setTracking] = useState(false)
  const [locating, setLocating] = useState(false)
  const [message, setMessage] = useState('')
  const mounted = useRef(true)
  const callbacks = useRef({ onSelect, onShare })
  callbacks.current = { onSelect, onShare }
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])

  function select(position) {
    const point = { latitude: position.coords.latitude, longitude: position.coords.longitude }
    if (!validPoint(point)) throw new Error('Invalid location')
    callbacks.current.onSelect(point)
    return point
  }

  function locate() {
    if (!navigator.geolocation) { setMessage('Device location is unavailable. Enter coordinates manually.'); return }
    setLocating(true)
    setMessage('Requesting device location…')
    navigator.geolocation.getCurrentPosition((position) => {
      if (!mounted.current) return
      try { select(position); setMessage('Location selected. Choose Go online or Share updated location to send it.') }
      catch { setMessage('The device returned an invalid location. Enter coordinates manually.') }
      setLocating(false)
    }, (error) => {
      if (mounted.current) { setMessage(errorText(error)); setLocating(false) }
    }, options)
  }

  useEffect(() => {
    if (!tracking || !online) { setTracking(false); return }
    if (!navigator.geolocation) { setMessage('Device location is unavailable.'); setTracking(false); return }
    let active = true, sending = false, lastSent = -Infinity
    const watcher = navigator.geolocation.watchPosition(async (position) => {
      if (!active || sending || Date.now() - lastSent < 15000) return
      sending = true
      lastSent = Date.now()
      try {
        const point = select(position)
        await callbacks.current.onShare(point)
        if (active) setMessage('Live GPS location shared. Updates are limited to one every 15 seconds.')
      } catch {
        if (active) { setMessage('Live GPS sharing failed and stopped. Check your connection and online status before retrying.'); setTracking(false) }
      } finally { sending = false }
    }, (error) => { if (active) { setMessage(errorText(error)); setTracking(false) } }, options)
    return () => { active = false; navigator.geolocation.clearWatch(watcher) }
  }, [tracking, online])

  return <div className="device-location-controls">
    <div className="auth-actions">
      <button type="button" className="secondary-button" disabled={disabled || locating || tracking} onClick={locate}>{locating ? 'Locating…' : 'Use my device location'}</button>
      {online && <button type="button" className="secondary-button" disabled={disabled} aria-pressed={tracking} onClick={() => {
        setTracking(!tracking)
        setMessage(tracking ? 'Live GPS sharing stopped. Your last shared point expires normally; Go offline clears it now.' : 'Requesting permission for live GPS sharing…')
      }}>{tracking ? 'Stop live GPS sharing' : 'Start live GPS sharing'}</button>}
    </div>
    <p className="fare-note">Device location needs your browser permission and localhost or HTTPS. Live sharing sends your position to this app for matching and your assigned rider. Stop sharing or go offline when finished.</p>
    <p role="status" className="fare-note">{message}</p>
  </div>
}

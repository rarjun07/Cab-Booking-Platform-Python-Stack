import { useEffect, useId, useRef, useState } from 'react'
import JourneyMap from './JourneyMap.jsx'
import useRoadRoute from './useRoadRoute.js'

const formatMoney = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value))
const tripSteps = { accepted: ['arriving', 'Head to pickup'], arriving: ['in_progress', 'Start trip'], in_progress: ['completed', 'Complete trip'] }

async function driverRequest(path, { method = 'GET', body, signal } = {}) {
  const response = await fetch(`/api/drivers/me${path}`, {
    method,
    credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000),
  })
  if (response.status === 204) return null
  const data = await response.json()
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Check your driver details and try again.')
    error.status = response.status
    throw error
  }
  return data
}

export default function DriverDashboard({ onSessionExpired, live }) {
  const formId = useId()
  const mounted = useRef(true)
  const formsInitialized = useRef(false)
  const [profile, setProfile] = useState(null)
  const [vehicle, setVehicle] = useState({ make: '', model: '', plate: '' })
  const [location, setLocation] = useState({ latitude: '', longitude: '' })
  const [offers, setOffers] = useState([])
  const [ride, setRide] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)
  const [now, setNow] = useState(Date.now())
  const fresh = profile?.status === 'active' && new Date(profile.location_expires_at).getTime() > now
  const nextStep = tripSteps[ride?.status]
  const roadRoute = useRoadRoute(ride, onSessionExpired)

  useEffect(() => {
    mounted.current = true
    const controller = new AbortController()
    async function restore() {
      try {
        const [saved, current] = await Promise.all([
          driverRequest('', { signal: controller.signal }),
          driverRequest('/ride', { signal: controller.signal }),
        ])
        const nearby = saved ? await driverRequest('/offers', { signal: controller.signal }) : []
        if (controller.signal.aborted) return
        setProfile(saved)
        if (saved) {
          formsInitialized.current = true
          setVehicle({ make: saved.vehicle_info.make ?? '', model: saved.vehicle_info.model ?? '', plate: saved.vehicle_info.plate ?? '' })
          if (saved.current_location) setLocation(saved.current_location)
        }
        setRide(current)
        setOffers(nearby)
      } catch (error) {
        if (controller.signal.aborted) return
        if (error.status === 401) onSessionExpired(null)
        setIsError(true)
        setMessage(error.status ? error.message : 'Could not load the dashboard. Try Refresh dashboard.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    restore()
    return () => { mounted.current = false; controller.abort() }
  }, [onSessionExpired])

  useEffect(() => {
    setNow(Date.now())
    if (!profile?.location_expires_at) return
    const delay = new Date(profile.location_expires_at).getTime() - Date.now()
    if (delay <= 0) { setOffers([]); return }
    const timer = setTimeout(() => { setNow(Date.now()); setOffers([]) }, delay + 10)
    return () => clearTimeout(timer)
  }, [profile])

  async function reloadDashboard(signal) {
    const [saved, current] = await Promise.all([driverRequest('', { signal }), driverRequest('/ride', { signal })])
    const nearby = saved ? await driverRequest('/offers', { signal }) : []
    if (!mounted.current || signal?.aborted) return
    setProfile(saved)
    if (saved && !formsInitialized.current) {
      setVehicle({ make: saved.vehicle_info.make ?? '', model: saved.vehicle_info.model ?? '', plate: saved.vehicle_info.plate ?? '' })
      if (saved.current_location) setLocation(saved.current_location)
      formsInitialized.current = true
    }
    setRide(current)
    setOffers(nearby)
  }

  useEffect(() => {
    if (!live.revision || busy || loading) return
    const controller = new AbortController()
    reloadDashboard(controller.signal).catch((error) => {
      if (controller.signal.aborted) return
      if (error.status === 401) onSessionExpired(null)
      setIsError(true)
      setMessage('Could not refresh live ride data. Try Refresh dashboard.')
    })
    return () => controller.abort()
  }, [live.revision, busy, loading, onSessionExpired])

  async function perform(action, successMessage) {
    setBusy(true)
    setMessage('')
    setIsError(false)
    try {
      await action()
      await reloadDashboard()
      if (mounted.current) setMessage(successMessage)
    } catch (error) {
      if (!mounted.current) return
      if (error.status === 401) onSessionExpired(null)
      setIsError(true)
      setMessage(error.status ? error.message : 'Could not finish the request. Refresh the dashboard before retrying.')
      // An offer can become unavailable between refresh and acceptance.
      if (error.status === 409) setOffers([])
    } finally {
      if (mounted.current) setBusy(false)
    }
  }

  function saveVehicle(event) {
    event.preventDefault()
    perform(() => driverRequest('', { method: 'PUT', body: { vehicle_info: vehicle } }), 'Vehicle profile saved.')
  }

  function goOnline(event) {
    event.preventDefault()
    perform(() => driverRequest('/availability', { method: 'POST', body: {
      status: 'active', location: { latitude: Number(location.latitude), longitude: Number(location.longitude) },
    } }), 'Location updated. You are online for nearby requests.')
  }

  function shareLocation() {
    if (location.latitude === '' || location.longitude === '' || !Number.isFinite(Number(location.latitude)) || !Number.isFinite(Number(location.longitude))) {
      setIsError(true)
      setMessage('Enter valid latitude and longitude before sharing.')
      return
    }
    const point = { latitude: Number(location.latitude), longitude: Number(location.longitude) }
    perform(() => live.status === 'connected' ? live.sendLocation(point) : driverRequest('/location', { method: 'POST', body: { location: point } }), 'Location updated.')
  }

  return (
    <section id="driver" tabIndex={-1} className="driver-card dashboard-module" aria-labelledby="driver-title" aria-busy={loading || busy}>
      <h2 id="driver-title" className="visually-hidden">Your driving workspace</h2>
      {loading ? <p role="status">Loading your driver dashboard…</p> : <>
        <div className="auth-card driver-toolbar">
          <div className="driver-status">
          <span className={`availability-badge${fresh && !ride ? ' availability-online' : ''}`}>
            {ride ? 'On a ride' : fresh ? 'Online' : profile?.status === 'active' ? 'Location expired' : 'Offline'}
          </span>
          <span className="fare-note">{ride ? 'Your current trip is assigned to you.' : fresh ? 'Ready for nearby requests.' : 'Go online when you’re ready to drive.'}</span>
          </div>
          <button className="secondary-button" type="button" disabled={busy} onClick={() => perform(async () => {}, 'Dashboard refreshed.')}>Refresh dashboard</button>
        </div>
        <div className="driver-layout">
        <div className="driver-settings">
        <form className="auth-card driver-vehicle-card" onSubmit={saveVehicle}>
          <fieldset disabled={busy}>
            <legend className="driver-section-title">Your vehicle</legend>
            <div className="vehicle-grid">
              {[['make', 'Make', 2, 50], ['model', 'Model', 1, 50], ['plate', 'Number plate', 3, 20]].map(([key, label, min, max]) => (
                <div className="form-field" key={key}><label htmlFor={`${formId}-${key}`}>{label}</label><input id={`${formId}-${key}`} value={vehicle[key]} minLength={min} maxLength={max} onChange={(event) => setVehicle({ ...vehicle, [key]: event.target.value })} required /></div>
              ))}
            </div>
            <button className="submit-button" type="submit">Save vehicle profile</button>
          </fieldset>
          {profile && <p className="fare-note driver-demo-note">{profile.verified ? 'Vehicle marked verified.' : 'Vehicle not verified. This learning demo allows unverified profiles; saving a vehicle does not verify it.'}</p>}
        </form>
        {profile && <>
          <form className="auth-card driver-location-form" onSubmit={goOnline}>
            <fieldset disabled={busy}>
              <legend className="driver-section-title">Your availability</legend>
              <div className="route-grid">
                {[['latitude', 'Current latitude', -90, 90], ['longitude', 'Current longitude', -180, 180]].map(([key, label, min, max]) => (
                  <div className="form-field" key={key}><label htmlFor={`${formId}-${key}`}>{label}</label><input id={`${formId}-${key}`} type="number" step="any" min={min} max={max} value={location[key]} onChange={(event) => setLocation({ ...location, [key]: event.target.value })} required /></div>
                ))}
              </div>
              <div className="auth-actions">
                <button className="secondary-button" type="button" onClick={() => setLocation({ latitude: '28.6140', longitude: '77.2090' })}>Use Delhi sample location</button>
                <button type="submit">{profile.status === 'active' ? 'Refresh location / go online' : 'Go online'}</button>
                {profile.status === 'active' && <button type="button" onClick={shareLocation}>Share updated location</button>}
                <button className="secondary-button" type="button" onClick={() => perform(() => driverRequest('/availability', { method: 'POST', body: { status: 'offline' } }), 'You are offline. Any accepted ride stays assigned.')}>Go offline</button>
              </div>
            </fieldset>
          <p className="fare-note driver-demo-note">Your location is shared with our backend for nearby matching. Refresh it before it expires{profile.location_expires_at ? ` at ${new Date(profile.location_expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}. Going offline stops new offers and clears this location.</p>
          {profile.current_location && <p className="fare-note driver-demo-note">Last shared: {profile.current_location.latitude}, {profile.current_location.longitude}. Edit the coordinates above and choose Share updated location to send a new point.</p>}
          </form>
        </>}
        </div>
          <div className="auth-card driver-requests">
            <div className="matching-title">
              <h3>{ride ? 'Your accepted ride' : 'Nearby ride requests'}</h3>
              <span>{ride ? '1 current trip' : `${offers.length} ${offers.length === 1 ? 'request' : 'requests'}`}</span>
            </div>
            {ride ? <div className="fare-summary" role="status">
              <p className="eyebrow">{ride.status.replaceAll('_', ' ')}</p>
              <p className="ride-reference">Reference: {ride.id}</p>
              <p>Pickup: {ride.pickup.latitude}, {ride.pickup.longitude}</p>
              <p>Destination: {ride.destination.latitude}, {ride.destination.longitude}</p>
              <p>Estimated fare: {formatMoney(ride.fare_estimate)}</p>
              <p className="fare-note">This ride is assigned to you. Update its progress when you reach each step. After completion, the rider can open test checkout.</p>
              {nextStep && <button type="button" disabled={busy} onClick={() => perform(() => driverRequest(`/rides/${ride.id}/status`, { method: 'POST', body: { status: nextStep[0] } }), 'Trip status updated.')}>{nextStep[1]}</button>}
            </div> : !fresh || offers.length === 0 ? <div className="dashboard-empty-state">
              <span className="empty-state-mark" aria-hidden="true">↗</span>
              <h4>{!profile ? 'Set up your vehicle to get started' : !fresh ? 'You’re not receiving requests yet' : 'You’re ready for your next pickup'}</h4>
              <p>{!profile ? 'Save your vehicle details, then share your location and go online.' : !fresh ? 'Go online with a fresh location to see nearby requests.' : 'No nearby requests right now. Refresh the dashboard to check again.'}</p>
            </div> : <ul className="matching-list">
              {offers.map(({ ride: offer, pickup_distance_meters: distance }) => <li key={offer.id}>
                <div className="matching-title"><h4>{formatMoney(offer.fare_estimate)}</h4><span>{(distance / 1000).toFixed(2)} km to pickup</span></div>
                <p>Pickup: {offer.pickup.latitude}, {offer.pickup.longitude}</p>
                <p>Destination: {offer.destination.latitude}, {offer.destination.longitude}</p>
                <p className="ride-reference">{offer.id}</p>
                <div className="auth-actions"><button type="button" disabled={busy} onClick={() => perform(() => driverRequest(`/rides/${offer.id}/accept`, { method: 'POST' }), 'Ride accepted and assigned to you.')}>Accept ride</button><button className="secondary-button" type="button" disabled={busy} onClick={() => perform(() => driverRequest(`/rides/${offer.id}/decline`, { method: 'POST' }), 'Request declined. It remains available to other nearby drivers.')}>Decline ride</button></div>
              </li>)}
            </ul>}
            {fresh && !ride && <p className="fare-note driver-demo-note">Pickup distances are geographic distances, not driving distances or traffic ETAs.</p>}
          </div>
          <JourneyMap title="Driver journey map" pickup={ride?.pickup} destination={ride?.destination}
            driver={fresh ? profile.current_location : null} selection={profile ? location : null}
            geometry={roadRoute?.geometry} disabled={busy || !profile} onPick={profile ? setLocation : undefined} />
          {roadRoute?.error && <p className="fare-note" role="status">Road preview unavailable: {roadRoute.error} Your trip controls remain available.</p>}
        </div>
      </>}
      <p className={`auth-message${isError ? ' auth-error' : ''}`} role="status" aria-live="polite" aria-atomic="true">{message}</p>
    </section>
  )
}

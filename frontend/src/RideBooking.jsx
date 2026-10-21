import { useEffect, useId, useRef, useState } from 'react'
import RidePayment from './RidePayment.jsx'
import JourneyMap from './JourneyMap.jsx'
import useRoadRoute from './useRoadRoute.js'
import useTripETA from './useTripETA.js'
import TripETA from './TripETA.jsx'

const emptyRoute = { pickupLat: '', pickupLng: '', destinationLat: '', destinationLng: '' }
const sampleRoute = { pickupLat: '28.6139', pickupLng: '77.2090', destinationLat: '28.6129', destinationLng: '77.2295' }
const formatMoney = (value) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Number(value))

async function rideRequest(path, body, signal) {
  const response = await fetch(`/api/rides/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000),
  })
  const data = await response.json()
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Check your route details and try again.')
    error.status = response.status
    throw error
  }
  return data
}

async function readDriverLocation(ride, signal) {
  return ride?.driver_id && ['accepted', 'arriving', 'in_progress'].includes(ride.status)
    ? rideRequest(`${ride.id}/driver-location`, undefined, signal) : null
}

export default function RideBooking({ user, onSessionExpired, liveRevision = 0 }) {
  const formId = useId()
  const [route, setRoute] = useState(emptyRoute)
  const [quote, setQuote] = useState(null)
  const [ride, setRide] = useState(null)
  const rideRef = useRef(null)
  rideRef.current = ride
  const [driverLocation, setDriverLocation] = useState(null)
  const [nearbyDrivers, setNearbyDrivers] = useState([])
  const [matchingChecked, setMatchingChecked] = useState(false)
  const [restoring, setRestoring] = useState(user?.role === 'rider')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)
  const [pickMode, setPickMode] = useState('pickup')
  const savedRoute = useRoadRoute(ride, onSessionExpired)
  const calculatedETA = useTripETA(ride, onSessionExpired)
  const hasDraft = Object.values(route).some((value) => value !== '')
  const showRide = ride && (!hasDraft || (Number(route.pickupLat) === ride.pickup.latitude &&
    Number(route.pickupLng) === ride.pickup.longitude && Number(route.destinationLat) === ride.destination.latitude &&
    Number(route.destinationLng) === ride.destination.longitude))
  const mapTrip = quote || (showRide ? ride : null)
  const pickup = mapTrip?.pickup ?? { latitude: route.pickupLat, longitude: route.pickupLng }
  const destination = mapTrip?.destination ?? { latitude: route.destinationLat, longitude: route.destinationLng }
  const [now, setNow] = useState(Date.now())
  const sharedFresh = Boolean(driverLocation?.location && driverLocation.ride_id === ride?.id && new Date(driverLocation.expires_at).getTime() > now)
  const eta = calculatedETA?.available && !sharedFresh ? { available: false } : calculatedETA

  useEffect(() => {
    setNow(Date.now())
    if (!driverLocation?.expires_at) return
    const timer = setTimeout(() => setNow(Date.now()), Math.max(0, new Date(driverLocation.expires_at).getTime() - Date.now()) + 10)
    return () => clearTimeout(timer)
  }, [driverLocation])

  useEffect(() => {
    if (user?.role !== 'rider') return
    const controller = new AbortController()
    rideRequest('current', undefined, controller.signal).then(async (saved) => {
      if (controller.signal.aborted) return
      setRide(saved)
      const location = await readDriverLocation(saved, controller.signal)
      if (!controller.signal.aborted) setDriverLocation(location)
    }).catch((error) => {
      if (controller.signal.aborted) return
      if (error.status === 401) onSessionExpired(null)
      setIsError(true)
      setMessage(error.status ? error.message : 'Could not restore your latest open ride. Refresh the page to retry.')
    }).finally(() => { if (!controller.signal.aborted) setRestoring(false) })
    return () => controller.abort()
  }, [user?.id, user?.role, onSessionExpired])

  useEffect(() => {
    if (user?.role !== 'rider' || !liveRevision || restoring || busy) return
    const controller = new AbortController()
    const previousId = rideRef.current?.id
    async function sync() {
      const latest = await rideRequest('current', undefined, controller.signal)
      const saved = latest ?? (previousId ? await rideRequest(`${previousId}/status`, undefined, controller.signal) : null)
      const location = await readDriverLocation(saved, controller.signal)
      const candidates = matchingChecked && saved?.status === 'requested'
        ? await rideRequest(`${saved.id}/drivers`, undefined, controller.signal) : []
      if (controller.signal.aborted || rideRef.current?.id !== previousId) return
      setRide(saved)
      setDriverLocation(location)
      setNearbyDrivers(candidates)
      if (saved?.status !== 'requested') setMatchingChecked(false)
    }
    sync().catch((error) => {
      if (controller.signal.aborted) return
      if (error.status === 401) onSessionExpired(null)
      setIsError(true)
      setMessage('Could not refresh live ride data. Try Refresh ride status.')
    })
    return () => controller.abort()
  }, [liveRevision, user?.id, user?.role, restoring, busy, matchingChecked, onSessionExpired])

  useEffect(() => {
    if (!quote) return
    const timer = setTimeout(() => {
      setQuote(null)
      setMessage('Your estimate expired. Get a new estimate to continue.')
    }, Math.max(0, new Date(quote.expires_at).getTime() - Date.now()))
    return () => clearTimeout(timer)
  }, [quote])

  function changeRoute(next) {
    setRoute(next)
    setQuote(null)
    setNearbyDrivers([])
    setMatchingChecked(false)
    setMessage('')
  }

  function showError(error) {
    if (error.status === 401) onSessionExpired(null)
    setIsError(true)
    setMessage(error.status ? error.message : 'Could not complete the request. Please try again; retries keep the same ride request.')
  }

  async function estimate(event) {
    event.preventDefault()
    setBusy(true)
    setMessage('')
    setIsError(false)
    setQuote(null)
    setNearbyDrivers([])
    setMatchingChecked(false)
    const parameters = new URLSearchParams({ origin: `${route.pickupLat},${route.pickupLng}`, dest: `${route.destinationLat},${route.destinationLng}` })
    try {
      setQuote(await rideRequest(`estimate?${parameters}`))
    } catch (error) {
      showError(error)
    } finally {
      setBusy(false)
    }
  }

  async function book() {
    if (!quote || Date.now() >= new Date(quote.expires_at).getTime()) {
      setQuote(null)
      setMessage('Get a fresh estimate before requesting a ride.')
      return
    }
    setBusy(true)
    setIsError(false)
    setMessage('')
    try {
      setRide(await rideRequest('request', { quote_token: quote.quote_token }))
      setQuote(null)
      setMessage('Your ride request has been saved.')
    } catch (error) {
      showError(error)
    } finally {
      setBusy(false)
    }
  }

  async function refreshStatus() {
    setBusy(true)
    setIsError(false)
    try {
      const saved = await rideRequest(`${ride.id}/status`)
      setRide(saved)
      setDriverLocation(await readDriverLocation(saved))
      setNearbyDrivers([])
      setMatchingChecked(false)
      setMessage('Ride status refreshed.')
    } catch (error) {
      showError(error)
    } finally {
      setBusy(false)
    }
  }

  async function findDrivers() {
    setBusy(true)
    setIsError(false)
    setMessage('')
    try {
      setNearbyDrivers(await rideRequest(`${ride.id}/drivers`))
      setMatchingChecked(true)
    } catch (error) {
      showError(error)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section id="booking" tabIndex={-1} className="booking-card dashboard-module" aria-labelledby="booking-title">
      <h2 id="booking-title" className="visually-hidden">Plan your ride</h2>
      {!user ? <p className="auth-description">Sign in above to estimate and request a ride.</p> : user.role !== 'rider' ? <p className="auth-description">You’re signed in as a driver. Ride requests are available to rider accounts.</p> : (
        <div className="booking-layout">
          <div className="auth-card booking-route-card">
          <p className="eyebrow">PLAN YOUR RIDE</p>
          <h3>Pickup & destination</h3>
          <p className="auth-description">Enter coordinates, or try our public Delhi sample route.</p>
          <form onSubmit={estimate} aria-busy={busy}>
            <fieldset disabled={busy || restoring}>
              {[
                ['Pickup location', [['pickupLat', 'Pickup latitude', -90, 90], ['pickupLng', 'Pickup longitude', -180, 180]]],
                ['Destination', [['destinationLat', 'Destination latitude', -90, 90], ['destinationLng', 'Destination longitude', -180, 180]]],
              ].map(([title, fields], index) => <fieldset className="route-stop" key={title}>
                <legend><span className="route-stop-number" aria-hidden="true">{index + 1}</span>{title}</legend>
                <div className="route-grid">{fields.map(([key, label, min, max]) => (
                  <div className="form-field" key={key}><label htmlFor={`${formId}-${key}`}>{label}</label><input id={`${formId}-${key}`} name={key} type="number" step="any" min={min} max={max} value={route[key]} onChange={(event) => changeRoute({ ...route, [key]: event.target.value })} required /></div>
                ))}</div>
              </fieldset>)}
              <div className="auth-actions booking-actions"><button className="secondary-button" type="button" onClick={() => changeRoute(sampleRoute)}>Use Delhi sample</button><button type="submit">{busy ? 'Please wait…' : 'Get fare estimate'}</button></div>
            </fieldset>
          </form>
          <p className="route-attribution">Routing by <a href="https://project-osrm.org/" target="_blank" rel="noreferrer">OSRM</a> · Data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a> · <a href="https://www.openstreetmap.org/fixthemap" target="_blank" rel="noreferrer">Fix the map</a>. These coordinates are sent to the public routing service when you request an estimate.</p>
          </div>
          <aside className="auth-card booking-summary-card" aria-label="Estimate and current ride">
          <p className="eyebrow">YOUR JOURNEY</p>
          <h3>Your trip at a glance</h3>
          <JourneyMap pickup={pickup} destination={destination}
            driver={ride && mapTrip === ride && driverLocation?.ride_id === ride.id && new Date(driverLocation.expires_at).getTime() > now ? driverLocation.location : null}
            geometry={quote?.geometry ?? (showRide ? savedRoute?.geometry : null)} approachGeometry={mapTrip === ride && eta?.available ? eta.geometry : null} pickMode={pickMode} onPickMode={setPickMode} disabled={busy || restoring}
            onPick={(point) => {
              const prefix = pickMode === 'pickup' ? 'pickup' : 'destination'
              changeRoute({ ...route, [`${prefix}Lat`]: String(point.latitude), [`${prefix}Lng`]: String(point.longitude) })
            }} />
          {!quote && savedRoute?.error && <p className="fare-note" role="status">Road preview unavailable: {savedRoute.error} Your saved ride is unchanged.</p>}
          {!quote && !ride && !restoring && <div className="dashboard-empty-state">
            <span className="empty-state-mark" aria-hidden="true">↗</span>
            <h4>Your next journey starts here</h4>
            <p>Choose your pickup and destination to see the route estimate and fare. Your saved ride will appear here.</p>
          </div>}
          {quote && <div className="fare-summary">
            <p className="eyebrow">YOUR ESTIMATE</p>
            <p className="fare-total">{formatMoney(quote.fare_estimate)}</p>
            <p>{(quote.distance_meters / 1000).toFixed(2)} km · About {Math.ceil(quote.duration_secs / 60)} minutes driving</p>
            <dl className="fare-breakdown"><div><dt>Base fare</dt><dd>{formatMoney(quote.breakdown.base_fare)}</dd></div><div><dt>Distance</dt><dd>{formatMoney(quote.breakdown.distance_charge)}</dd></div><div><dt>Travel time</dt><dd>{formatMoney(quote.breakdown.time_charge)}</dd></div>{Number(quote.breakdown.minimum_adjustment) > 0 && <div><dt>Minimum fare adjustment</dt><dd>{formatMoney(quote.breakdown.minimum_adjustment)}</dd></div>}</dl>
            <p className="fare-note">Sample project pricing. Expires at {new Date(quote.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}. Travel time excludes live traffic.</p>
            <button type="button" disabled={busy} onClick={book}>{busy ? 'Saving…' : 'Request this ride'}</button>
          </div>}
          {restoring && <p role="status">Checking your latest open ride…</p>}
          {ride && <div className="fare-summary"><p className="eyebrow">RIDE REQUEST SAVED</p><h3>Status: {ride.status.replaceAll('_', ' ')}</h3><p>Estimated fare: {formatMoney(ride.fare_estimate)}</p><p className="ride-reference">Reference: {ride.id}</p>
            {ride.driver_id && <p className="ride-reference">Assigned driver: {ride.driver_id}</p>}
            {ride.driver_id && ['accepted', 'arriving', 'in_progress'].includes(ride.status) && <div className="driver-location-card">
              <strong>Driver’s last shared location</strong>
              {driverLocation?.ride_id === ride.id && driverLocation.location && new Date(driverLocation.expires_at).getTime() > now
                ? <p>{driverLocation.location.latitude}, {driverLocation.location.longitude} · Updated {new Date(driverLocation.updated_at).toLocaleTimeString()}</p>
                : <p>Waiting for a fresh location. The driver may be offline.</p>}
            </div>}
            <TripETA eta={eta} />
            {ride.status === 'completed' && <RidePayment key={ride.id} rideId={ride.id} liveRevision={liveRevision} onSessionExpired={onSessionExpired} />}
            <div className="auth-actions"><button type="button" disabled={busy} onClick={refreshStatus}>Refresh ride status</button>{ride.status === 'requested' && <button className="secondary-button" type="button" disabled={busy} onClick={findDrivers}>Find nearby drivers</button>}</div>
            {ride.status === 'requested' && matchingChecked && <div className="rider-matching">
              <h4>Nearby available drivers</h4>
              <p className="fare-note">Drivers must accept your request. These are geographic pickup distances, not driving ETAs. Refresh ride status to check for acceptance.</p>
              {nearbyDrivers.length === 0 ? <p>No nearby available drivers right now. Try again after a driver goes online.</p> : <ul className="matching-list">
                {nearbyDrivers.map((driver) => <li key={driver.driver_id}><div className="matching-title"><strong>{driver.name}</strong><span>{(driver.distance_meters / 1000).toFixed(2)} km away</span></div><p>{driver.vehicle_info.make} {driver.vehicle_info.model} · {driver.vehicle_info.plate}</p><p className="fare-note">{driver.verified ? 'Vehicle marked verified' : 'Unverified learning-demo vehicle'}</p></li>)}
              </ul>}
            </div>}
          </div>}
          </aside>
        </div>
      )}
      <p className={`auth-message${isError ? ' auth-error' : ''}`} role="status" aria-live="polite" aria-atomic="true">{message}</p>
    </section>
  )
}

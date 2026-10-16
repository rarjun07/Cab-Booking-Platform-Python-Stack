import { useState } from 'react'
import AuthPanel from './AuthPanel.jsx'
import RideBooking from './RideBooking.jsx'
import DriverDashboard from './DriverDashboard.jsx'
import useRealtime from './useRealtime.js'

const connectionMessages = {
  idle: 'Ready when you are. Start FastAPI, then check the connection.',
  checking: 'Checking the backend connection…',
  connected: 'Connected! FastAPI returned a healthy response.',
  unavailable: 'Could not reach a healthy backend. Start FastAPI on port 8000 and try again.',
}

export default function App() {
  const [connection, setConnection] = useState('idle')
  const [user, setUser] = useState(null)
  const live = useRealtime(user, setUser)

  async function checkConnection() {
    setConnection('checking')

    try {
      const response = await fetch('/api/health', {
        signal: AbortSignal.timeout(5000),
      })

      if (!response.ok) {
        throw new Error('The health request failed.')
      }

      const data = await response.json()
      if (data.status !== 'ok') {
        throw new Error('The API did not report a healthy status.')
      }

      setConnection('connected')
    } catch {
      setConnection('unavailable')
    }
  }

  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <a className="brand" href="/" aria-label="Cab Booking Platform home">
          <span className="brand-mark" aria-hidden="true">C</span>
          Cab Booking Platform
        </a>
        <span className="day-label">Day 05 <span aria-hidden="true">/</span> Your ride, live</span>
      </header>

      <main id="main">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">YOUR NEXT JOURNEY</p>
          <h1 id="page-title">Where would you<br />like to go?</h1>
          <p className="intro-copy">
            Sign in, choose your pickup and destination, and get an estimate
            before you request your ride.
          </p>
        </section>

        <AuthPanel user={user} onUserChange={setUser} />
        {user && <p className={`live-connection${live.status === 'connected' ? ' live-connected' : ''}`} role="status" aria-live="polite">{live.status === 'connected' ? 'Live updates connected' : live.status === 'connecting' ? 'Connecting live updates…' : 'Live updates reconnecting. Refresh is still available.'}</p>}
        {user?.role === 'driver'
          ? <DriverDashboard key={user.id} onSessionExpired={setUser} live={live} />
          : <RideBooking key={user?.id ?? 'signed-out'} user={user} onSessionExpired={setUser} liveRevision={live.revision} />}

        <section className="connection-card" aria-labelledby="connection-title">
          <div>
            <p className="eyebrow">THE FIRST CONNECTION</p>
            <h2 id="connection-title">Let’s see if we’re connected.</h2>
            <p className="card-copy">This button asks our API if it’s running.</p>
          </div>

          <div className={`status-panel status-${connection}`} role="status" aria-live="polite" aria-atomic="true">
            <span className="status-dot" aria-hidden="true" />
            <p>{connectionMessages[connection]}</p>
          </div>

          <button type="button" onClick={checkConnection} disabled={connection === 'checking'}>
            {connection === 'checking' ? 'Checking…' : connection === 'idle' ? 'Check backend connection' : 'Check again'}
            <span aria-hidden="true">↗</span>
          </button>
          <p className="endpoint-note">GET /api/health</p>
        </section>

        <section className="journey" aria-labelledby="journey-title">
          <h2 id="journey-title">Your booking route</h2>
          <ol>
            <li><span className="step-number">01</span><div><h3>Your account</h3><p>Sign in as a rider.</p></div></li>
            <li><span className="step-number">02</span><div><h3>Your estimate</h3><p>Road distance, travel time, and fare.</p></div></li>
            <li><span className="step-number">03</span><div><h3>Your driver</h3><p>A nearby driver accepts your saved request.</p></div></li>
          </ol>
        </section>
      </main>
      <footer>Built with Python, FastAPI & React. <span>One day at a time.</span></footer>
    </>
  )
}

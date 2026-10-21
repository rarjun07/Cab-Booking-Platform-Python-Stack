import { useState } from 'react'
import AuthPanel from './AuthPanel.jsx'
import RideBooking from './RideBooking.jsx'
import DriverDashboard from './DriverDashboard.jsx'
import useRealtime from './useRealtime.js'
import RideHistory from './RideHistory.jsx'
import Wallet from './Wallet.jsx'

const connectionMessages = {
  idle: 'Ready when you are. Start FastAPI, then check the connection.',
  checking: 'Checking the backend connection…',
  connected: 'Connected! FastAPI returned a healthy response.',
  unavailable: 'Could not reach a healthy backend. Start FastAPI on port 8000 and try again.',
}

export default function App() {
  const [connection, setConnection] = useState('idle')
  const [user, setUser] = useState(null)
  const [authMode, setAuthMode] = useState('register')
  const [accountFocusRequest, setAccountFocusRequest] = useState(0)
  const live = useRealtime(user, setUser)

  function openAccount(mode = authMode) {
    setAuthMode(mode)
    setAccountFocusRequest((request) => request + 1)
  }

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
        <div className="header-actions">
          <span className="demo-label">Learning project · Test payments</span>
          <nav className="account-nav" aria-label="Account navigation">
            {!user && <>
              <button type="button" aria-controls="account" onClick={() => openAccount('login')}>Login</button>
              <button className="nav-register" type="button" aria-controls="account" onClick={() => openAccount('register')}>Register</button>
            </>}
            <button className="nav-account" type="button" aria-label={user ? 'My account' : 'Account'} title={user ? `Account: ${user.name}` : 'Your account'} aria-controls="account" onClick={() => openAccount()}>
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
                <circle cx="12" cy="8" r="3.5" />
                <path d="M5 21v-2a7 7 0 0 1 14 0v2" />
              </svg>
            </button>
          </nav>
        </div>
      </header>

      <main id="main" tabIndex={-1}>
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">{user?.role === 'driver' ? 'YOUR DRIVER WORKSPACE' : 'YOUR NEXT JOURNEY'}</p>
          <h1 id="page-title">{user?.role === 'driver' ? 'Ready for your next pickup?' : 'Where would you like to go?'}</h1>
          <p className="intro-copy">
            {user?.role === 'driver' ? 'Save your vehicle, share your location, and manage your next trip.' : 'Choose your pickup and destination, check the fare, and request your ride.'}
          </p>
        </section>

        <nav className="section-nav" aria-label="Workspace sections">
          <a href="#account">Account</a>
          <a href={user?.role === 'driver' ? '#driver' : '#booking'}>{user?.role === 'driver' ? 'Driver dashboard' : 'Book a ride'}</a>
          {user?.role === 'rider' && <a href="#wallet">Wallet</a>}
          {user && <a href="#history">Ride history</a>}
        </nav>
        <AuthPanel user={user} onUserChange={setUser} mode={authMode} onModeChange={setAuthMode} focusRequest={accountFocusRequest} />
        {user && <p className={`live-connection${live.status === 'connected' ? ' live-connected' : ''}`} role="status" aria-live="polite">{live.status === 'connected' ? 'Live updates connected' : live.status === 'connecting' ? 'Connecting live updates…' : 'Live updates reconnecting. Refresh is still available.'}</p>}
        <div className={`workspace${user?.role === 'rider' ? ' rider-workspace' : ''}`}>
        {user?.role === 'driver'
          ? <DriverDashboard key={user.id} onSessionExpired={setUser} live={live} />
          : <RideBooking key={user?.id ?? 'signed-out'} user={user} onSessionExpired={setUser} liveRevision={live.revision} />}
        {user?.role === 'rider' && <Wallet key={user.id} liveRevision={live.revision} onSessionExpired={setUser} />}
        </div>
        {user && <RideHistory key={user.id} user={user} liveRevision={live.revision} onSessionExpired={setUser} />}

        <details className="connection-details">
        <summary>Check the app connection</summary>
        <section className="connection-card" aria-labelledby="connection-title">
          <div>
            <h2 id="connection-title">Connection check</h2>
            <p className="card-copy">Having trouble loading your trips? Check whether the app can reach its server.</p>
          </div>

          <div className={`status-panel status-${connection}`} role="status" aria-live="polite" aria-atomic="true">
            <span className="status-dot" aria-hidden="true" />
            <p>{connectionMessages[connection]}</p>
          </div>

          <button type="button" onClick={checkConnection} disabled={connection === 'checking'}>
            {connection === 'checking' ? 'Checking…' : connection === 'idle' ? 'Check backend connection' : 'Check again'}
            <span aria-hidden="true">↗</span>
          </button>
        </section>
        </details>

        <section className="journey" aria-labelledby="journey-title">
          <h2 id="journey-title">{user?.role === 'driver' ? 'Your driver checklist' : 'Your booking route'}</h2>
          <ol>
            <li><span className="step-number" aria-hidden="true">01</span><div><h3>{user?.role === 'driver' ? 'Your vehicle' : 'Your account'}</h3><p>{user?.role === 'driver' ? 'Save your vehicle details before going online.' : 'Create an account or sign in as a rider.'}</p></div></li>
            <li><span className="step-number" aria-hidden="true">02</span><div><h3>{user?.role === 'driver' ? 'Your availability' : 'Your estimate'}</h3><p>{user?.role === 'driver' ? 'Go online with a fresh location to find requests.' : 'Check road distance, travel time, and fare.'}</p></div></li>
            <li><span className="step-number" aria-hidden="true">03</span><div><h3>{user?.role === 'driver' ? 'Your trip' : 'Your driver'}</h3><p>{user?.role === 'driver' ? 'Accept a request and update each trip step.' : 'A nearby driver accepts your saved request.'}</p></div></li>
          </ol>
        </section>
      </main>
      <footer><span>Cab Booking Platform</span><span>Learning project · Test payments only</span></footer>
    </>
  )
}

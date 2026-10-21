import { useEffect, useState } from 'react'
import AuthPanel from './AuthPanel.jsx'
import RideBooking from './RideBooking.jsx'
import DriverDashboard from './DriverDashboard.jsx'
import useRealtime from './useRealtime.js'
import RideHistory from './RideHistory.jsx'
import Wallet from './Wallet.jsx'
import WorkspaceNavigation from './WorkspaceNavigation.jsx'

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
  const [section, setSection] = useState(() => window.location.hash.slice(1))
  const [viewFocus, setViewFocus] = useState(null)
  const live = useRealtime(user, setUser)
  const primarySection = user?.role === 'driver' ? 'driver' : 'booking'
  const sections = [primarySection, 'account', 'history', ...(user?.role === 'rider' ? ['wallet'] : [])]
  const activeSection = sections.includes(section) ? section : primarySection
  const titles = { booking: 'Book your next ride', driver: 'Driver dashboard', wallet: 'Your wallet', history: 'Your ride history', account: 'Your account' }
  const descriptions = {
    booking: 'Set your route, check the fare, and follow your journey.',
    driver: 'Manage your vehicle, availability and nearby ride requests.',
    wallet: 'View your balance and keep track of test top-ups.',
    history: 'Find your previous trips, documents and reviews.',
    account: 'Manage your session and account details.',
  }

  useEffect(() => {
    function restoreSection() {
      setSection(window.location.hash.slice(1))
      setViewFocus({ id: 'page-title' })
    }
    window.addEventListener('hashchange', restoreSection)
    window.addEventListener('popstate', restoreSection)
    return () => {
      window.removeEventListener('hashchange', restoreSection)
      window.removeEventListener('popstate', restoreSection)
    }
  }, [])

  useEffect(() => {
    if (!viewFocus) return
    const target = document.getElementById(viewFocus.id)
    target?.focus()
    target?.scrollIntoView?.({ block: 'start' })
  }, [viewFocus])

  function navigateTo(id) {
    setSection(id)
    if (window.location.hash !== `#${id}`) window.history.pushState(null, '', `#${id}`)
    if (id === 'account') setAccountFocusRequest((request) => request + 1)
    else setViewFocus({ id })
  }

  function openAccount(mode = authMode) {
    setAuthMode(mode)
    navigateTo('account')
  }

  function openAuthenticatedWorkspace(account) {
    const id = account.role === 'driver' ? 'driver' : 'booking'
    setSection(id)
    window.history.replaceState(null, '', `#${id}`)
    setViewFocus({ id: 'page-title' })
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
      <header className={`site-header${user ? ' signed-in-header' : ''}`}>
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

      <main id="main" tabIndex={-1} className={user ? 'dashboard-shell' : 'landing-shell'}>
        <aside className="dashboard-sidebar" hidden={!user} aria-label="Your workspace">
          {user && <WorkspaceNavigation user={user} activeSection={activeSection} onNavigate={navigateTo} />}
        </aside>
        <div className="page-content">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">{user ? `${user.role.toUpperCase()} WORKSPACE` : 'YOUR NEXT JOURNEY'}</p>
          <h1 id="page-title" tabIndex={-1}>{user ? titles[activeSection] : 'Where would you like to go?'}</h1>
          <p className="intro-copy">
            {user ? descriptions[activeSection] : 'Choose your pickup and destination, check the fare, and request your ride.'}
          </p>
          {!user && <section className="journey" aria-labelledby="journey-title">
            <h2 id="journey-title">A simpler way to get going</h2>
            <ol>
              <li><span className="step-number" aria-hidden="true">01</span><div><h3>Create your account</h3><p>Join as a rider or a driver.</p></div></li>
              <li><span className="step-number" aria-hidden="true">02</span><div><h3>Plan your journey</h3><p>Check your route and fare before requesting.</p></div></li>
              <li><span className="step-number" aria-hidden="true">03</span><div><h3>Keep everything together</h3><p>Follow your trip and find your documents.</p></div></li>
            </ol>
          </section>}
          {user && <p className={`live-connection${live.status === 'connected' ? ' live-connected' : ''}`} role="status" aria-live="polite">{live.status === 'connected' ? 'Live updates connected' : live.status === 'connecting' ? 'Connecting live updates…' : 'Live updates reconnecting. Refresh is still available.'}</p>}
        </section>

        <div className="account-pane" hidden={Boolean(user) && activeSection !== 'account'}>
        <AuthPanel user={user} onUserChange={setUser} onAuthenticated={openAuthenticatedWorkspace} mode={authMode} onModeChange={setAuthMode} focusRequest={accountFocusRequest} />
        </div>
        <div className="workspace" hidden={!user || activeSection !== primarySection}>
        {user?.role === 'driver'
          ? <DriverDashboard key={user.id} onSessionExpired={setUser} live={live} />
          : <RideBooking key={user?.id ?? 'signed-out'} user={user} onSessionExpired={setUser} liveRevision={live.revision} />}
        </div>
        <div className="wallet-pane" hidden={!user || activeSection !== 'wallet'}>
        {user?.role === 'rider' && <Wallet key={user.id} liveRevision={live.revision} onSessionExpired={setUser} />}
        </div>
        <div className="history-pane" hidden={!user || activeSection !== 'history'}>
        {user && <RideHistory key={user.id} user={user} liveRevision={live.revision} onSessionExpired={setUser} />}
        </div>

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

        </div>
      </main>
      <footer><span>Cab Booking Platform</span><span>Learning project · Test payments only</span></footer>
    </>
  )
}

import { useState } from 'react'
import AuthPanel from './AuthPanel.jsx'

const connectionMessages = {
  idle: 'Ready when you are. Start FastAPI, then check the connection.',
  checking: 'Checking the backend connection…',
  connected: 'Connected! FastAPI returned a healthy response.',
  unavailable: 'Could not reach a healthy backend. Start FastAPI on port 8000 and try again.',
}

export default function App() {
  const [connection, setConnection] = useState('idle')

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
        <span className="day-label">Day 01 <span aria-hidden="true">/</span> Getting started</span>
      </header>

      <main id="main">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">ONE CONNECTION AT A TIME</p>
          <h1 id="page-title">Every journey starts<br />with a first step.</h1>
          <p className="intro-copy">
            Welcome to our cab booking project. Our first stop: connecting
            this React app to the FastAPI backend.
          </p>
        </section>

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

        <AuthPanel />

        <section className="journey" aria-labelledby="journey-title">
          <h2 id="journey-title">Our Day 1 route</h2>
          <ol>
            <li><span className="step-number">01</span><div><h3>Project setup</h3><p>Local Git and app foundations.</p></div><span className="step-tag">Ready</span></li>
            <li><span className="step-number">02</span><div><h3>Connect the apps</h3><p>React meets our FastAPI endpoint.</p></div><span className="step-tag">Try it above</span></li>
            <li><span className="step-number">03</span><div><h3>Your account</h3><p>Sign in and verify your session above.</p></div><span className="step-tag">Try it above</span></li>
          </ol>
        </section>
      </main>
      <footer>Built with Python, FastAPI & React. <span>One day at a time.</span></footer>
    </>
  )
}

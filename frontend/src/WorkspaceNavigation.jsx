const paths = {
  booking: <><path d="M4 10l2-6h12l2 6M3 10h18v8H3zM6 18v2m12-2v2M6 14h1m10 0h1" /></>,
  driver: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3" /><path d="M3 11h6m6 0h6m-9 4v6" /></>,
  wallet: <><path d="M20 8V5H5a2 2 0 0 0 0 4h16v11H5a2 2 0 0 1-2-2V7" /><path d="M21 12h-5v5h5m-2-2.5h.01" /></>,
  history: <><path d="M3 11a9 9 0 1 1 3 8M3 4v7h7m2-5v6l4 2" /></>,
  account: <><circle cx="12" cy="8" r="3.5" /><path d="M5 21v-2a7 7 0 0 1 14 0v2" /></>,
}

export default function WorkspaceNavigation({ user, activeSection, onNavigate }) {
  const primary = user.role === 'driver' ? ['driver', 'Driver dashboard'] : ['booking', 'Book a ride']
  const links = [primary, ...(user.role === 'rider' ? [['wallet', 'Wallet']] : []), ['history', 'Ride history'], ['account', 'Account']]
  return <nav className="section-nav workspace-top-nav" aria-label="Workspace sections">
      {links.map(([id, label]) => <a key={id} href={`#${id}`} aria-current={activeSection === id ? 'page' : undefined} onClick={(event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        event.preventDefault()
        onNavigate(id)
      }}>
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{paths[id]}</svg>
        {label}
      </a>)}
    </nav>
}

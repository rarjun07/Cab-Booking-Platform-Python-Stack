import { useState } from 'react'

export default function Avatar({ user }) {
  const [failed, setFailed] = useState(null)
  const source = user.profile_pic?.startsWith('https://') ? user.profile_pic : null
  const initials = user.name.trim().split(/\s+/).slice(0, 2).map((name) => [...name][0]).join('')
  return <span className="workspace-avatar" aria-hidden="true">
    {source && failed !== source ? <img src={source} alt="" referrerPolicy="no-referrer" onError={() => setFailed(source)} /> : initials}
  </span>
}

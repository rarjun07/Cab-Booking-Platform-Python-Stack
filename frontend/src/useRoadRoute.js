import { useEffect, useState } from 'react'

export default function useRoadRoute(ride, onSessionExpired) {
  const [saved, setSaved] = useState(null)
  const id = ride?.id
  useEffect(() => {
    if (!id) return
    const controller = new AbortController()
    fetch(`/api/rides/${id}/route`, { credentials: 'same-origin',
      signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) }).then(async (response) => {
      const data = await response.json()
      if (!response.ok) {
        if (response.status === 401) onSessionExpired(null)
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Route unavailable.')
      }
      if (!controller.signal.aborted) setSaved({ id, ...data })
    }).catch((error) => {
      if (!controller.signal.aborted) setSaved({ id, error: error.message || 'Route unavailable.' })
    })
    return () => controller.abort()
  }, [id, onSessionExpired])
  return saved?.id === id ? saved : null
}

import { useEffect, useState } from 'react'

export default function useTripETA(ride, onSessionExpired) {
  const [saved, setSaved] = useState(null)
  const [now, setNow] = useState(Date.now())
  const id = ride?.id, status = ride?.status
  const active = Boolean(ride?.driver_id && ['accepted', 'arriving', 'in_progress'].includes(status))
  useEffect(() => {
    if (!active) return
    const controller = new AbortController()
    let stopped = false
    let timer
    async function refresh() {
      try {
        if (document.visibilityState !== 'hidden') {
          const response = await fetch(`/api/rides/${id}/eta`, { credentials: 'same-origin',
            signal: AbortSignal.any([controller.signal, AbortSignal.timeout(12000)]) })
          const data = await response.json()
          if (!response.ok) {
            if (response.status === 401) { stopped = true; onSessionExpired(null); return }
            throw new Error('ETA temporarily unavailable. Retrying automatically.')
          }
          if (!controller.signal.aborted) { setSaved({ ...data, id, status }); setNow(Date.now()) }
        }
      } catch (error) {
        if (!controller.signal.aborted) setSaved({ id, status, error: error.message })
      } finally {
        // Never overlap requests or calculate a route on every GPS point.
        if (!controller.signal.aborted && !stopped) timer = setTimeout(refresh, 15000)
      }
    }
    // Avoid competing with the initial saved-route request for OSRM's throttle.
    timer = setTimeout(refresh, 1200)
    return () => { controller.abort(); clearTimeout(timer) }
  }, [id, status, active, onSessionExpired])

  useEffect(() => {
    if (!saved?.expires_at) return
    const timer = setTimeout(() => setNow(Date.now()), Math.max(0, new Date(saved.expires_at).getTime() - Date.now()) + 10)
    return () => clearTimeout(timer)
  }, [saved])
  if (!active) return null
  if (!saved || saved.id !== id || saved.status !== status) return { loading: true }
  if (saved.available && new Date(saved.expires_at).getTime() <= now) return { available: false, reason: 'location_unavailable' }
  return saved
}

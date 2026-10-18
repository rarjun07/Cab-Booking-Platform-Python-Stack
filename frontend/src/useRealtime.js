import { useCallback, useEffect, useRef, useState } from 'react'

export default function useRealtime(user, onSessionExpired) {
  const [status, setStatus] = useState('off')
  const [revision, setRevision] = useState(0)
  const socketRef = useRef(null)
  const readyRef = useRef(false)
  const pending = useRef(new Map())

  useEffect(() => {
    if (!user) { setStatus('off'); return }
    let active = true
    let reconnectTimer
    let handshakeTimer
    let changeTimer
    let attempts = 0

    function rejectPending() {
      for (const item of pending.current.values()) {
        clearTimeout(item.timer)
        item.reject(new Error('The live connection closed. Refresh before retrying.'))
      }
      pending.current.clear()
    }

    function changed() {
      if (changeTimer) return
      changeTimer = setTimeout(() => {
        changeTimer = null
        if (active) setRevision((value) => value + 1)
      }, 100)
    }

    function connect() {
      if (!active) return
      setStatus(attempts ? 'reconnecting' : 'connecting')
      readyRef.current = false
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const socket = new WebSocket(`${protocol}://${window.location.host}/api/ws/${encodeURIComponent(user.role)}/${encodeURIComponent(user.id)}`)
      socketRef.current = socket
      handshakeTimer = setTimeout(() => { if (!readyRef.current) socket.close() }, 12000)
      socket.onmessage = (message) => {
        if (!active) return
        let event
        try { event = JSON.parse(message.data) } catch { return }
        if (event.type === 'ready') {
          clearTimeout(handshakeTimer)
          readyRef.current = true
          attempts = 0
          setStatus('connected')
          changed()
        } else if (['sync', 'matching.changed', 'driver.changed', 'ride.changed', 'ride.location', 'payment.changed', 'review.changed'].includes(event.type)) {
          changed()
        } else if (event.request_id && pending.current.has(event.request_id)) {
          const item = pending.current.get(event.request_id)
          clearTimeout(item.timer)
          pending.current.delete(event.request_id)
          if (event.type === 'location.saved') item.resolve(event)
          else {
            const error = new Error(event.message ?? 'Could not share this location.')
            error.status = event.status
            item.reject(error)
          }
        }
      }
      socket.onclose = (event) => {
        clearTimeout(handshakeTimer)
        if (!active || socketRef.current !== socket) return
        readyRef.current = false
        rejectPending()
        if (event.code === 4401) { onSessionExpired(null); return }
        setStatus('reconnecting')
        reconnectTimer = setTimeout(connect, Math.min(15000, 1000 * 2 ** Math.min(attempts++, 4)))
      }
      socket.onerror = () => { if (active && socketRef.current === socket) setStatus('reconnecting') }
    }
    connect()
    return () => {
      active = false
      clearTimeout(reconnectTimer)
      clearTimeout(handshakeTimer)
      clearTimeout(changeTimer)
      readyRef.current = false
      socketRef.current?.close()
      socketRef.current = null
      rejectPending()
    }
  }, [user?.id, user?.role, onSessionExpired])

  const sendLocation = useCallback((location) => new Promise((resolve, reject) => {
    const socket = socketRef.current
    if (!readyRef.current || socket?.readyState !== WebSocket.OPEN) {
      reject(new Error('Live updates are disconnected. Refresh before retrying.'))
      return
    }
    const requestId = crypto.randomUUID()
    const timer = setTimeout(() => {
      pending.current.delete(requestId)
      reject(new Error('Location confirmation timed out. Refresh before retrying.'))
    }, 8000)
    pending.current.set(requestId, { resolve, reject, timer })
    try { socket.send(JSON.stringify({ type: 'location.update', request_id: requestId, location })) }
    catch (error) { clearTimeout(timer); pending.current.delete(requestId); reject(error) }
  }), [])

  return { status, revision, sendLocation }
}

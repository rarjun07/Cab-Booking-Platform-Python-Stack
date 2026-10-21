// Shared cookie-based authentication requests for account forms and the header.
export async function authRequest(path, body, signal) {
  const response = await fetch(`/api/auth/${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: signal ?? AbortSignal.timeout(10000),
  })
  if (response.status === 204) return null
  const data = await response.json()
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Check your inputs and try again.')
    error.status = response.status
    throw error
  }
  return data
}

import { afterEach, expect, test, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProfileEditor from '../src/ProfileEditor.jsx'
import Avatar from '../src/Avatar.jsx'

const user = { id: 'rider', name: 'Test Rider', role: 'rider', email: 'rider@example.com' }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

test('profile save sends only editable fields and updates the shared account', async () => {
  const saved = { ...user, name: 'Updated Rider', phone: '+919876543210', profile_pic: null }
  const fetcher = vi.fn(async () => new Response(JSON.stringify(saved), { status: 200 }))
  vi.stubGlobal('fetch', fetcher)
  const onUserChange = vi.fn(), keyboard = userEvent.setup()
  render(<ProfileEditor user={user} onUserChange={onUserChange} />)
  await keyboard.clear(screen.getByLabelText('Display name'))
  await keyboard.type(screen.getByLabelText('Display name'), 'Updated Rider')
  await keyboard.type(screen.getByLabelText('Phone number (optional)'), '+919876543210')
  await keyboard.click(screen.getByRole('button', { name: 'Save profile' }))
  await screen.findByText('Profile saved.')
  expect(fetcher.mock.calls[0][0]).toBe('/api/auth/profile')
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ name: 'Updated Rider', phone: '+919876543210', profile_pic: null })
  expect(onUserChange).toHaveBeenCalledWith(saved)
})

test('failed save preserves the form draft', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'That phone number is already in use.' }), { status: 409 })))
  const onUserChange = vi.fn(), keyboard = userEvent.setup()
  render(<ProfileEditor user={user} onUserChange={onUserChange} />)
  await keyboard.type(screen.getByLabelText('Phone number (optional)'), '+919876543210')
  await keyboard.click(screen.getByRole('button', { name: 'Save profile' }))
  await screen.findByRole('alert')
  expect(screen.getByLabelText('Phone number (optional)').value).toBe('+919876543210')
  expect(onUserChange).not.toHaveBeenCalled()
})

test('broken profile images fall back to initials', () => {
  const { container } = render(<Avatar user={{ ...user, profile_pic: 'https://images.example.com/p.png' }} />)
  const image = container.querySelector('img')
  expect(image.getAttribute('referrerpolicy')).toBe('no-referrer')
  fireEvent.error(image)
  expect(container.querySelector('img')).toBeNull()
  expect(container.textContent).toBe('TR')
})

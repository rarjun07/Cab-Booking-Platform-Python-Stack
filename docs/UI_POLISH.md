# Day 11: React usability, accessibility and responsive layout

Day 11 improved the existing account, booking, driver, wallet and history screens. On 2026-10-21 the user also requested header controls and better aligned rider/driver dashboards using the same colors. The current layout below includes those follow-ups. The backend, API contracts, database schema, pricing and payment verification are unchanged. The user-deferred real Stripe checks remain pending.

The code/build and simulated-DOM checks described below passed. Actual desktop/mobile rendering, zoom, focus visibility and screen-reader behavior still require the manual checklist. Earlier browser automation was blocked; no new automated browser session or workaround was used. This is not a claim of WCAG conformance or a completed visual review.

## Step 1: open your local app

Use the existing [two-terminal startup instructions](../frontend/README.md). On this Mac the backend terminal needs the PDF library path:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/backend"
source .venv/bin/activate
export DYLD_FALLBACK_LIBRARY_PATH="/opt/homebrew/lib${DYLD_FALLBACK_LIBRARY_PATH:+:$DYLD_FALLBACK_LIBRARY_PATH}"
python -m uvicorn app.main:app --reload --no-proxy-headers --ws-max-size 2048
```

In a separate terminal:

```bash
cd "/Users/arjunsair/Desktop/Python_Developer/Cab Booking Platform/frontend"
npm run dev
```

Reuse servers already running on ports 8000 and 5173. Open <http://127.0.0.1:5173/>. PostgreSQL and Redis remain the existing local services; no new database setup is needed.

## Step 2: understand the layout

The signed-in sidebar has **Book a ride** or **Driver dashboard**, **Wallet** for riders, **Ride history**, and **Account**. These remain real fragment links, with ordinary clicks selecting a focused view and updating browser history. `aria-current="page"` marks the selected link. Bookmarks, Back/Forward and modified-click/new-tab behavior are supported. An unavailable role-specific fragment falls back to that account's primary workspace. The first keyboard link skips the header and moves to main content.

Account settings, wallet and history have separate views so they do not push the main workspace down the page. Hidden views stay mounted to preserve form drafts, selected payment/review controls and live state; `[hidden]` is explicitly styled to keep inactive views out of layout and keyboard navigation. The account panel stays mounted during session restoration. The header retains the learning/test-payment label and Login/Register/profile controls. The connection checker remains inside its native disclosure below the active content.

`App.jsx` and `WorkspaceNavigation.jsx` provide the shared shell, user identity and navigation. On desktop, the sidebar aligns with a compact page heading/content column in the same 1,240-pixel maximum container as the header/footer. At 1,100 CSS pixels and above, `RideBooking.jsx` places grouped pickup/destination fields beside the real estimate/current ride, and `DriverDashboard.jsx` places vehicle/availability cards beside incoming/current requests. Empty states explain the next action without invented maps, earnings or activity metrics. Existing cream, dark-green and lime colors are retained.

At 900 CSS pixels and below, the sidebar becomes a top navigation card and the guest introduction/form stack. At 540 CSS pixels and below, navigation uses a compact grid and form/action rows stack. The guest page otherwise uses an introduction/account-form split. Wrapping text and zero minimum grid widths keep long names/references from forcing grid expansion; no overflow clipping is used to conceal layout problems. Rendered reflow still needs the manual check below.

Buttons and disclosure controls have a minimum 44-pixel height; rating labels are enlarged around native radio inputs. Text inputs are at least 16 pixels and have explicit colors, borders and labels. Nested payment/review panels use smaller fluid padding to preserve space on phones. Actual rendered sizes and reflow remain a manual check.

## Step 3: understand keyboard and form changes

- `tabIndex={-1}` makes a section/heading focusable by navigation or code without adding an extra Tab stop. There are no positive tab indices or custom keyboard handlers replacing native controls.
- Successful sign-in/registration in the full app opens the rider/driver workspace and focuses its visible page heading. The standalone `AuthPanel` retains its heading-focus behavior; sign-out focuses the now-visible account heading. Failed account actions focus error feedback and preserve the email. Passive session restoration does not move focus.
- Sidebar navigation focuses the selected section; browser navigation focuses the visible page heading. The header's Login/Register controls select the matching form and focus its first field, and the profile button opens account details.
- A visible `:focus-visible` outline remains around keyboard targets. Forced-colors mode uses the system highlight color. Native form validation and the existing server checks remain in place.
- Each `RidePayment` instance uses React `useId()`. A trip can appear in both current booking and history without duplicate payment-heading/promo-input IDs or a label pointing to the wrong input.
- History trips have headings, per-trip action groups and named pagination. Review/payment disclosure buttons expose their expanded state and reference a mounted panel while open. Page changes clear the expanded trip selections.
- Wallet amounts and review comments have associated hints. The balance is announced as a short atomic value rather than announcing the whole wallet on each update. Native rating radios still support arrow-key selection. Background review reads preserve a draft.

## Step 4: run the focused checks

From `frontend/`:

```bash
npm test
npm run build
```

On another machine, run `npm ci` first. Production dependency pins and Vite versions are unchanged. The exact new development-only versions are recorded in the manifest and lockfile: Vitest 5.0.5, jsdom 30.1.3, Testing Library React 16.3.3, user-event 14.6.8 and axe-core 4.14.0. They are not imported by the production app. The local install reported no vulnerabilities; an existing npm-cache permission error was resolved using a separate temporary cache, without changing ownership or permissions of the user's cache.

`vitest.config.js` transforms React JSX and selects jsdom; it does not start a browser. `tests/accessibility.test.jsx` supplies controlled HTTP responses and a controlled realtime hook. It never connects to the backend, database, routing, WebSocket or Stripe services. Tests cover behavior rather than CSS snapshots:

| Check | Observed result |
| --- | --- |
| Guest/rider/driver workspace: named controls, unique IDs, valid label/ARIA targets and axe structural WCAG checks | Three parameterized cases passed. |
| Initial keyboard entry and account-mode activation | Skip link is the first Tab target; Enter activates sign-in mode. |
| Account success/logout and failure | Persistent heading/error receives focus, email retained on failure. |
| Same trip's current/history payment panels | Distinct IDs and correct labels/expanded state. |
| Promo with checkout disabled | Keyboard submission saves the controlled discount without opening Stripe. |
| Review radio selection and background update | Arrow keys select five stars; draft remains; numeric rating is submitted. |

The original Day 11 checkpoint passed **9 tests**. After the 2026-10-21 layout follow-up, the complete frontend suite passes **21 tests**, including account-header actions, role-specific sign-in, active-view visibility/focus, route/vehicle draft retention, bookmarks/browser navigation and structural accessibility checks for each role's allowed views. The final production build passed with 31 modules (294.87 kB JavaScript / 89.33 kB gzip). A source-level palette check confirmed that the dashboard CSS introduces no colors outside the existing palette. Backend code is unchanged; Day 13's 268 backend tests remain the latest recorded backend result, not a rerun for this UI change.

The axe audit runs WCAG 2 A/AA, 2.1 AA and 2.2 AA tagged rules with color contrast disabled because jsdom does not paint or lay out a page. Detected violations were zero for these fixtures. This does not test every screen state or establish visual/keyboard/screen-reader conformance in a real browser.

A separate calculation checked the opaque text/background palette: primary text `#172a28` on `#fffef9` is 14.87:1; muted text `#596660` on `#f6f5ef` is 5.50:1 and on `#edf1df` is 5.22:1; error text `#a02b1d` on `#fffef9` is 7.28:1. The old decorative step-number shade calculated at 4.34:1 and was replaced with the stronger muted shade. These calculations do not measure the rendered page, disabled controls, provider iframes or all adjacent UI boundaries.

## Step 5: manual review still needed

Try the following and record the actual browser/device and result in [PROGRESS.md](PROGRESS.md). Report overlapping controls, missing focus, hidden text or an action that cannot be reached; do not tick a check merely because the build succeeds.

- [ ] Desktop: inspect guest, rider and driver screens at approximately 1,280 pixels. Check the header/sidebar/content alignment, guest form split, rider route/summary columns and driver settings/request columns. Open wallet/history/account and payment/review details.
- [ ] Narrow layout: inspect 320, 375 and 768 CSS-pixel widths. Ensure the page has no horizontal scrolling, long references/email/name text wrap, all buttons remain readable and nested panels stay usable.
- [ ] Zoom: enlarge to 200%, then check reflow equivalent to 320 CSS pixels (for example 1,280 pixels at 400%). No content or action should disappear.
- [ ] Keyboard: reload, press Tab to reveal **Skip to content**, activate it and verify main receives focus. Use section links, Shift+Tab, Enter and Space; check visible focus and no trap. Verify the native connection disclosure opens/closes.
- [ ] Account: use sign-in/registration, a wrong password and sign-out. Confirm the focus destination remains useful and error/success feedback is understandable.
- [ ] Rider: use the Delhi sample, estimate, request a ride, open history, apply an eligible promo before checkout, and inspect wallet hints/empty balance. Missing Stripe keys should leave top-ups disabled. Carry earlier rider/driver flow checks forward where not actually tried.
- [ ] Driver: save a vehicle, go online with the sample location, reach each trip action and inspect disabled/loading states. This manual sample is not GPS tracking.
- [ ] Reviews/history: select a radio with arrow keys, type a comment, check its draft during live refresh, submit, open/close details, and page history. Ensure each action clearly belongs to its trip.
- [ ] VoiceOver or another screen reader: check landmarks/headings, field labels/hints, error focus, disclosure state, rating group, live status and wallet value. Check increased contrast/forced-colors where supported.

Actual Stripe Elements rendering, confirmation/failure/retry and a real test webhook remain part of the user's deferred payment setup. Do not substitute fixture results for those checks. After the verified Day 11 Git checkpoint and manual-review reminder, the user repeatedly requested continuation. Day 12 proceeds with the manual checklist still pending; no browser pass is claimed.

References: W3C's [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [visible focus](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html) and [target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) guidance; [Vitest setup](https://vitest.dev/guide/), [Testing Library keyboard simulation](https://testing-library.com/docs/user-event/keyboard/) and [axe-core API](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md).

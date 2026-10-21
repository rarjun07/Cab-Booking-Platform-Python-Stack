export default function TripETA({ eta }) {
  if (!eta) return null
  return <div className="driver-location-card" aria-label="Estimated arrival">
    <strong>{eta.target === 'destination' ? 'ETA to destination' : 'Driver arrival estimate'}</strong>
    <p role="status">{eta.loading ? 'Calculating road ETA…' : eta.error ? eta.error : eta.available
      ? `${Math.max(1, Math.ceil(eta.duration_secs / 60))} min · ${(eta.distance_meters / 1000).toFixed(2)} km by road`
      : 'Waiting for a fresh shared driver location.'}</p>
    {eta.available && <p className="fare-note">Based on location shared at {new Date(eta.location_updated_at).toLocaleTimeString()}. Road-time estimate excludes live traffic; refreshes approximately every 15 seconds.</p>}
  </div>
}

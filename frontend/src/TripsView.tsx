import { useEffect, useState, type FormEvent } from 'react'
import { api, type FamilyProfile, type Trip, type TripDocument } from './api'

const blankTrip = () => ({ title: '', destination: '', start_date: '', end_date: '', notes: '' })

export function TripsView({ isAdmin }: { isAdmin: boolean }) {
  const [trips, setTrips] = useState<Trip[] | null>(null)
  const [profiles, setProfiles] = useState<FamilyProfile[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(blankTrip)
  const [participantName, setParticipantName] = useState('')
  const [participantProfile, setParticipantProfile] = useState('')
  const [preparation, setPreparation] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [fileKey, setFileKey] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const selected = trips?.find((trip) => trip.id === selectedId)

  async function refresh() {
    try { setTrips(await api.trips()) } catch { setTrips(null); setError('No se pudieron cargar los viajes.') }
  }
  useEffect(() => { void refresh(); void api.familyProfiles().then(setProfiles).catch(() => setProfiles([])) }, [])

  async function run(action: () => Promise<unknown>, message: string) {
    setBusy(true); setError(''); setNotice('')
    try { await action(); await refresh(); setNotice(message); return true }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo confirmar el cambio.'); return false }
    finally { setBusy(false) }
  }
  function open(trip?: Trip) {
    setSelectedId(trip?.id ?? null)
    setDraft(trip ? { title: trip.title, destination: trip.destination, start_date: trip.start_date || '', end_date: trip.end_date || '', notes: trip.notes } : blankTrip())
    setEditing(true); setError(''); setNotice('')
  }
  async function save(event: FormEvent) {
    event.preventDefault()
    const data = { ...draft, title: draft.title.trim(), destination: draft.destination.trim(), start_date: draft.start_date || null, end_date: draft.end_date || null }
    setBusy(true); setError(''); setNotice('')
    try {
      const saved = selectedId ? await api.updateTrip(selectedId, data) : await api.createTrip(data)
      await refresh(); setSelectedId(saved.id); setEditing(false); setNotice('Viaje guardado.')
    } catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo guardar.') }
    finally { setBusy(false) }
  }
  async function addParticipant(event: FormEvent) {
    event.preventDefault(); if (!selected) return
    if (await run(() => api.addTripParticipant(selected.id, { name: participantName.trim(), profile: participantProfile ? Number(participantProfile) : null }), 'Participante añadido.')) { setParticipantName(''); setParticipantProfile('') }
  }
  async function addPreparation(event: FormEvent) {
    event.preventDefault(); if (!selected) return
    if (await run(() => api.addTripPreparation(selected.id, preparation.trim()), 'Preparativo añadido.')) setPreparation('')
  }
  async function upload(event: FormEvent) {
    event.preventDefault(); if (!selected || !file) return
    if (await run(() => api.uploadTripDocument(selected.id, file), 'Documento guardado.')) { setFile(null); setFileKey((value) => value + 1) }
  }
  async function download(document: TripDocument) {
    if (!selected) return
    setError('')
    try {
      const blob = await api.downloadTripDocument(selected.id, document.id)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url; anchor.download = document.original_name; anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo descargar.') }
  }
  async function removeTrip(trip: Trip) {
    if (!window.confirm(`¿Eliminar «${trip.title}» y sus documentos?`)) return
    if (await run(() => api.deleteTrip(trip.id), 'Viaje eliminado.')) { setSelectedId(null); setEditing(false) }
  }

  return <>
    {selected || editing ? <button className="back-button" onClick={() => { setSelectedId(null); setEditing(false); setError(''); setNotice('') }}>← Volver a viajes</button> : null}
    <header className="page-header"><p className="eyebrow">Planes compartidos</p><h1>{selected ? selected.title : 'Viajes'}</h1></header>
    {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="success-message" role="status">{notice}</p>}
    {editing ? <form className="event-form" onSubmit={(event) => void save(event)}>
      <h2>{selectedId ? 'Editar viaje' : 'Nuevo viaje'}</h2>
      <label>Nombre<input required maxLength={180} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
      <label>Destino<input maxLength={180} value={draft.destination} onChange={(event) => setDraft({ ...draft, destination: event.target.value })} /></label>
      <div className="time-fields"><label>Desde<input type="date" value={draft.start_date} onChange={(event) => setDraft({ ...draft, start_date: event.target.value })} /></label><label>Hasta<input type="date" value={draft.end_date} onChange={(event) => setDraft({ ...draft, end_date: event.target.value })} /></label></div>
      <label>Notas<textarea value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} /></label>
      <button className="primary-button" disabled={busy || !draft.title.trim()}>Guardar viaje</button>
    </form> : selected ? <>
      <div className="detail-card"><div className="detail-row"><span>Destino</span><strong>{selected.destination || 'Sin datos'}</strong></div><div className="detail-row"><span>Fechas</span><strong>{selected.start_date || 'Sin datos'}{selected.end_date && ` al ${selected.end_date}`}</strong></div>{selected.notes && <div className="detail-row"><span>Notas</span><strong>{selected.notes}</strong></div>}</div>
      <section className="section-block"><h2>Participantes</h2>{selected.participants.length ? <ul className="family-detail-list">{selected.participants.map((person) => <li key={person.id}><span><strong>{person.name}</strong></span>{isAdmin && <button disabled={busy} onClick={() => { if (window.confirm(`¿Quitar a ${person.name}?`)) void run(() => api.deleteTripParticipant(selected.id, person.id), 'Participante retirado.') }}>Quitar</button>}</li>)}</ul> : <p className="muted section-empty">Sin datos</p>}
        {isAdmin && <form className="event-form family-inline-form" onSubmit={(event) => void addParticipant(event)}><label>Nombre<input required maxLength={160} value={participantName} onChange={(event) => setParticipantName(event.target.value)} /></label><label>Vincular perfil familiar (opcional)<select value={participantProfile} onChange={(event) => { const value = event.target.value; setParticipantProfile(value); if (value) setParticipantName(profiles.find((profile) => profile.id === Number(value))?.name || '') }}><option value="">Sin vínculo</option>{profiles.map((profile) => <option value={profile.id} key={profile.id}>{profile.name}</option>)}</select></label><button className="primary-button" disabled={busy || !participantName.trim()}>Añadir participante</button></form>}
      </section>
      <section className="section-block"><h2>Preparativos</h2><p className="muted intro">Se guardan en este viaje; no se envían automáticamente a To-do.</p>{selected.preparations.length ? <ul className="family-detail-list">{selected.preparations.map((item) => <li key={item.id}><span><strong>{item.title}</strong><small>{item.done ? 'Hecho' : 'Pendiente'}</small></span>{isAdmin && <div><button disabled={busy} onClick={() => void run(() => api.updateTripPreparation(selected.id, item.id, !item.done), item.done ? 'Preparativo reabierto.' : 'Preparativo completado.')}>{item.done ? 'Reabrir' : 'Completar'}</button><button disabled={busy} onClick={() => { if (window.confirm(`¿Eliminar «${item.title}»?`)) void run(() => api.deleteTripPreparation(selected.id, item.id), 'Preparativo eliminado.') }}>Eliminar</button></div>}</li>)}</ul> : <p className="muted section-empty">Sin datos</p>}
        {isAdmin && <form className="event-form family-inline-form" onSubmit={(event) => void addPreparation(event)}><label>Preparativo<input required maxLength={200} value={preparation} onChange={(event) => setPreparation(event.target.value)} /></label><button className="primary-button" disabled={busy || !preparation.trim()}>Añadir preparativo</button></form>}
      </section>
      <section className="section-block"><h2>Documentos privados</h2>{selected.documents.length ? <ul className="family-detail-list">{selected.documents.map((document) => <li key={document.id}><span><strong>{document.original_name}</strong><small>{Math.ceil(document.size / 1024)} KB</small></span>{isAdmin && <div><button disabled={busy} onClick={() => void download(document)}>Descargar</button><button disabled={busy} onClick={() => { if (window.confirm(`¿Eliminar «${document.original_name}»?`)) void run(() => api.deleteTripDocument(selected.id, document.id), 'Documento eliminado.') }}>Eliminar</button></div>}</li>)}</ul> : <p className="muted section-empty">Sin datos</p>}
        {isAdmin && <form className="event-form family-inline-form" onSubmit={(event) => void upload(event)}><label>Archivo (máximo 15 MB)<input key={fileKey} type="file" required onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="primary-button" disabled={busy || !file}>Subir documento</button></form>}
      </section>
      {isAdmin && <div className="detail-actions"><button className="secondary-button" onClick={() => open(selected)}>Editar viaje</button><button className="danger-button" disabled={busy} onClick={() => void removeTrip(selected)}>Eliminar viaje</button></div>}
    </> : <>
      {isAdmin && <button className="secondary-button family-add-button" onClick={() => open()}>Añadir viaje</button>}
      {trips === null ? <div className="empty-state"><strong>Sin conexión</strong></div> : trips.length ? <div className="family-list">{trips.map((trip) => <button className="family-row" key={trip.id} onClick={() => setSelectedId(trip.id)}><span className="family-avatar">{trip.title.charAt(0).toUpperCase()}</span><span><strong>{trip.title}</strong><small>{trip.destination || 'Destino sin datos'}{trip.start_date ? ` · ${trip.start_date}` : ''}</small></span><span aria-hidden="true">→</span></button>)}</div> : <div className="empty-state"><strong>Sin datos</strong><p>Aún no hay viajes.</p></div>}
    </>}
  </>
}

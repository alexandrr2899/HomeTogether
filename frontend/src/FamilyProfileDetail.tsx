import { useState, type FormEvent } from 'react'
import { api, type FamilyDocument, type FamilyProfile, type FamilyReferenceStatus, type FamilyResponsibility } from './api'
import { FamilyReferencePicker, type ReferenceChoice } from './FamilyReferencePicker'

function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'No se pudo confirmar el cambio.'
}

export function FamilyProfileDetail({ profile, isAdmin, onChanged, onBack }: {
  profile: FamilyProfile
  isAdmin: boolean
  onChanged: () => Promise<void>
  onBack: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [details, setDetails] = useState({
    name: profile.name, relationship: profile.relationship, phone: profile.phone,
    email: profile.email, birthday: profile.birthday || '', notes: profile.notes,
  })
  const [dateLabel, setDateLabel] = useState('')
  const [dateValue, setDateValue] = useState('')
  const [annual, setAnnual] = useState(true)
  const [addingDate, setAddingDate] = useState(false)
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDue, setTaskDue] = useState('')
  const [addingResponsibility, setAddingResponsibility] = useState(false)
  const [reference, setReference] = useState<ReferenceChoice>({ source: '', id: '', label: '' })
  const [referenceStatuses, setReferenceStatuses] = useState<Record<number, FamilyReferenceStatus>>({})
  const [checkingReference, setCheckingReference] = useState<number | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [fileInputKey, setFileInputKey] = useState(0)
  const [addingDocument, setAddingDocument] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      await onChanged()
      setNotice(success)
      return true
    } catch (problem) {
      setError(errorText(problem))
      return false
    } finally { setBusy(false) }
  }

  async function saveProfile(event: FormEvent) {
    event.preventDefault()
    const confirmed = await run(() => api.updateFamilyProfile(profile.id, {
      ...details, name: details.name.trim(), relationship: details.relationship.trim(),
      birthday: details.birthday || null,
    }), 'Perfil guardado.')
    if (confirmed) setEditing(false)
  }

  async function addDate(event: FormEvent) {
    event.preventDefault()
    if (await run(() => api.createFamilyDate(profile.id, {
      label: dateLabel.trim(), date: dateValue, repeats_annually: annual,
    }), 'Fecha guardada.')) {
      setDateLabel('')
      setDateValue('')
      setAddingDate(false)
    }
  }

  async function addResponsibility(event: FormEvent) {
    event.preventDefault()
    if (await run(() => api.createResponsibility(profile.id, {
      title: taskTitle.trim(), due_date: taskDue || null,
      external_source: reference.source, external_id: reference.id,
    }), 'Responsabilidad guardada.')) {
      setTaskTitle('')
      setTaskDue('')
      setReference({ source: '', id: '', label: '' })
      setAddingResponsibility(false)
    }
  }

  async function checkReference(responsibility: FamilyResponsibility) {
    setCheckingReference(responsibility.id)
    setError('')
    try {
      const result = await api.responsibilitySource(profile.id, responsibility.id)
      setReferenceStatuses((current) => ({ ...current, [responsibility.id]: result }))
    } catch (problem) { setError(errorText(problem)) }
    finally { setCheckingReference(null) }
  }

  async function upload(event: FormEvent) {
    event.preventDefault()
    if (!file) return
    if (await run(() => api.uploadFamilyDocument(profile.id, file), 'Documento guardado en el espacio privado.')) {
      setFile(null)
      setFileInputKey((value) => value + 1)
      setAddingDocument(false)
    }
  }

  async function download(document: FamilyDocument) {
    setError('')
    try {
      const blob = await api.downloadFamilyDocument(profile.id, document.id)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = document.original_name
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (problem) { setError(errorText(problem)) }
  }

  async function removeProfile() {
    if (!window.confirm(`¿Eliminar el perfil de ${profile.name} y sus datos y documentos?`)) return
    if (await run(() => api.deleteFamilyProfile(profile.id), 'Perfil eliminado.')) onBack()
  }

  return <>
    <button className="back-button" onClick={onBack}>← Familia</button>
    <header className="page-header"><p className="eyebrow">Perfil familiar</p><h1 className="detail-heading">{profile.name}</h1><p className="muted">{profile.relationship || 'Relación sin datos'}</p></header>
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}
    <div className="family-profile-grid">
    <section className="section-block family-profile-panel family-contact"><div className="section-heading"><h2>Datos y contacto</h2>{isAdmin && <button className="text-button" onClick={() => { setDetails({ name: profile.name, relationship: profile.relationship, phone: profile.phone, email: profile.email, birthday: profile.birthday || '', notes: profile.notes }); setEditing(!editing) }}>{editing ? 'Cerrar' : 'Editar'}</button>}</div>
      {editing ? <form className="event-form" onSubmit={(event) => void saveProfile(event)}><label>Nombre<input required maxLength={160} value={details.name} onChange={(event) => setDetails({ ...details, name: event.target.value })} /></label><label>Relación familiar<input maxLength={160} value={details.relationship} onChange={(event) => setDetails({ ...details, relationship: event.target.value })} /></label><label>Teléfono<input type="tel" maxLength={40} value={details.phone} onChange={(event) => setDetails({ ...details, phone: event.target.value })} /></label><label>Correo<input type="email" value={details.email} onChange={(event) => setDetails({ ...details, email: event.target.value })} /></label><label>Cumpleaños<input type="date" value={details.birthday} onChange={(event) => setDetails({ ...details, birthday: event.target.value })} /></label><label>Notas<input value={details.notes} onChange={(event) => setDetails({ ...details, notes: event.target.value })} /></label><button className="primary-button" disabled={busy || !details.name.trim()}>Guardar perfil</button></form> : <div className="detail-card"><div className="detail-row"><span>Teléfono</span><strong>{profile.phone || 'Sin datos'}</strong></div><div className="detail-row"><span>Correo</span><strong>{profile.email || 'Sin datos'}</strong></div><div className="detail-row"><span>Cumpleaños</span><strong>{profile.birthday || 'Sin datos'}</strong></div>{profile.notes && <div className="detail-row"><span>Notas</span><strong>{profile.notes}</strong></div>}</div>}
    </section>
    <section className="section-block family-profile-panel"><div className="section-heading"><h2>Fechas importantes</h2>{isAdmin && <button className="text-button" onClick={() => setAddingDate(!addingDate)}>{addingDate ? 'Cerrar' : 'Añadir fecha'}</button>}</div>{profile.important_dates.length ? <ul className="family-detail-list">{profile.important_dates.map((date) => <li key={date.id}><span><strong>{date.label}</strong><small>{date.date}{date.repeats_annually ? ' · Cada año' : ''}</small></span>{isAdmin && <button disabled={busy} onClick={() => { if (window.confirm(`¿Eliminar «${date.label}»?`)) void run(() => api.deleteFamilyDate(profile.id, date.id), 'Fecha eliminada.') }}>Eliminar</button>}</li>)}</ul> : <p className="muted section-empty">Sin datos</p>}
      {isAdmin && addingDate && <form className="event-form family-inline-form" onSubmit={(event) => void addDate(event)}><label>Descripción<input required maxLength={120} value={dateLabel} onChange={(event) => setDateLabel(event.target.value)} /></label><label>Fecha<input required type="date" value={dateValue} onChange={(event) => setDateValue(event.target.value)} /></label><label className="checkbox-label"><input type="checkbox" checked={annual} onChange={(event) => setAnnual(event.target.checked)} /> Repetir cada año</label><button className="primary-button" disabled={busy || !dateLabel.trim() || !dateValue}>Guardar fecha</button></form>}
    </section>
    <section className="section-block family-profile-panel"><div className="section-heading"><h2>Responsabilidades</h2>{isAdmin && <button className="text-button" onClick={() => setAddingResponsibility(!addingResponsibility)}>{addingResponsibility ? 'Cerrar' : 'Añadir'}</button>}</div><p className="muted intro">Notas propias que puedes vincular con una tarea o evento existente.</p>{profile.responsibilities.length ? <ul className="family-detail-list">{profile.responsibilities.map((responsibility) => <li key={responsibility.id}><span><strong>{responsibility.title}</strong><small>{responsibility.due_date ? `Para ${responsibility.due_date}` : 'Sin fecha'}{responsibility.external_source ? ` · Vinculada a ${responsibility.external_source === 'google_calendar' ? 'Calendario' : 'To-do'}` : ''}</small>{responsibility.external_source && <><button className="reference-check" disabled={checkingReference === responsibility.id} onClick={() => void checkReference(responsibility)}>{checkingReference === responsibility.id ? 'Consultando…' : 'Consultar vínculo'}</button>{referenceStatuses[responsibility.id] && <small className="reference-status">{referenceStatuses[responsibility.id].status === 'Conectado' ? `${referenceStatuses[responsibility.id].title} · ${referenceStatuses[responsibility.id].item_status === 'completed' ? 'Completada' : 'Disponible en origen'}` : `${referenceStatuses[responsibility.id].status} en origen`}</small>}</>}</span>{isAdmin && <button disabled={busy} onClick={() => { if (window.confirm(`¿Eliminar «${responsibility.title}»?`)) void run(() => api.deleteResponsibility(profile.id, responsibility.id), 'Responsabilidad eliminada.') }}>Eliminar</button>}</li>)}</ul> : <p className="muted section-empty">Sin datos</p>}
      {isAdmin && addingResponsibility && <form className="event-form family-inline-form" onSubmit={(event) => void addResponsibility(event)}><label>Responsabilidad<input required maxLength={200} value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} /></label><label>Fecha opcional para esta nota<input type="date" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} /></label><FamilyReferencePicker value={reference} onChange={setReference} /><button className="primary-button" disabled={busy || !taskTitle.trim()}>Guardar responsabilidad</button></form>}
    </section>
    <section className="section-block family-profile-panel"><div className="section-heading"><h2>Documentos privados</h2>{isAdmin && <button className="text-button" onClick={() => setAddingDocument(!addingDocument)}>{addingDocument ? 'Cerrar' : 'Subir archivo'}</button>}</div><p className="muted intro">Solo Alexander y Lastenia pueden descargarlos.</p>{profile.documents.length ? <ul className="family-detail-list">{profile.documents.map((document) => <li key={document.id}><span><strong>{document.original_name}</strong><small>{Math.ceil(document.size / 1024)} KB</small></span><div>{isAdmin && <><button disabled={busy} onClick={() => void download(document)}>Descargar</button><button disabled={busy} onClick={() => { if (window.confirm(`¿Eliminar «${document.original_name}»?`)) void run(() => api.deleteFamilyDocument(profile.id, document.id), 'Documento eliminado.') }}>Eliminar</button></>}</div></li>)}</ul> : <p className="muted section-empty">Sin datos</p>}
      {isAdmin && addingDocument && <form className="event-form family-inline-form" onSubmit={(event) => void upload(event)}><label>Archivo (máximo 15 MB)<input key={fileInputKey} type="file" required onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="primary-button" disabled={busy || !file}>Subir documento</button></form>}
    </section>
    </div>
    {isAdmin && <button className="danger-button family-profile-delete" disabled={busy} onClick={() => void removeProfile()}>Eliminar perfil</button>}
  </>
}

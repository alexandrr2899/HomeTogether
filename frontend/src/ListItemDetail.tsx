import { useState, type FormEvent } from 'react'
import { api, type HouseholdList, type ListItem } from './api'

function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'No se pudo confirmar la operación.'
}

export function ListItemDetail({ list, item, isAdmin, onBack, onChanged }: {
  list: HouseholdList
  item: ListItem
  isAdmin: boolean
  onBack: () => void
  onChanged: () => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [summary, setSummary] = useState(item.summary)
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
      await onChanged()
      return false
    } finally {
      setBusy(false)
    }
  }

  async function rename(event: FormEvent) {
    event.preventDefault()
    const next = summary.trim()
    if (!next || next === item.summary) return
    if (await run(() => api.updateListItem(list.id, item.uid, { summary: next }), 'Cambio confirmado en Home Assistant.')) {
      setEditing(false)
    }
  }

  async function toggle() {
    await run(() => api.updateListItem(list.id, item.uid, {
      status: item.status === 'completed' ? 'needs_action' : 'completed',
    }), 'Estado confirmado en Home Assistant.')
  }

  async function remove() {
    if (!window.confirm(`¿Eliminar «${item.summary}» de ${list.name}?`)) return
    if (await run(() => api.deleteListItem(list.id, item.uid), 'Eliminación confirmada en Home Assistant.')) onBack()
  }

  return <>
    <button className="back-button" onClick={onBack}>← Volver a {list.name}</button>
    <header className="page-header"><p className="eyebrow">{list.name}</p><h1 className="detail-heading">{item.summary}</h1></header>
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}
    <section className="detail-card" aria-label="Detalles del ítem">
      <div className="detail-row"><span>Estado</span><strong>{item.status === 'completed' ? 'Completado' : 'Pendiente'}</strong></div>
      <div className="detail-row"><span>Origen</span><strong>Alexa mediante Home Assistant</strong></div>
      {item.due && <div className="detail-row"><span>Vence</span><strong>{item.due}</strong></div>}
    </section>
    {isAdmin && <section className="detail-actions" aria-label="Acciones del ítem">
      <button className="primary-button" disabled={busy} onClick={() => void toggle()}>{item.status === 'completed' ? 'Reabrir' : 'Marcar como completado'}</button>
      <button className="secondary-button" disabled={busy} onClick={() => { setSummary(item.summary); setEditing(true) }}>Editar nombre</button>
      {editing && <form className="event-form" onSubmit={(event) => void rename(event)}><label>Nuevo nombre<input required maxLength={255} value={summary} onChange={(event) => setSummary(event.target.value)} /></label><button className="primary-button" disabled={busy || !summary.trim() || summary.trim() === item.summary}>Guardar cambio</button><button className="plain-button" type="button" onClick={() => setEditing(false)}>Cancelar</button></form>}
      <button className="danger-button" disabled={busy} onClick={() => void remove()}>Eliminar ítem</button>
    </section>}
  </>
}

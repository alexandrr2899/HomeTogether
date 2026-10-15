import { useState, type FormEvent } from 'react'
import { api, type HouseholdList, type ListItem, type ListsResponse } from './api'
import { ListItemDetail } from './ListItemDetail'

function newOperationId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = [...bytes].map((part) => part.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function draftKey(listId: string) {
  return `home-together-list-draft-${listId}`
}

function savedDraft(listId: string) {
  try {
    const raw = sessionStorage.getItem(draftKey(listId))
    if (raw) {
      const parsed = JSON.parse(raw) as { summary?: string; operationId?: string }
      if (typeof parsed.summary === 'string' && typeof parsed.operationId === 'string') {
        return { summary: parsed.summary, operationId: parsed.operationId }
      }
    }
  } catch { /* Private browsing can disable storage. */ }
  return { summary: '', operationId: newOperationId() }
}

function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'No se pudo confirmar la operación.'
}

function lastChecked(value: string | null | undefined) {
  if (!value) return 'Sin datos'
  return new Intl.DateTimeFormat('es-HN', {
    timeZone: 'America/Tegucigalpa', dateStyle: 'short', timeStyle: 'short',
  }).format(new Date(value))
}

function ListCard({ list, isAdmin, onChanged, onOpen }: {
  list: HouseholdList
  isAdmin: boolean
  onChanged: () => Promise<void>
  onOpen: (item: ListItem) => void
}) {
  const [draft, setDraft] = useState(() => savedDraft(list.id))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const pending = list.items.filter((item) => item.status === 'needs_action')
  const completed = list.items.filter((item) => item.status === 'completed')

  function changeDraft(summary: string) {
    const next = { summary, operationId: newOperationId() }
    setDraft(next)
    try { sessionStorage.setItem(draftKey(list.id), JSON.stringify(next)) } catch { /* Keep the in-memory draft. */ }
  }

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

  async function add(event: FormEvent) {
    event.preventDefault()
    const value = draft.summary.trim()
    if (!value) return
    const confirmed = await run(
      () => api.createListItem(list.id, draft.operationId, value),
      `Ítem confirmado en ${list.name}.`,
    )
    if (confirmed) {
      setDraft({ summary: '', operationId: newOperationId() })
      try { sessionStorage.removeItem(draftKey(list.id)) } catch { /* No stored draft. */ }
    }
  }

  async function toggle(item: ListItem) {
    await run(
      () => api.updateListItem(list.id, item.uid, {
        status: item.status === 'completed' ? 'needs_action' : 'completed',
      }),
      'Estado confirmado en Home Assistant.',
    )
  }

  function itemRow(item: ListItem) {
    return <li key={item.uid}>
      {isAdmin ? <button className="item-toggle" disabled={busy} aria-label={item.status === 'completed' ? `Reabrir ${item.summary}` : `Completar ${item.summary}`} onClick={() => void toggle(item)}>{item.status === 'completed' ? '✓' : ''}</button> : <span className="item-circle" aria-hidden="true" />}
      <div className="item-body"><button className="item-title" onClick={() => onOpen(item)}>{item.summary}<span aria-hidden="true">→</span></button>{item.due && <small>Vence {item.due}</small>}</div>
    </li>
  }

  return <section className="list-section">
    <div className="section-heading"><h3>{list.name}</h3><span className="count">{list.status === 'Conectado' ? pending.length : '—'}</span></div>
    <p className="source-line">{list.status} · Home Assistant / Alexa</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}
    {list.status !== 'Conectado' ? <div className="empty-state"><strong>{list.status}</strong></div> : <>
      {isAdmin && <form className="list-add" onSubmit={(event) => void add(event)}><label className="visually-hidden" htmlFor={`new-${list.id}`}>Nuevo ítem en {list.name}</label><input id={`new-${list.id}`} value={draft.summary} maxLength={255} placeholder={`Añadir a ${list.name}`} onChange={(event) => changeDraft(event.target.value)} /><button disabled={busy || !draft.summary.trim()}>{busy ? '…' : 'Añadir'}</button></form>}
      {pending.length ? <ul className="item-list">{pending.map(itemRow)}</ul> : <div className="empty-state"><strong>Sin datos</strong><p>No hay ítems pendientes en esta lista.</p></div>}
      {completed.length > 0 && <details className="completed-items"><summary>Completados ({completed.length})</summary><ul className="item-list">{completed.map(itemRow)}</ul></details>}
    </>}
  </section>
}

export function ListsView({ lists, isAdmin, onChanged }: {
  lists: ListsResponse | null
  isAdmin: boolean
  onChanged: () => Promise<void>
}) {
  const [selected, setSelected] = useState<'todas' | 'tareas' | 'compras' | 'super'>('todas')
  const [openItem, setOpenItem] = useState<{ listId: HouseholdList['id']; uid: string } | null>(null)
  const detailList = lists?.lists.find((list) => list.id === openItem?.listId)
  const detailItem = detailList?.items.find((item) => item.uid === openItem?.uid)
  const visible = lists?.lists.filter((list) => selected === 'todas' || list.id === selected) ?? []
  if (openItem && detailList && detailItem) {
    return <ListItemDetail list={detailList} item={detailItem} isAdmin={isAdmin} onBack={() => setOpenItem(null)} onChanged={onChanged} />
  }
  if (openItem) return <><button className="back-button" onClick={() => setOpenItem(null)}>← Volver a listas</button><div className="empty-state"><strong>Sin datos</strong><p>Este ítem ya no está disponible en Home Assistant.</p></div></>
  return <><header className="page-header"><p className="eyebrow">Lo que tenemos pendiente</p><h1>Organizar</h1></header>
    <div className="chips" role="tablist" aria-label="Filtrar listas">{[
      ['todas', 'Todas'], ['tareas', 'To-do'], ['compras', 'Compras'], ['super', 'Súper'],
    ].map(([id, label]) => <button key={id} role="tab" aria-selected={selected === id} className={selected === id ? 'chip active' : 'chip'} onClick={() => setSelected(id as typeof selected)}>{label}</button>)}</div>
    {visible.length ? visible.map((list) => <ListCard key={list.id} list={list} isAdmin={isAdmin} onChanged={onChanged} onOpen={(item) => setOpenItem({ listId: list.id, uid: item.uid })} />) : <div className="empty-state"><strong>Sin conexión</strong><p>No se pudo consultar Home Assistant.</p></div>}
    <p className="updated">Última consulta: {lastChecked(lists?.last_checked_at)}</p>
  </>
}

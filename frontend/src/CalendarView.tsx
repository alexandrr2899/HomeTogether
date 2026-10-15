import { useEffect, useState, type FormEvent } from 'react'
import { api, type CalendarEvent, type CalendarResponse } from './api'
import { eventsByDay, monthCells, nextDay, nextMonth } from './calendarDates'
import { fetchMonth } from './calendarService'

type Draft = { operationId: string; summary: string; date: string; allDay: boolean; startTime: string; endTime: string }
const DRAFT_KEY = 'home-together-calendar-draft'
const zone = 'America/Tegucigalpa'

function newOperationId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = [...bytes].map((part) => part.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

function localDay() {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date())
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${value.year}-${value.month}-${value.day}`
}

function newDraft(): Draft {
  return { operationId: newOperationId(), summary: '', date: localDay(), allDay: false, startTime: '12:00', endTime: '12:30' }
}

function savedDraft(): Draft {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    if (raw) {
      const value = JSON.parse(raw) as Draft
      if (value.operationId && value.date && typeof value.summary === 'string') return value
    }
  } catch { /* Private browsing can disable storage. */ }
  return newDraft()
}

function monthLabel(month: string) {
  const label = new Intl.DateTimeFormat('es-HN', { timeZone: 'UTC', month: 'long', year: 'numeric' }).format(new Date(`${month}-01T12:00:00Z`))
  return label.charAt(0).toUpperCase() + label.slice(1)
}

function eventDate(event: CalendarEvent) {
  if (event.start?.date) {
    const [year, month, day] = event.start.date.split('-')
    return `${day}/${month}/${year} · Todo el día`
  }
  if (!event.start?.dateTime) return 'Fecha sin datos'
  return new Intl.DateTimeFormat('es-HN', { timeZone: zone, dateStyle: 'medium', timeStyle: 'short' }).format(new Date(event.start.dateTime))
}

function message(error: unknown) {
  return error instanceof Error ? error.message : 'No se pudo confirmar el cambio en Google.'
}

export function CalendarView({ calendar, isAdmin, onChanged }: {
  calendar: CalendarResponse | null
  isAdmin: boolean
  onChanged: () => Promise<void>
}) {
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState<Draft>(savedDraft)
  const [editing, setEditing] = useState<string | null>(null)
  const [editedTitle, setEditedTitle] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [month, setMonth] = useState(() => localDay().slice(0, 7))
  const [selectedDay, setSelectedDay] = useState(localDay)
  const [monthResult, setMonthResult] = useState<CalendarResponse | null>(null)
  const [loadingMonth, setLoadingMonth] = useState(true)

  useEffect(() => {
    let active = true
    setLoadingMonth(true)
    setMonthResult(null)
    void fetchMonth(month).then((result) => {
      if (active) setMonthResult(result)
    }).catch(() => {
      if (active) setMonthResult({ status: 'Sin conexión', source: 'google_calendar', events: [], last_checked_at: null })
    }).finally(() => { if (active) setLoadingMonth(false) })
    return () => { active = false }
  }, [month])

  function changeMonth(next: string) {
    setMonth(next)
    const today = localDay()
    setSelectedDay(today.startsWith(next) ? today : `${next}-01`)
    setEditing(null)
    setNotice('')
  }

  async function refreshAfterChange() {
    const [result] = await Promise.allSettled([fetchMonth(month), onChanged()])
    if (result.status === 'fulfilled') setMonthResult(result.value)
    else setError('El cambio se confirmó en Google, pero no se pudo actualizar la vista del mes.')
  }

  function changeDraft(patch: Partial<Draft>) {
    const next = { ...draft, ...patch }
    setDraft(next)
    try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(next)) } catch { /* Keep the in-memory draft. */ }
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    setError('')
    setNotice('')
    if (!draft.summary.trim()) return setError('Escribe un título.')
    if (!draft.allDay && draft.endTime <= draft.startTime) return setError('La hora de fin debe ser posterior al inicio.')
    const start = draft.allDay ? { date: draft.date } : { dateTime: `${draft.date}T${draft.startTime}:00-06:00`, timeZone: zone }
    const end = draft.allDay ? { date: nextDay(draft.date) } : { dateTime: `${draft.date}T${draft.endTime}:00-06:00`, timeZone: zone }
    setBusy(true)
    try {
      await api.createCalendarEvent({ operation_id: draft.operationId, summary: draft.summary.trim(), start, end })
      try { sessionStorage.removeItem(DRAFT_KEY) } catch { /* No stored draft. */ }
      setDraft(newDraft())
      setAdding(false)
      await refreshAfterChange()
      setNotice('Evento confirmado en Google Calendar.')
    } catch (problem) {
      const detail = message(problem)
      setError(detail.includes('incierto') ? `${detail} Puedes reintentar este mismo borrador; el backend consultará su ID antes de escribir.` : detail)
    } finally { setBusy(false) }
  }

  async function rename(event: CalendarEvent) {
    if (!event.etag || !editedTitle.trim()) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await api.updateCalendarEvent(event.id, event.etag, { summary: editedTitle.trim() })
      setEditing(null)
      await refreshAfterChange()
      setNotice('Cambio confirmado en Google Calendar.')
    } catch (problem) {
      setError(message(problem))
      try { setMonthResult(await fetchMonth(month)) } catch { /* Keep the previous view. */ }
    } finally { setBusy(false) }
  }

  async function remove(event: CalendarEvent) {
    if (!event.etag || !window.confirm(`¿Eliminar «${event.summary || 'este evento'}» del calendario familiar?`)) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await api.deleteCalendarEvent(event.id, event.etag)
      await refreshAfterChange()
      setNotice('Eliminación confirmada en Google Calendar.')
    } catch (problem) {
      setError(message(problem))
      try { setMonthResult(await fetchMonth(month)) } catch { /* Keep the previous view. */ }
    } finally { setBusy(false) }
  }

  const connected = monthResult?.status === 'Conectado'
  const byDay = eventsByDay(monthResult?.events || [], month)
  const selectedEvents = byDay.get(selectedDay) || []
  const dayLabel = new Intl.DateTimeFormat('es-HN', { timeZone: 'UTC', weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(`${selectedDay}T12:00:00Z`))
  const selectedLabel = dayLabel.charAt(0).toUpperCase() + dayLabel.slice(1)
  return <>
    <header className="page-header"><p className="eyebrow">Agenda familiar</p><h1>Calendario</h1></header>
    <p className="muted intro">Zona horaria de la app: America/Tegucigalpa · Fuente: Google Calendar</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}
    <div className="calendar-toolbar"><button type="button" className="calendar-arrow" aria-label="Mes anterior" disabled={busy} onClick={() => changeMonth(nextMonth(month, -1))}>‹</button><h2 aria-live="polite">{monthLabel(month)}</h2><button type="button" className="calendar-arrow" aria-label="Mes siguiente" disabled={busy} onClick={() => changeMonth(nextMonth(month))}>›</button><button type="button" className="calendar-today" disabled={busy} onClick={() => changeMonth(localDay().slice(0, 7))}>Hoy</button></div>
    {isAdmin && connected && <div className="calendar-actions"><button className="secondary-button" onClick={() => { if (!draft.summary.trim()) changeDraft({ date: selectedDay }); setAdding(!adding) }}>{adding ? 'Cerrar formulario' : 'Añadir evento'}</button></div>}
    {adding && connected && <form className="event-form" onSubmit={(event) => void create(event)}>
      <h2>Nuevo evento</h2>
      <label>Título<input required maxLength={200} value={draft.summary} onChange={(event) => changeDraft({ summary: event.target.value })} /></label>
      <label>Fecha<input required type="date" value={draft.date} onChange={(event) => changeDraft({ date: event.target.value })} /></label>
      <label className="checkbox-label"><input type="checkbox" checked={draft.allDay} onChange={(event) => changeDraft({ allDay: event.target.checked })} /> Todo el día</label>
      {!draft.allDay && <div className="time-fields"><label>Inicio<input type="time" required value={draft.startTime} onChange={(event) => changeDraft({ startTime: event.target.value })} /></label><label>Fin<input type="time" required value={draft.endTime} onChange={(event) => changeDraft({ endTime: event.target.value })} /></label></div>}
      <button className="primary-button" disabled={busy}>{busy ? 'Confirmando…' : 'Guardar en Google Calendar'}</button>
    </form>}
    {connected ? <div className="calendar-layout"><div className="calendar-month" aria-label={`Calendario de ${monthLabel(month)}`}>
      {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((name) => <div className="calendar-weekday" key={name}>{name}</div>)}
      {monthCells(month).map((day, index) => day ? <button type="button" key={day} className={`calendar-day ${day === selectedDay ? 'selected' : ''} ${day === localDay() ? 'today' : ''}`} aria-label={`${day}, ${byDay.get(day)?.length || 0} eventos`} aria-pressed={day === selectedDay} onClick={() => { setSelectedDay(day); setEditing(null) }}>
        <span className="calendar-day-number">{Number(day.slice(-2))}</span><span className="calendar-day-events">{(byDay.get(day) || []).slice(0, 2).map((event) => <span className="calendar-event-chip" key={event.id} title={event.summary || 'Sin título'}>{event.summary || 'Sin título'}</span>)}</span>{(byDay.get(day)?.length || 0) > 2 && <span className="calendar-event-more">+{(byDay.get(day)?.length || 0) - 2}</span>}
      </button> : <div className="calendar-day outside" key={`outside-${index}`} aria-hidden="true" />)}
    </div><section className="calendar-agenda" aria-label={`Eventos del ${selectedLabel}`}><div className="section-heading"><h2>{selectedLabel}</h2><span className="count">{selectedEvents.length}</span></div>
      {selectedEvents.length ? <div className="event-list">{selectedEvents.map((event) => <article className="event-card" key={event.id}>
      <span className="event-time">{eventDate(event)}</span>
      <div><h2>{event.summary || 'Sin título'}</h2>{event.location && <p>{event.location}</p>}
        {event.recurringEventId && <p>Ocurrencia recurrente · edición desde Google Calendar por ahora</p>}
        {isAdmin && !event.recurringEventId && event.etag && <div className="event-buttons">
          <button type="button" onClick={() => { setEditing(event.id); setEditedTitle(event.summary || '') }}>Editar título</button>
          <button type="button" disabled={busy} onClick={() => void remove(event)}>Eliminar</button>
        </div>}
        {editing === event.id && <div className="inline-edit"><label>Nuevo título<input value={editedTitle} maxLength={200} onChange={(change) => setEditedTitle(change.target.value)} /></label><button disabled={busy || !editedTitle.trim()} onClick={() => void rename(event)}>Guardar</button><button onClick={() => setEditing(null)}>Cancelar</button></div>}
      </div>
    </article>)}</div> : <div className="empty-state"><strong>Sin datos</strong><p>No hay eventos en este día.</p></div>}
    </section></div> : <div className="empty-state"><strong>{loadingMonth ? 'Cargando mes…' : monthResult?.status || calendar?.status || 'Sin configurar'}</strong><p>{loadingMonth ? 'Consultando Google Calendar.' : 'Revisa la conexión de Google Calendar en Configuración.'}</p></div>}
    <p className="updated">Última consulta: {monthResult?.last_checked_at ? new Intl.DateTimeFormat('es-HN', { timeZone: zone, dateStyle: 'short', timeStyle: 'short' }).format(new Date(monthResult.last_checked_at)) : 'Sin datos'}</p>
  </>
}

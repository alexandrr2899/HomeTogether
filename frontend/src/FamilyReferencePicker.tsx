import { useEffect, useState } from 'react'
import { api, type CalendarEvent, type ListItem } from './api'
import { nextMonth } from './calendarDates'
import { fetchMonth } from './calendarService'

export type ReferenceChoice = { source: '' | 'google_calendar' | 'home_assistant_todo'; id: string; label: string }
type Kind = 'none' | 'tareas' | 'calendar'

function currentMonth() {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Tegucigalpa', year: 'numeric', month: '2-digit' }).formatToParts(new Date())
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}`
}

function eventDate(event: CalendarEvent) {
  if (event.start?.date) return `${event.start.date} · Todo el día`
  if (event.start?.dateTime) return new Intl.DateTimeFormat('es-HN', { timeZone: 'America/Tegucigalpa', dateStyle: 'medium', timeStyle: 'short' }).format(new Date(event.start.dateTime))
  return 'Fecha sin datos'
}

export function FamilyReferencePicker({ value, onChange }: { value: ReferenceChoice; onChange: (value: ReferenceChoice) => void }) {
  const [kind, setKind] = useState<Kind>('none')
  const [month, setMonth] = useState(currentMonth)
  const [tasks, setTasks] = useState<ListItem[]>([])
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [status, setStatus] = useState('')

  useEffect(() => {
    let active = true
    if (kind === 'none') return () => { active = false }
    setStatus('Cargando…')
    const query = kind === 'tareas'
      ? api.lists().then((result) => {
        const list = result.lists.find((item) => item.id === 'tareas')
        return { status: list?.status || 'Sin configurar', tasks: list?.items || [], events: [] as CalendarEvent[] }
      })
      : fetchMonth(month).then((result) => ({ status: result.status, tasks: [] as ListItem[], events: result.events.filter((item) => item.status !== 'cancelled') }))
    void query.then((result) => {
      if (!active) return
      setStatus(result.status)
      setTasks(result.tasks)
      setEvents(result.events)
    }).catch(() => { if (active) setStatus('Sin conexión') })
    return () => { active = false }
  }, [kind, month])

  function chooseKind(next: Kind) {
    setKind(next)
    onChange({ source: '', id: '', label: '' })
  }

  return <div className="reference-picker"><span className="reference-title">Vincular elemento existente (opcional)</span>
    <div className="reference-kinds">
      {([['none', 'Sin vínculo'], ['tareas', 'To-do'], ['calendar', 'Calendario']] as const).map(([key, label]) => <button key={key} type="button" className={kind === key ? 'reference-kind selected' : 'reference-kind'} aria-pressed={kind === key} onClick={() => chooseKind(key)}>{label}</button>)}
    </div>
    {kind === 'calendar' && <div className="reference-month"><button type="button" aria-label="Mes anterior" onClick={() => setMonth(nextMonth(month, -1))}>‹</button><span>{month}</span><button type="button" aria-label="Mes siguiente" onClick={() => setMonth(nextMonth(month))}>›</button></div>}
    {kind !== 'none' && (status === 'Conectado' ? <div className="reference-results">
      {kind === 'tareas' && (tasks.length ? tasks.map((item) => <button type="button" key={item.uid} aria-pressed={value.id === `tareas:${item.uid}`} className={value.id === `tareas:${item.uid}` ? 'reference-option selected' : 'reference-option'} onClick={() => onChange({ source: 'home_assistant_todo', id: `tareas:${item.uid}`, label: item.summary })}><strong>{item.summary}</strong><small>{item.status === 'completed' ? 'Completada' : 'Pendiente'} · To-do</small></button>) : <p className="muted">Sin datos en To-do.</p>)}
      {kind === 'calendar' && (events.length ? events.map((event) => <button type="button" key={event.id} aria-pressed={value.id === event.id} className={value.id === event.id ? 'reference-option selected' : 'reference-option'} onClick={() => onChange({ source: 'google_calendar', id: event.id, label: event.summary || 'Sin título' })}><strong>{event.summary || 'Sin título'}</strong><small>{eventDate(event)}</small></button>) : <p className="muted">Sin datos en este mes.</p>)}
    </div> : <p className="muted">{status || 'Cargando…'}</p>)}
    {value.id && <p className="reference-chosen">Vínculo elegido: <strong>{value.label}</strong></p>}
  </div>
}

import { api, type CalendarEvent, type CalendarResponse } from './api'
import { nextMonth } from './calendarDates'

export async function fetchMonth(month: string): Promise<CalendarResponse> {
  const start = `${month}-01T00:00:00-06:00`
  const end = `${nextMonth(month)}-01T00:00:00-06:00`
  const events: CalendarEvent[] = []
  const seen = new Set<string>()
  let token: string | undefined
  for (let page = 0; page < 20; page += 1) {
    const result = await api.calendar(start, end, token)
    if (result.status !== 'Conectado') return result
    events.push(...result.events)
    token = result.next_page_token || undefined
    if (!token) return { ...result, events, next_page_token: null }
    if (seen.has(token)) throw new Error('La paginación de Google Calendar se repitió. Actualiza la agenda.')
    seen.add(token)
  }
  throw new Error('El mes contiene demasiadas páginas. Consulta Google Calendar directamente.')
}

import type { CalendarEvent } from './api'

const zone = 'America/Tegucigalpa'

export function nextDay(day: string) {
  const date = new Date(`${day}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() + 1)
  return date.toISOString().slice(0, 10)
}

export function nextMonth(month: string, change = 1) {
  const date = new Date(`${month}-01T12:00:00Z`)
  date.setUTCMonth(date.getUTCMonth() + change)
  return date.toISOString().slice(0, 7)
}

function zonedParts(value: string) {
  return Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(value)).map((part) => [part.type, part.value]))
}

function startDay(event: CalendarEvent) {
  if (event.start?.date) return event.start.date
  if (!event.start?.dateTime) return null
  const parts = zonedParts(event.start.dateTime)
  return `${parts.year}-${parts.month}-${parts.day}`
}

function exclusiveEndDay(event: CalendarEvent) {
  if (event.end?.date) return event.end.date
  if (event.end?.dateTime) {
    const parts = zonedParts(event.end.dateTime)
    const day = `${parts.year}-${parts.month}-${parts.day}`
    return parts.hour === '00' && parts.minute === '00' && parts.second === '00' ? day : nextDay(day)
  }
  const day = startDay(event)
  return day ? nextDay(day) : null
}

export function monthCells(month: string) {
  const first = new Date(`${month}-01T12:00:00Z`)
  const offset = (first.getUTCDay() + 6) % 7
  const total = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate()
  return Array.from({ length: Math.ceil((offset + total) / 7) * 7 }, (_, index) => {
    const day = index - offset + 1
    return day >= 1 && day <= total ? `${month}-${String(day).padStart(2, '0')}` : null
  })
}

export function eventsByDay(events: CalendarEvent[], month: string) {
  const output = new Map<string, CalendarEvent[]>()
  const first = `${month}-01`
  const after = `${nextMonth(month)}-01`
  for (const event of events) {
    if (event.status === 'cancelled') continue
    const start = startDay(event)
    const end = exclusiveEndDay(event)
    if (!start || !end) continue
    for (let day = start < first ? first : start, count = 0; day < end && day < after && count < 31; day = nextDay(day), count += 1) {
      output.set(day, [...(output.get(day) || []), event])
    }
  }
  return output
}

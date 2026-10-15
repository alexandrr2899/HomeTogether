import assert from 'node:assert/strict'
import test from 'node:test'

import { eventsByDay, monthCells } from '../src/calendarDates.ts'

test('the month starts on Monday and keeps all 31 days visible', () => {
  const cells = monthCells('2026-10')
  assert.equal(cells.length, 35)
  assert.equal(cells[3], '2026-10-01')
  assert.equal(cells[33], '2026-10-31')
})

test('all-day spans use the exclusive Google end date and cross months', () => {
  const days = eventsByDay([{
    id: 'external-1', start: { date: '2026-09-30' }, end: { date: '2026-10-03' },
  }], '2026-10')
  assert.deepEqual([...days.keys()], ['2026-10-01', '2026-10-02'])
})

test('timed events use Tegucigalpa days and do not fill a midnight end day', () => {
  const days = eventsByDay([{
    id: 'external-2', start: { dateTime: '2026-10-10T23:30:00-06:00' },
    end: { dateTime: '2026-10-11T00:00:00-06:00' },
  }], '2026-10')
  assert.deepEqual([...days.keys()], ['2026-10-10'])
})

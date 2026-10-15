import { useEffect, useState, type FormEvent } from 'react'
import { api, type MenuEntry, type Recipe, type ShoppingPreview } from './api'

function dayInHonduras() {
  const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Tegucigalpa', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date())
  const get = (type: string) => parts.find((part) => part.type === type)?.value || ''
  return `${get('year')}-${get('month')}-${get('day')}`
}
function shift(date: string, days: number) {
  const value = new Date(`${date}T12:00:00Z`)
  value.setUTCDate(value.getUTCDate() + days)
  return value.toISOString().slice(0, 10)
}
function weekStart() {
  const today = dayInHonduras()
  const weekday = new Date(`${today}T12:00:00Z`).getUTCDay()
  return shift(today, -(weekday + 6) % 7)
}
const meals = { desayuno: 'Desayuno', almuerzo: 'Almuerzo', cena: 'Cena', otro: 'Otro' }

export function MenuView({ isAdmin, onListsChanged }: { isAdmin: boolean; onListsChanged: () => Promise<void> }) {
  const [start, setStart] = useState(weekStart)
  const end = shift(start, 6)
  const [entries, setEntries] = useState<MenuEntry[] | null>(null)
  const [recipes, setRecipes] = useState<Recipe[] | null>(null)
  const [preview, setPreview] = useState<ShoppingPreview | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [operationIds, setOperationIds] = useState<Record<string, string>>({})
  const [date, setDate] = useState(dayInHonduras)
  const menuDate = date >= start && date <= end ? date : start
  const [meal, setMeal] = useState<MenuEntry['meal']>('almuerzo')
  const [recipeId, setRecipeId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function refresh() {
    const result = await Promise.allSettled([api.menu(start, end), api.recipes()])
    setEntries(result[0].status === 'fulfilled' ? result[0].value : null)
    setRecipes(result[1].status === 'fulfilled' ? result[1].value : null)
    if (result.some((item) => item.status === 'rejected')) setError('No se pudo cargar el menú o las recetas.')
  }
  useEffect(() => { void refresh(); setPreview(null); setSelected([]) }, [start])

  async function add(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try { await api.createMenuEntry({ date: menuDate, meal, recipe: Number(recipeId), notes: '' }); await refresh(); setPreview(null); setNotice('Comida añadida al menú.') }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo guardar.') }
    finally { setBusy(false) }
  }
  async function remove(entry: MenuEntry) {
    if (!window.confirm(`¿Quitar «${entry.recipe_title}» del menú?`)) return
    setBusy(true); setError('')
    try { await api.deleteMenuEntry(entry.id); await refresh(); setPreview(null); setNotice('Comida retirada del menú.') }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo quitar.') }
    finally { setBusy(false) }
  }
  async function review() {
    setBusy(true); setError(''); setNotice('')
    try { const result = await api.shoppingPreview(start, end); setPreview(result); setSelected(result.items.filter((item) => !item.already_on_list).map((item) => item.summary)) }
    catch (problem) { setPreview(null); setError(problem instanceof Error ? problem.message : 'No se pudo consultar Compras.') }
    finally { setBusy(false) }
  }
  async function addToShopping() {
    if (!preview || preview.shopping_status !== 'Conectado' || !selected.length) return
    if (!window.confirm(`¿Añadir ${selected.length} ${selected.length === 1 ? 'ingrediente' : 'ingredientes'} a la lista real Compras?`)) return
    setBusy(true); setError(''); setNotice('')
    const failures: string[] = []
    const succeeded: string[] = []
    const nextIds = { ...operationIds }
    for (const summary of selected) {
      const operationId = nextIds[summary] || crypto.randomUUID()
      nextIds[summary] = operationId
      try { await api.createListItem('compras', operationId, summary); succeeded.push(summary); delete nextIds[summary] }
      catch { failures.push(summary) }
    }
    setOperationIds(nextIds)
    if (succeeded.length) setNotice(`${succeeded.length} ${succeeded.length === 1 ? 'ingrediente confirmado' : 'ingredientes confirmados'} en Compras.`)
    if (failures.length) setError(`No se confirmó: ${failures.join(', ')}. Revisa Compras antes de reintentar.`)
    try {
      const result = await api.shoppingPreview(start, end)
      setPreview(result)
      setSelected(failures.filter((summary) => !result.items.find((item) => item.summary === summary)?.already_on_list))
      await onListsChanged()
    } catch { setError('No se pudo releer Compras. Revisa la lista antes de reintentar.') }
    finally { setBusy(false) }
  }

  return <>
    <header className="page-header"><p className="eyebrow">Plan de comidas</p><h1>Menú semanal</h1></header>
    <div className="week-controls"><button className="plain-button" onClick={() => setStart(shift(start, -7))}>← Anterior</button><strong>{start} al {end}</strong><button className="plain-button" onClick={() => setStart(shift(start, 7))}>Siguiente →</button></div>
    {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="success-message" role="status">{notice}</p>}
    {entries === null ? <div className="empty-state"><strong>Sin conexión</strong></div> : entries.length ? <ul className="family-detail-list">{entries.map((entry) => <li key={entry.id}><span><strong>{entry.recipe_title}</strong><small>{entry.date} · {meals[entry.meal]}</small></span>{isAdmin && <button disabled={busy} onClick={() => void remove(entry)}>Quitar</button>}</li>)}</ul> : <div className="empty-state"><strong>Sin datos</strong><p>No hay comidas planificadas esta semana.</p></div>}
    {isAdmin && <section className="section-block"><h2>Añadir al menú</h2>{recipes?.length ? <form className="event-form family-inline-form" onSubmit={(event) => void add(event)}>
      <label>Fecha<input type="date" min={start} max={end} required value={menuDate} onChange={(event) => setDate(event.target.value)} /></label>
      <label>Comida<select value={meal} onChange={(event) => setMeal(event.target.value as MenuEntry['meal'])}>{Object.entries(meals).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label>Receta<select required value={recipeId} onChange={(event) => setRecipeId(event.target.value)}><option value="">Selecciona una receta</option>{recipes.map((recipe) => <option key={recipe.id} value={recipe.id}>{recipe.title}</option>)}</select></label>
      <button className="primary-button" disabled={busy || !recipeId}>Añadir comida</button>
    </form> : <p className="muted section-empty">{recipes === null ? 'Sin conexión' : 'Crea primero una receta en Organizar → Recetas.'}</p>}</section>}
    <section className="section-block"><h2>Ingredientes para Compras</h2><p className="muted intro">Revisa los ingredientes antes de enviarlos a la lista real. Guardar el menú no añade compras.</p>
      {isAdmin && <button className="secondary-button family-add-button" disabled={busy || !entries?.length} onClick={() => void review()}>Revisar ingredientes</button>}
      {preview && <><p className="source-line">Compras: {preview.shopping_status}</p>{preview.items.length ? <ul className="shopping-preview">{preview.items.map((item) => <li key={item.summary}><label><input type="checkbox" disabled={busy || item.already_on_list || preview.shopping_status !== 'Conectado'} checked={selected.includes(item.summary) && !item.already_on_list} onChange={(event) => setSelected(event.target.checked ? [...selected, item.summary] : selected.filter((value) => value !== item.summary))} /><span>{item.summary}</span></label><small>{item.already_on_list ? 'Ya está en Compras' : item.occurrences > 1 ? `${item.occurrences} comidas` : ''}</small></li>)}</ul> : <div className="empty-state"><strong>Sin datos</strong><p>Las recetas del menú no tienen ingredientes.</p></div>}
        {isAdmin && <button className="primary-button" disabled={busy || !selected.length || preview.shopping_status !== 'Conectado'} onClick={() => void addToShopping()}>{busy ? 'Comprobando…' : `Añadir ${selected.length} a Compras`}</button>}</>}
    </section>
  </>
}

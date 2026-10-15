import { useEffect, useState, type FormEvent } from 'react'
import { api, type Ingredient, type Recipe } from './api'

const blankIngredient = (): Ingredient => ({ name: '', amount: '', position: 0 })
const blankRecipe = () => ({ title: '', instructions: '', servings: 2, ingredients: [blankIngredient()] })

export function RecipesView({ isAdmin }: { isAdmin: boolean }) {
  const [recipes, setRecipes] = useState<Recipe[] | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(blankRecipe)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const selected = recipes?.find((recipe) => recipe.id === selectedId)

  async function refresh() {
    try { setRecipes(await api.recipes()) } catch { setRecipes(null); setError('No se pudieron cargar las recetas.') }
  }
  useEffect(() => { void refresh() }, [])

  function open(recipe?: Recipe) {
    setSelectedId(recipe?.id ?? null)
    setDraft(recipe ? { title: recipe.title, instructions: recipe.instructions, servings: recipe.servings, ingredients: recipe.ingredients.map((item) => ({ ...item })) } : blankRecipe())
    setEditing(true); setError(''); setNotice('')
  }

  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try {
      const data = { ...draft, title: draft.title.trim(), ingredients: draft.ingredients.filter((item) => item.name.trim()).map((item, index) => ({ name: item.name.trim(), amount: item.amount.trim(), position: index })) }
      const saved = selectedId ? await api.updateRecipe(selectedId, data) : await api.createRecipe(data)
      await refresh(); setSelectedId(saved.id); setEditing(false); setNotice('Receta guardada.')
    } catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo guardar la receta.') } finally { setBusy(false) }
  }

  async function remove(recipe: Recipe) {
    if (!window.confirm(`¿Eliminar «${recipe.title}»?`)) return
    setBusy(true); setError('')
    try { await api.deleteRecipe(recipe.id); await refresh(); setSelectedId(null); setEditing(false); setNotice('Receta eliminada.') }
    catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo eliminar.') }
    finally { setBusy(false) }
  }

  return <>
    {selected || editing ? <button className="back-button" onClick={() => { setSelectedId(null); setEditing(false); setError(''); setNotice('') }}>← Volver a recetas</button> : null}
    <header className="page-header"><p className="eyebrow">Para compartir en casa</p><h1>{selected ? selected.title : 'Recetas'}</h1></header>
    {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="success-message" role="status">{notice}</p>}
    {editing ? <form className="event-form" onSubmit={(event) => void save(event)}>
      <h2>{selectedId ? 'Editar receta' : 'Nueva receta'}</h2>
      <label>Nombre<input required maxLength={180} value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
      <label>Porciones<input required type="number" min={1} max={999} value={draft.servings} onChange={(event) => setDraft({ ...draft, servings: Number(event.target.value) })} /></label>
      <h2>Ingredientes</h2>
      {draft.ingredients.map((item, index) => <div className="ingredient-inputs" key={index}>
        <label>Ingrediente {index + 1}<input maxLength={160} value={item.name} onChange={(event) => setDraft({ ...draft, ingredients: draft.ingredients.map((value, at) => at === index ? { ...value, name: event.target.value } : value) })} /></label>
        <label>Cantidad<input maxLength={80} value={item.amount} onChange={(event) => setDraft({ ...draft, ingredients: draft.ingredients.map((value, at) => at === index ? { ...value, amount: event.target.value } : value) })} /></label>
      </div>)}
      <button type="button" className="plain-button" onClick={() => setDraft({ ...draft, ingredients: [...draft.ingredients, blankIngredient()] })}>+ Otro ingrediente</button>
      <label>Preparación<textarea value={draft.instructions} onChange={(event) => setDraft({ ...draft, instructions: event.target.value })} /></label>
      <button className="primary-button" disabled={busy || !draft.title.trim()}>{busy ? 'Guardando…' : 'Guardar receta'}</button>
    </form> : selected ? <>
      <p className="muted">{selected.servings} porciones</p>
      <section className="section-block"><h2>Ingredientes</h2>{selected.ingredients.length ? <ul className="family-detail-list">{selected.ingredients.map((item) => <li key={item.id}><span><strong>{item.amount && `${item.amount} `}{item.name}</strong></span></li>)}</ul> : <p className="muted section-empty">Sin datos</p>}</section>
      <section className="section-block"><h2>Preparación</h2><p className="multiline-text">{selected.instructions || 'Sin datos'}</p></section>
      {isAdmin && <div className="detail-actions"><button className="secondary-button" onClick={() => open(selected)}>Editar receta</button><button className="danger-button" disabled={busy} onClick={() => void remove(selected)}>Eliminar receta</button></div>}
    </> : <>
      {isAdmin && <button className="secondary-button family-add-button" onClick={() => open()}>Añadir receta</button>}
      {recipes === null ? <div className="empty-state"><strong>Sin conexión</strong></div> : recipes.length ? <div className="family-list">{recipes.map((recipe) => <button className="family-row" key={recipe.id} onClick={() => { setSelectedId(recipe.id); setEditing(false) }}><span className="family-avatar">{recipe.title.charAt(0).toUpperCase()}</span><span><strong>{recipe.title}</strong><small>{recipe.ingredients.length} ingredientes · {recipe.servings} porciones</small></span><span aria-hidden="true">→</span></button>)}</div> : <div className="empty-state"><strong>Sin datos</strong><p>Aún no hay recetas.</p></div>}
    </>}
  </>
}

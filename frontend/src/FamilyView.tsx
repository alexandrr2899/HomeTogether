import { useState, type FormEvent } from 'react'
import { api, type FamilyProfile } from './api'
import { FamilyProfileDetail } from './FamilyProfileDetail'

function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'No se pudo guardar.'
}

export function FamilyView({ profiles, isAdmin, onChanged, onExit }: {
  profiles: FamilyProfile[] | null
  isAdmin: boolean
  onChanged: () => Promise<void>
  onExit: () => void
}) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [relationship, setRelationship] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const selected = profiles?.find((profile) => profile.id === selectedId)

  async function create(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const profile = await api.createFamilyProfile({ name: name.trim(), relationship: relationship.trim() })
      await onChanged()
      setName('')
      setRelationship('')
      setAdding(false)
      setSelectedId(profile.id)
    } catch (problem) {
      setError(errorText(problem))
    } finally { setBusy(false) }
  }

  if (selected) return <FamilyProfileDetail profile={selected} isAdmin={isAdmin} onChanged={onChanged} onBack={() => setSelectedId(null)} />
  return <>
    <button className="back-button" onClick={onExit}>← Configuración</button>
    <header className="page-header"><p className="eyebrow">Nuestro círculo</p><h1>Familia</h1></header>
    <p className="muted intro">Los perfiles familiares se crean aquí. No necesitan cuenta para entrar.</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    {isAdmin && <button className="secondary-button family-add-button" onClick={() => setAdding(!adding)}>{adding ? 'Cerrar formulario' : 'Añadir familiar'}</button>}
    {adding && <form className="event-form" onSubmit={(event) => void create(event)}><h2>Nuevo perfil</h2><label>Nombre<input required maxLength={160} value={name} onChange={(event) => setName(event.target.value)} /></label><label>Relación familiar<input maxLength={160} value={relationship} onChange={(event) => setRelationship(event.target.value)} placeholder="Por ejemplo, papá de Alexander" /></label><button className="primary-button" disabled={busy || !name.trim()}>{busy ? 'Guardando…' : 'Crear perfil'}</button></form>}
    {profiles === null ? <div className="empty-state"><strong>Sin conexión</strong><p>No se pudieron consultar los perfiles.</p></div> : profiles.length === 0 ? <div className="empty-state"><strong>Sin datos</strong><p>Aún no hay perfiles familiares.</p></div> : <div className="family-list">{profiles.map((profile) => <button key={profile.id} className="family-row" onClick={() => setSelectedId(profile.id)}><span className="family-avatar">{profile.name.charAt(0).toUpperCase()}</span><span><strong>{profile.name}</strong><small>{profile.relationship || 'Relación sin datos'}</small></span><span aria-hidden="true">→</span></button>)}</div>}
  </>
}

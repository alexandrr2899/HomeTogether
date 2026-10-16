import { useEffect, useState } from 'react'
import { api, type GarminCatalog, type WellnessPreferences } from './api'

export function WellnessSettings({ onChanged }: { onChanged: () => Promise<void> }) {
  const [saved, setSaved] = useState<WellnessPreferences | null>(null)
  const [draft, setDraft] = useState<WellnessPreferences | null>(null)
  const [catalog, setCatalog] = useState<GarminCatalog | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    void Promise.all([api.wellnessPreferences(), api.wellnessCatalog()])
      .then(([preferences, available]) => {
        setSaved(preferences)
        setDraft(preferences)
        setCatalog(available)
      })
      .catch(() => setError('No se pudieron cargar los indicadores de Garmin.'))
  }, [])

  function toggleVisible(key: string) {
    setSuccess('')
    setDraft((current) => {
      if (!current) return current
      const selected = current.visible_metrics.includes(key)
      return {
        ...current,
        visible_metrics: selected ? current.visible_metrics.filter((item) => item !== key) : [...current.visible_metrics, key],
        shared_metrics: selected ? current.shared_metrics.filter((item) => item !== key) : current.shared_metrics,
      }
    })
  }

  function toggleShared(key: string) {
    setSuccess('')
    setDraft((current) => current && ({
      ...current,
      shared_metrics: current.shared_metrics.includes(key)
        ? current.shared_metrics.filter((item) => item !== key)
        : [...current.shared_metrics, key],
    }))
  }

  async function save() {
    if (!draft) return
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      const result = await api.updateWellnessPreferences(draft)
      setSaved(result)
      setDraft(result)
      await onChanged()
      setSuccess('Preferencias guardadas.')
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'No se pudieron guardar las preferencias.')
    } finally {
      setBusy(false)
    }
  }

  const groups = [...new Set(catalog?.stats.map((stat) => stat.group) ?? [])]
  const changed = JSON.stringify(saved) !== JSON.stringify(draft)

  return <section className="section-block">
    <h2>Indicadores de Garmin</h2>
    <p className="muted intro">Elige qué aparece en Inicio. Los datos siguen siendo privados hasta que decidas compartirlos.</p>
    {error && <p className="form-error" role="alert">{error}</p>}
    {catalog?.status === 'Sin conexión' && <p className="muted">Sin conexión con Garmin. Tus preferencias guardadas se conservan.</p>}
    {catalog?.status === 'Sin configurar' && <p className="muted">Sin configurar</p>}
    {draft && catalog?.status === 'Conectado' && <>
      {groups.map((group) => <div className="garmin-group" key={group}>
        <h3>{group}</h3>
        <div className="privacy-options">{catalog.stats.filter((stat) => stat.group === group).map((stat) => <label key={stat.key}>
          <input type="checkbox" checked={draft.visible_metrics.includes(stat.key)} disabled={busy || (!stat.available && !draft.visible_metrics.includes(stat.key))} onChange={() => toggleVisible(stat.key)} />
          <span><strong>{stat.label}</strong><small>{stat.available ? 'Mostrar en Inicio' : 'Sin datos en Home Assistant'}</small></span>
        </label>)}</div>
      </div>)}
      <div className="garmin-sharing">
        <h3>Compartir con la familia</h3>
        <p className="muted intro">Solo Alexander y Lastenia pueden ver los indicadores que compartas. Si ocultas uno de Inicio, también dejará de compartirse.</p>
        {draft.visible_metrics.length ? <div className="privacy-options">{draft.visible_metrics.map((key) => {
          const stat = catalog.stats.find((item) => item.key === key)
          return stat && <label key={key}><input type="checkbox" checked={draft.shared_metrics.includes(key)} disabled={busy} onChange={() => toggleShared(key)} /><span><strong>{stat.label}</strong><small>Permitir que la otra cuenta lo consulte</small></span></label>
        })}</div> : <p className="muted">Sin indicadores seleccionados.</p>}
      </div>
      <div className="privacy-options garmin-jaime"><label><input type="checkbox" checked={draft.allow_jaime} disabled={busy} onChange={() => { setSuccess(''); setDraft({ ...draft, allow_jaime: !draft.allow_jaime }) }} /><span><strong>Compartir indicadores desde Home Together con Jaime</strong><small>Controla esta función de la app. El agente principal conserva sus herramientas generales de OpenClaw; este ajuste no las limita.</small></span></label></div>
      <button className="primary-button" disabled={busy || !changed} onClick={() => void save()}>{busy ? 'Guardando…' : 'Guardar preferencias'}</button>
      {success && <p className="success-message" role="status">{success}</p>}
    </>}
    {!draft && !error && <p className="muted">Cargando indicadores…</p>}
  </section>
}

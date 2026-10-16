import { useEffect, useState, type FormEvent } from 'react'
import { api, type JaimeProposal } from './api'

const actionName = { add_task: 'Añadir a To-do', add_shopping: 'Añadir a Compras', complete_task: 'Completar tarea' }

export function JaimeView({ isAdmin, onChanged }: { isAdmin: boolean; onChanged: () => Promise<void> }) {
  const [proposals, setProposals] = useState<JaimeProposal[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [chatStatus, setChatStatus] = useState('Cargando…')
  const [bridgeStatus, setBridgeStatus] = useState('Sin configurar')
  const [conversationId] = useState(() => crypto.randomUUID())
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([])
  async function refresh() {
    try { setProposals(await api.jaimeProposals()) } catch { setProposals(null); setError('No se pudieron consultar las propuestas.') }
  }
  useEffect(() => {
    if (!isAdmin) return
    void refresh()
    void api.jaimeStatus().then((result) => { setChatStatus(result.status); setBridgeStatus(result.bridge_status) }).catch(() => setChatStatus('Sin conexión'))
  }, [isAdmin])

  async function send(event: FormEvent) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || sending) return
    setSending(true); setError(''); setDraft('')
    setMessages((current) => [...current, { role: 'user', content }])
    try {
      const result = await api.jaimeChat(conversationId, content)
      setMessages((current) => [...current, { role: 'assistant', content: result.message }])
      if (result.proposal_ids.length) await refresh()
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'No se pudo consultar a Jaime.')
      await refresh()
    } finally { setSending(false) }
  }
  async function act(proposal: JaimeProposal, action: 'confirm' | 'discard') {
    if (action === 'confirm' && !window.confirm(`¿${actionName[proposal.kind]}: «${proposal.payload.summary || proposal.payload.uid}»?`)) return
    setBusy(true); setError(''); setNotice('')
    try {
      if (action === 'confirm') { await api.confirmJaimeProposal(proposal.id); await onChanged(); setNotice('Acción confirmada en Home Assistant.') }
      else { await api.discardJaimeProposal(proposal.id); setNotice('Propuesta descartada.') }
      await refresh()
    } catch (problem) { setError(problem instanceof Error ? problem.message : 'No se pudo confirmar.'); await refresh() }
    finally { setBusy(false) }
  }
  const pending = proposals?.filter((item) => item.state === 'pending') || []
  const recent = proposals?.filter((item) => item.state !== 'pending') || []
  return <>
    <header className="page-header"><p className="eyebrow">Asistente familiar</p><h1>Jaime</h1></header>
    {chatStatus === 'Conectado' ? <section className="jaime-chat" aria-label="Conversación con Jaime">
      <div className="jaime-messages" aria-live="polite">{messages.length ? messages.map((item, index) => <p className={`jaime-message ${item.role}`} key={index}>{item.content}</p>) : <div className="empty-state"><strong>Hola, soy Jaime</strong><p>{bridgeStatus === 'Configurado' ? 'El puente de consultas de Home Together está configurado. Puedo comprobar agenda, listas, presencia y bienestar autorizado.' : 'Estoy conectado a OpenClaw. Las consultas de Home Together están sin configurar.'}</p></div>}{sending && <p className="muted">Jaime está consultando…</p>}</div>
      <form className="jaime-composer" onSubmit={(event) => void send(event)}><label className="visually-hidden" htmlFor="jaime-message">Escribe a Jaime</label><input id="jaime-message" value={draft} maxLength={2000} onChange={(event) => setDraft(event.target.value)} placeholder="Escribe a Jaime" disabled={sending} /><button disabled={sending || !draft.trim()}>Enviar</button></form>
    </section> : <div className="empty-state"><strong>{chatStatus}</strong><p>{chatStatus === 'Sin configurar' ? 'La conversación necesita conectar OpenClaw en mewtwo. Las propuestas existentes se revisan aquí.' : 'No se pudo comprobar la conexión con OpenClaw.'}</p></div>}
    <p className="muted intro">Jaime comparte el agente principal de OpenClaw. Las propuestas de Home Together requieren tu confirmación aquí; sus otras herramientas conservan los permisos de OpenClaw. La voz se configurará después.</p>
    {error && <p className="form-error" role="alert">{error}</p>}{notice && <p className="success-message" role="status">{notice}</p>}
    {isAdmin && <section className="section-block"><h2>Propuestas pendientes</h2>{proposals === null ? <p className="muted section-empty">Sin conexión</p> : pending.length ? <ul className="family-detail-list">{pending.map((item) => <li key={item.id}><span><strong>{actionName[item.kind]}</strong><small>{item.payload.summary || `UID ${item.payload.uid}`}</small></span><div><button disabled={busy} onClick={() => void act(item, 'confirm')}>Confirmar</button><button disabled={busy} onClick={() => void act(item, 'discard')}>Descartar</button></div></li>)}</ul> : <p className="muted section-empty">Sin datos</p>}</section>}
    {isAdmin && !!recent.length && <section className="section-block"><h2>Actividad reciente</h2><ul className="family-detail-list">{recent.slice(0, 10).map((item) => <li key={item.id}><span><strong>{actionName[item.kind]}</strong><small>{item.state === 'confirmed' ? 'Confirmada' : 'Resultado incierto · revisar la lista'}{item.error && ` · ${item.error}`}</small></span></li>)}</ul></section>}
  </>
}

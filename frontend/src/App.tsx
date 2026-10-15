import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, type CalendarResponse, type ConnectionsResponse, type FamilyProfile, type ListsResponse, type Member, type MenuEntry, type PresenceResponse, type SharedWellness, type Trip, type WellnessMetric, type WellnessResponse } from './api'
import { CalendarView } from './CalendarView'
import { FamilyView } from './FamilyView'
import { OrganizeView } from './OrganizeView'
import { JaimeView } from './JaimeView'
import { WellnessSettings } from './WellnessSettings'

type Tab = 'inicio' | 'calendario' | 'organizar' | 'jaime' | 'configuracion'
type SettingsSection = 'general' | 'familia'
const tabs: { id: Tab; label: string }[] = [
  { id: 'inicio', label: 'Inicio' },
  { id: 'calendario', label: 'Calendario' },
  { id: 'organizar', label: 'Organizar' },
  { id: 'jaime', label: 'Jaime' },
]

function NavIcon({ tab }: { tab: Tab }) {
  const paths: Record<Exclude<Tab, 'configuracion'>, React.ReactNode> = {
    inicio: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" /><path d="M9 21v-7h6v7" /></>,
    calendario: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4M17 3v4M3 10h18" /><path d="M8 14h3v3H8z" /></>,
    organizar: <><path d="M10 6h11M10 12h11M10 18h11" /><path d="m3 6 1.5 1.5L7 5M3 12l1.5 1.5L7 11M3 18l1.5 1.5L7 17" /></>,
    jaime: <><path d="M5 5h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-9l-5 3v-3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z" /><path d="m12 8 .6 1.8L14.5 10l-1.9.6L12 12.5l-.6-1.9-1.9-.6 1.9-.2z" /></>,
  }
  if (tab === 'configuracion') return null
  return <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[tab]}</svg>
}

function displayTime(value?: string | null) {
  if (!value) return 'Sin datos'
  return new Intl.DateTimeFormat('es-HN', { timeZone: 'America/Tegucigalpa', dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function displayShortTime(value?: string | null) {
  if (!value) return 'Sin datos'
  return new Intl.DateTimeFormat('es-HN', { timeZone: 'America/Tegucigalpa', day: 'numeric', month: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

function sleepText(metric?: WellnessMetric) {
  if (!metric || metric.status !== 'Conectado') return metric?.status || 'Sin datos'
  const minutes = Number(metric.value)
  if (!Number.isFinite(minutes) || minutes < 0) return 'Sin datos'
  const rounded = Math.round(minutes)
  return `${Math.floor(rounded / 60)}:${String(rounded % 60).padStart(2, '0')}`
}

function metricText(metric: WellnessMetric) {
  if (metric.status !== 'Conectado' || metric.value === null) return metric.status
  if (metric.kind === 'duration') return sleepText(metric)
  if (metric.kind === 'text') return String(metric.value)
  const number = Number(metric.value)
  if (!Number.isFinite(number)) return 'Sin datos'
  const unit = metric.unit && !['steps', 'floors', 'level'].includes(metric.unit) ? ` ${metric.unit}` : ''
  return `${new Intl.NumberFormat('es-HN', { maximumFractionDigits: 1 }).format(number)}${unit}`
}

function eventTime(event: { start?: { date?: string; dateTime?: string } }) {
  if (event.start?.date) {
    const [year, month, day] = event.start.date.split('-')
    return `${day}/${month}/${year} · Todo el día`
  }
  if (!event.start?.dateTime) return 'Hora sin datos'
  return new Intl.DateTimeFormat('es-HN', { timeZone: 'America/Tegucigalpa', dateStyle: 'medium', timeStyle: 'short' }).format(new Date(event.start.dateTime))
}

function StatusMessage({ status, detail }: { status: string; detail?: string }) {
  return <div className="empty-state"><strong>{status}</strong>{detail && <p>{detail}</p>}</div>
}

function Login({ onSuccess }: { onSuccess: (member: Member) => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await api.csrf()
      await api.login(username.trim(), password)
      onSuccess(await api.me())
      setPassword('')
    } catch {
      setError('No se pudo iniciar sesión. Revisa tus datos o la conexión.')
    } finally {
      setBusy(false)
    }
  }

  return <main className="login-screen">
    <div className="login-card">
      <div className="brand-mark">H</div>
      <p className="eyebrow">Nuestro espacio privado</p>
      <h1>Home Together</h1>
      <p className="muted">Un lugar para organizar lo que compartimos.</p>
      <form onSubmit={submit}>
        <label>Usuario<input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
        <label>Contraseña<input autoComplete="current-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button>
      </form>
    </div>
  </main>
}

function Home({ member, lists, calendar, presence, profiles, menu, trips, wellness, sharedWellness, onNavigate, onOpenFamily }: { member: Member; lists: ListsResponse | null; calendar: CalendarResponse | null; presence: PresenceResponse | null; profiles: FamilyProfile[] | null; menu: MenuEntry[] | null; trips: Trip[] | null; wellness: WellnessResponse | null; sharedWellness: SharedWellness[] | null; onNavigate: (tab: Tab) => void; onOpenFamily: () => void }) {
  const firstName = member.first_name || member.username
  const pending = lists?.lists.flatMap((list) => list.items.filter((item) => item.status === 'needs_action').map((item) => ({ ...item, listName: list.name }))) ?? []
  const next = calendar?.events.find((event) => event.status !== 'cancelled')
  return <>
    <header className="home-header"><p className="eyebrow">Tu espacio compartido</p><h1>Hola, <span>{firstName}</span></h1></header>
    <div className="home-grid">
    <div className="home-column home-main">
    <section className="home-section"><div className="section-heading"><h2>Próximo compromiso</h2><button className="text-button" onClick={() => onNavigate('calendario')}>Ver calendario</button></div>
      {calendar?.status === 'Conectado' && next ? <article className="highlight-card"><p className="eyebrow">{eventTime(next)}</p><h3>{next.summary || 'Sin título'}</h3>{next.location && <p>{next.location}</p>}</article> :
        <StatusMessage status={calendar?.status === 'Conectado' ? 'Sin datos' : calendar?.status || 'Sin configurar'} detail={calendar?.status === 'Conectado' ? 'No hay próximos eventos en el intervalo consultado.' : 'Revisa la conexión con Google Calendar.'} />}
      <p className="updated">Google Calendar · Consultado: {displayTime(calendar?.last_checked_at)}</p>
    </section>
    <section className="home-section"><div className="section-heading"><h2>Tareas y compras</h2><button className="text-button" onClick={() => onNavigate('organizar')}>Ver listas</button></div>
      {lists?.status === 'Conectado' ? pending.length ? <ul className="compact-list">{pending.slice(0, 4).map((item) => <li key={`${item.listName}-${item.uid}`}><span>{item.summary}</span><small>{item.listName}</small></li>)}</ul> : <StatusMessage status="Sin datos" detail="No hay ítems pendientes." /> : <StatusMessage status={lists?.status || 'Sin conexión'} />}
      <p className="updated">Home Assistant · Consultado: {displayTime(lists?.last_checked_at)}</p>
    </section>
    {!!menu?.length && <section className="home-section"><div className="section-heading"><h2>Próximas comidas</h2><button className="text-button" onClick={() => onNavigate('organizar')}>Ver menú</button></div><ul className="compact-list">{menu.slice(0, 3).map((entry) => <li key={entry.id}><span>{entry.recipe_title}</span><small>{entry.date} · {entry.meal}</small></li>)}</ul></section>}
    {!!trips?.length && <section className="home-section"><div className="section-heading"><h2>Viajes</h2><button className="text-button" onClick={() => onNavigate('organizar')}>Ver viajes</button></div><ul className="compact-list">{trips.slice(0, 2).map((trip) => <li key={trip.id}><span>{trip.title}</span><small>{trip.start_date || 'Sin fecha'}</small></li>)}</ul></section>}
    </div>
    <div className="home-column home-side">
    <section className="home-section"><div className="section-heading"><h2>Presencia</h2></div>
      {presence?.people.length ? <div className="presence-list">{presence.people.map((person) => <div className="presence-row" key={person.account_id}><div className={`member-initial ${person.username === 'lastenia' ? 'lastenia' : 'alexander'}`}>{person.name.charAt(0).toUpperCase()}</div><div><strong>{person.name}</strong><small>Actualizado: {displayShortTime(person.last_updated)}</small></div><span className="presence-status">{person.state === 'work' ? 'Trabajo' : person.label}</span></div>)}</div> : <StatusMessage status={presence?.status || 'Sin configurar'} detail="No hay entidades de presencia asociadas." />}
      <p className="updated">Home Assistant · Consultado: {displayTime(presence?.last_checked_at)}</p>
    </section>
    {wellness && wellness.status !== 'Sin configurar' && <section className="home-section"><div className="section-heading"><h2>Mi bienestar</h2><button className="text-button" onClick={() => onNavigate('configuracion')}>Elegir indicadores</button></div>
      {Object.keys(wellness.metrics).length ? <div className="detail-card wellness-card">{Object.entries(wellness.metrics).map(([key, metric]) => <div className="detail-row" key={key}><span>{metric.label}</span><strong>{metricText(metric)}</strong></div>)}</div> : <StatusMessage status="Sin datos" detail="Elige tus indicadores en Configuración." />}
      <p className="updated">Garmin vía Home Assistant · Consultado: {displayTime(wellness.last_checked_at)}</p></section>}
    {!!profiles?.length && <section className="home-section"><div className="section-heading"><h2>Familia</h2><button className="text-button" onClick={onOpenFamily}>Ver perfiles</button></div><div className="family-summary"><strong>{profiles.length} {profiles.length === 1 ? 'perfil' : 'perfiles'}</strong><p>{profiles.reduce((count, profile) => count + profile.important_dates.length + (profile.birthday ? 1 : 0), 0)} fechas importantes registradas</p></div></section>}
    {!!sharedWellness?.length && <section className="home-section"><h2>Bienestar compartido</h2>{sharedWellness.map((person) => <div key={person.account_id} className="detail-card wellness-card"><h3>{person.name}</h3>{Object.entries(person.metrics).map(([key, metric]) => <div className="detail-row" key={key}><span>{metric.label}</span><strong>{metricText(metric)}</strong></div>)}</div>)}</section>}
    </div>
    </div>
  </>
}

function Settings({ section, onSectionChange, connections, wellness, profiles, isAdmin, onChanged, onLogout }: { section: SettingsSection; onSectionChange: (section: SettingsSection) => void; connections: ConnectionsResponse | null; wellness: WellnessResponse | null; profiles: FamilyProfile[] | null; isAdmin: boolean; onChanged: () => Promise<void>; onLogout: () => void }) {
  const homeAssistantUrl = connections?.connections.find((connection) => connection.service === 'home_assistant')?.web_url
  if (section === 'familia') return <FamilyView profiles={profiles} isAdmin={isAdmin} onChanged={onChanged} onExit={() => onSectionChange('general')} />
  return <><header className="page-header"><p className="eyebrow">Estado y acceso</p><h1>Configuración</h1></header>
    <section className="section-block"><h2>Familia</h2><p className="muted intro">Perfiles, fechas, responsabilidades y documentos privados.</p><button className="settings-family-button" onClick={() => onSectionChange('familia')}><span>Gestionar familia</span><span aria-hidden="true">→</span></button></section>
    <section className="section-block"><h2>Conexiones</h2>{connections?.connections.map((connection) => <div className="connection-row" key={connection.service}><div><strong>{{ home_assistant: 'Home Assistant', google_calendar: 'Google Calendar', openclaw: 'Jaime · OpenClaw' }[connection.service] || connection.service}</strong><small>Última comprobación: {displayTime(connection.last_sync)}</small></div><span className={`status-pill ${connection.status === 'Conectado' ? 'connected' : ''}`}>{connection.status}</span>{connection.error && <p className="connection-error">{connection.error}</p>}</div>) ?? <StatusMessage status="Sin datos" />}</section>
    {homeAssistantUrl && <section className="section-block"><h2>Panel del hogar</h2><p className="muted intro">Abre Home Assistant con su propia sesión para consultar y controlar la casa.</p><a className="home-assistant-link" href={homeAssistantUrl} target="_blank" rel="noopener noreferrer">Abrir Home Assistant ↗</a></section>}
    {wellness && wellness.status !== 'Sin configurar' && <WellnessSettings onChanged={onChanged} />}
    <button className="secondary-button" onClick={onLogout}>Cerrar sesión</button>
  </>
}

export default function App() {
  const [online, setOnline] = useState(navigator.onLine)
  const [member, setMember] = useState<Member | null | undefined>(undefined)
  const [tab, setTab] = useState<Tab>('inicio')
  const [settingsSection, setSettingsSection] = useState<SettingsSection>('general')
  const [lists, setLists] = useState<ListsResponse | null>(null)
  const [calendar, setCalendar] = useState<CalendarResponse | null>(null)
  const [connections, setConnections] = useState<ConnectionsResponse | null>(null)
  const [presence, setPresence] = useState<PresenceResponse | null>(null)
  const [profiles, setProfiles] = useState<FamilyProfile[] | null>(null)
  const [menu, setMenu] = useState<MenuEntry[] | null>(null)
  const [trips, setTrips] = useState<Trip[] | null>(null)
  const [wellness, setWellness] = useState<WellnessResponse | null>(null)
  const [sharedWellness, setSharedWellness] = useState<SharedWellness[] | null>(null)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const homeAssistantUrl = connections?.connections.find((connection) => connection.service === 'home_assistant')?.web_url

  const refresh = useCallback(async () => {
    setRefreshing(true)
    setError('')
    const now = new Date()
    const end = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
    const dateParts = new Intl.DateTimeFormat('en-US', { timeZone: 'America/Tegucigalpa', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now)
    const part = (type: string) => dateParts.find((entry) => entry.type === type)?.value || ''
    const today = `${part('year')}-${part('month')}-${part('day')}`
    const finalDay = new Date(`${today}T12:00:00Z`)
    finalDay.setUTCDate(finalDay.getUTCDate() + 6)
    const results = await Promise.allSettled([api.lists(), api.calendar(now.toISOString(), end.toISOString()), api.connections(), api.presence(), api.familyProfiles(), api.menu(today, finalDay.toISOString().slice(0, 10)), api.trips(), api.myWellness(), api.sharedWellness()])
    setLists(results[0].status === 'fulfilled' ? results[0].value : { status: 'Sin conexión', lists: [], last_checked_at: null })
    setCalendar(results[1].status === 'fulfilled' ? results[1].value : { status: 'Sin conexión', source: 'google_calendar', events: [], last_checked_at: null })
    setConnections(results[2].status === 'fulfilled' ? results[2].value : { connections: [] })
    setPresence(results[3].status === 'fulfilled' ? results[3].value : { status: 'Sin conexión', people: [], last_checked_at: null })
    setProfiles(results[4].status === 'fulfilled' ? results[4].value : null)
    setMenu(results[5].status === 'fulfilled' ? results[5].value : null)
    setTrips(results[6].status === 'fulfilled' ? results[6].value : null)
    setWellness(results[7].status === 'fulfilled' ? results[7].value : null)
    setSharedWellness(results[8].status === 'fulfilled' ? results[8].value : null)
    if (results.some((result) => result.status === 'rejected')) setError('No se pudieron actualizar todos los servicios. Revisa Configuración.')
    setRefreshing(false)
  }, [])

  useEffect(() => { api.me().then(setMember).catch(() => setMember(null)) }, [])
  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener('online', update); window.addEventListener('offline', update)
    return () => { window.removeEventListener('online', update); window.removeEventListener('offline', update) }
  }, [])
  useEffect(() => { if (member) void refresh() }, [member, refresh])
  useEffect(() => {
    if (!member) return
    const updateWhenVisible = () => { if (document.visibilityState === 'visible') void refresh() }
    const timer = window.setInterval(updateWhenVisible, 30_000)
    window.addEventListener('focus', updateWhenVisible)
    document.addEventListener('visibilitychange', updateWhenVisible)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', updateWhenVisible)
      document.removeEventListener('visibilitychange', updateWhenVisible)
    }
  }, [member, refresh])

  async function logout() {
    try { await api.logout() } finally { setMember(null); setLists(null); setCalendar(null); setConnections(null); setPresence(null); setProfiles(null); setMenu(null); setTrips(null); setWellness(null); setSharedWellness(null) }
  }

  if (member === undefined) return <main className="loading-screen">Cargando Home Together…</main>
  if (member === null) return online ? <Login onSuccess={setMember} /> : <main className="loading-screen"><div className="empty-state"><strong>Sin conexión</strong><p>Conéctate para abrir tu información privada. No se guardan cambios sin red.</p></div></main>

  return <div className="app-shell">
    <main className="content">
      <div className="top-actions"><span className="app-name">Home Together</span><div>{homeAssistantUrl && <a className="home-assistant-link top-home-link" href={homeAssistantUrl} target="_blank" rel="noopener noreferrer" aria-label="Abrir Home Assistant">Hogar ↗</a>}<button className="icon-button" aria-label="Actualizar" disabled={refreshing} onClick={() => void refresh()}>{refreshing ? '…' : '↻'}</button><button className="icon-button" aria-label="Configuración" onClick={() => { setSettingsSection('general'); setTab('configuracion') }}>⚙</button></div></div>
      {!online && <p className="banner-error" role="status">Sin conexión. Los cambios están desactivados; la información puede estar desactualizada.</p>}
      {error && <p className="banner-error" role="alert">{error}</p>}
      {tab === 'inicio' && <Home member={member} lists={lists} calendar={calendar} presence={presence} profiles={profiles} menu={menu} trips={trips} wellness={wellness} sharedWellness={sharedWellness} onNavigate={setTab} onOpenFamily={() => { setSettingsSection('familia'); setTab('configuracion') }} />}
      {tab === 'calendario' && <CalendarView calendar={calendar} isAdmin={member.is_admin} onChanged={refresh} />}
      {tab === 'organizar' && <OrganizeView lists={lists} isAdmin={member.is_admin} onChanged={refresh} />}
      {tab === 'jaime' && <JaimeView isAdmin={member.is_admin} onChanged={refresh} />}
      {tab === 'configuracion' && <Settings section={settingsSection} onSectionChange={setSettingsSection} connections={connections} wellness={wellness} profiles={profiles} isAdmin={member.is_admin} onChanged={refresh} onLogout={() => void logout()} />}
    </main>
    <nav className="bottom-nav" aria-label="Navegación principal">{tabs.map((item) => <button key={item.id} className={tab === item.id ? 'nav-item selected' : 'nav-item'} aria-current={tab === item.id ? 'page' : undefined} onClick={() => setTab(item.id)}><span className="nav-icon-wrap"><NavIcon tab={item.id} /></span><span>{item.label}</span></button>)}</nav>
  </div>
}

export type Member = { id: number; username: string; first_name: string; is_admin: boolean }
export type ListItem = { uid: string; summary: string; status: 'needs_action' | 'completed'; due?: string }
export type HouseholdList = {
  id: 'compras' | 'super' | 'tareas'
  name: string
  entity_id: string | null
  origin: string
  status: string
  items: ListItem[]
}
export type ListsResponse = { status: string; lists: HouseholdList[]; last_checked_at: string | null }
export type CalendarEvent = {
  id: string
  etag?: string
  summary?: string
  start?: { date?: string; dateTime?: string }
  end?: { date?: string; dateTime?: string }
  location?: string
  status?: string
  recurringEventId?: string
}
export type CalendarResponse = {
  status: string
  source: string
  events: CalendarEvent[]
  time_zone?: string
  last_checked_at: string | null
  error?: string
  next_page_token?: string | null
}
export type Connection = { service: string; status: string; last_sync: string | null; error?: string | null; web_url?: string | null }
export type ConnectionsResponse = { connections: Connection[] }
export type PresencePerson = { account_id: number; username: string; name: string; state: string | null; label: string; last_updated: string | null }
export type PresenceResponse = { status: string; people: PresencePerson[]; last_checked_at: string | null }
export type FamilyDate = { id: number; label: string; date: string; repeats_annually: boolean }
export type FamilyResponsibility = { id: number; title: string; notes: string; due_date: string | null; external_source: string; external_id: string }
export type FamilyReferenceStatus = { status: string; title?: string; kind?: string; item_status?: string; start?: { date?: string; dateTime?: string } }
export type FamilyDocument = { id: number; original_name: string; size: number; uploaded_at: string }
export type FamilyProfile = {
  id: number; name: string; relationship: string; phone: string; email: string; birthday: string | null; notes: string
  important_dates: FamilyDate[]; responsibilities: FamilyResponsibility[]; documents: FamilyDocument[]
  created_at: string; updated_at: string
}
export type Ingredient = { id?: number; name: string; amount: string; position: number }
export type Recipe = { id: number; title: string; instructions: string; servings: number; ingredients: Ingredient[]; created_at: string; updated_at: string }
export type MenuEntry = { id: number; date: string; meal: 'desayuno' | 'almuerzo' | 'cena' | 'otro'; recipe: number; recipe_title: string; notes: string }
export type ShoppingCandidate = { summary: string; occurrences: number; already_on_list: boolean }
export type ShoppingPreview = { status: string; shopping_status: string; items: ShoppingCandidate[]; last_checked_at: string }
export type TripParticipant = { id: number; profile: number | null; name: string }
export type TripPreparation = { id: number; title: string; done: boolean }
export type TripDocument = { id: number; original_name: string; size: number; uploaded_at: string }
export type Trip = { id: number; title: string; destination: string; start_date: string | null; end_date: string | null; notes: string; participants: TripParticipant[]; preparations: TripPreparation[]; documents: TripDocument[] }
export type JaimeProposal = { id: string; kind: 'add_task' | 'add_shopping' | 'complete_task'; payload: { summary?: string; uid?: string }; state: 'pending' | 'confirmed' | 'uncertain'; result: { source?: string; list_id?: string; uid?: string; summary?: string; status?: string }; error: string; created_at: string; confirmed_at: string | null }
export type JaimeChatResponse = { status: string; message: string; proposal_ids: string[] }
export type WellnessMetric = { label: string; kind: 'number' | 'duration' | 'text'; status: string; value: number | string | null; unit: string | null; last_updated: string | null; started_at?: string | null }
export type WellnessResponse = { status: string; account_id: number; metrics: Record<string, WellnessMetric>; last_checked_at: string | null }
export type SharedWellness = WellnessResponse & { name: string }
export type WellnessPreferences = { visible_metrics: string[]; shared_metrics: string[]; allow_jaime: boolean; jaime_viewers: number[]; available_jaime_viewers: { id: number; name: string }[] }
export type GarminStat = { key: string; label: string; group: string; kind: WellnessMetric['kind']; available: boolean }
export type GarminCatalog = { status: string; stats: GarminStat[] }

function csrfToken(): string {
  return decodeURIComponent(document.cookie.split('; ').find((part) => part.startsWith('csrftoken='))?.split('=')[1] ?? '')
}

function jsonMutation<T>(path: string, method: 'POST' | 'PATCH', data: object): Promise<T> {
  return request<T>(path, { method, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(data) })
}

function deleteResource(path: string): Promise<void> {
  return request<void>(path, { method: 'DELETE', headers: { 'X-CSRFToken': csrfToken() } })
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (init?.method && init.method !== 'GET' && !navigator.onLine) throw new Error('Sin conexión. Los cambios están desactivados hasta recuperar la red.')
  const response = await fetch(path, { credentials: 'same-origin', ...init })
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null
    const error = new Error(body?.detail || `HTTP ${response.status}`) as Error & { status: number }
    error.status = response.status
    throw error
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  csrf: () => request<{ status: string }>('/api/v1/accounts/csrf/'),
  me: () => request<Member>('/api/v1/accounts/me/'),
  login: (username: string, password: string) => request<Member>('/api/v1/accounts/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
    body: JSON.stringify({ username, password }),
  }),
  logout: () => request<{ status: string }>('/api/v1/accounts/logout/', {
    method: 'POST', headers: { 'X-CSRFToken': csrfToken() },
  }),
  lists: () => request<ListsResponse>('/api/v1/lists/'),
  createListItem: (listId: HouseholdList['id'], operationId: string, summary: string) => request<{ item: ListItem }>(
    `/api/v1/lists/${listId}/items/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify({ operation_id: operationId, summary }),
    },
  ),
  updateListItem: (listId: HouseholdList['id'], uid: string, changes: { summary?: string; status?: ListItem['status'] }) => request<{ item: ListItem }>(
    `/api/v1/lists/${listId}/items/${encodeURIComponent(uid)}/`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify(changes),
    },
  ),
  deleteListItem: async (listId: HouseholdList['id'], uid: string) => {
    if (!navigator.onLine) throw new Error('Sin conexión. Los cambios están desactivados.')
    const response = await fetch(`/api/v1/lists/${listId}/items/${encodeURIComponent(uid)}/`, {
      method: 'DELETE', credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new Error(body?.detail || `HTTP ${response.status}`)
    }
  },
  calendar: (start: string, end: string, pageToken?: string) => request<CalendarResponse>(
    `/api/v1/calendar/events/?${new URLSearchParams({ start, end, ...(pageToken ? { page_token: pageToken } : {}) })}`,
  ),
  createCalendarEvent: (event: { operation_id: string; summary: string; start: object; end: object }) => request<{ event: CalendarEvent }>(
    '/api/v1/calendar/events/', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify(event),
    },
  ),
  updateCalendarEvent: (id: string, etag: string, changes: { summary: string }) => request<{ event: CalendarEvent }>(
    `/api/v1/calendar/events/${encodeURIComponent(id)}/`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(), 'If-Match': etag },
      body: JSON.stringify(changes),
    },
  ),
  deleteCalendarEvent: async (id: string, etag: string) => {
    if (!navigator.onLine) throw new Error('Sin conexión. Los cambios están desactivados.')
    const response = await fetch(`/api/v1/calendar/events/${encodeURIComponent(id)}/`, {
      method: 'DELETE', credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken(), 'If-Match': etag },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null) as { detail?: string } | null
      throw new Error(body?.detail || `HTTP ${response.status}`)
    }
  },
  connections: () => request<ConnectionsResponse>('/api/v1/integrations/connections/'),
  presence: () => request<PresenceResponse>('/api/v1/home/presence/'),
  myWellness: () => request<WellnessResponse>('/api/v1/home/wellness/me/'),
  wellnessCatalog: () => request<GarminCatalog>('/api/v1/home/wellness/catalog/'),
  sharedWellness: () => request<SharedWellness[]>('/api/v1/home/wellness/shared/'),
  wellnessPreferences: () => request<WellnessPreferences>('/api/v1/home/wellness/preferences/'),
  updateWellnessPreferences: (changes: Partial<WellnessPreferences>) => jsonMutation<WellnessPreferences>('/api/v1/home/wellness/preferences/', 'PATCH', changes),
  familyProfiles: () => request<FamilyProfile[]>('/api/v1/family/profiles/'),
  createFamilyProfile: (data: { name: string; relationship: string }) => request<FamilyProfile>('/api/v1/family/profiles/', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(data),
  }),
  updateFamilyProfile: (id: number, data: Partial<Pick<FamilyProfile, 'name' | 'relationship' | 'phone' | 'email' | 'birthday' | 'notes'>>) => request<FamilyProfile>(`/api/v1/family/profiles/${id}/`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(data),
  }),
  deleteFamilyProfile: (id: number) => request<void>(`/api/v1/family/profiles/${id}/`, {
    method: 'DELETE', headers: { 'X-CSRFToken': csrfToken() },
  }),
  createFamilyDate: (profileId: number, data: { label: string; date: string; repeats_annually: boolean }) => request<FamilyDate>(`/api/v1/family/profiles/${profileId}/dates/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(data),
  }),
  deleteFamilyDate: (profileId: number, dateId: number) => request<void>(`/api/v1/family/profiles/${profileId}/dates/${dateId}/`, {
    method: 'DELETE', headers: { 'X-CSRFToken': csrfToken() },
  }),
  createResponsibility: (profileId: number, data: { title: string; due_date?: string | null; external_source?: string; external_id?: string }) => request<FamilyResponsibility>(`/api/v1/family/profiles/${profileId}/responsibilities/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(data),
  }),
  responsibilitySource: (profileId: number, responsibilityId: number) => request<FamilyReferenceStatus>(`/api/v1/family/profiles/${profileId}/responsibilities/${responsibilityId}/source/`),
  deleteResponsibility: (profileId: number, responsibilityId: number) => request<void>(`/api/v1/family/profiles/${profileId}/responsibilities/${responsibilityId}/`, {
    method: 'DELETE', headers: { 'X-CSRFToken': csrfToken() },
  }),
  uploadFamilyDocument: (profileId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<FamilyDocument>(`/api/v1/family/profiles/${profileId}/documents/`, {
      method: 'POST', headers: { 'X-CSRFToken': csrfToken() }, body: form,
    })
  },
  downloadFamilyDocument: async (profileId: number, documentId: number) => {
    const response = await fetch(`/api/v1/family/profiles/${profileId}/documents/${documentId}/`, { credentials: 'same-origin' })
    if (!response.ok) throw new Error(`No se pudo descargar el documento (HTTP ${response.status})`)
    return response.blob()
  },
  deleteFamilyDocument: (profileId: number, documentId: number) => request<void>(`/api/v1/family/profiles/${profileId}/documents/${documentId}/`, {
    method: 'DELETE', headers: { 'X-CSRFToken': csrfToken() },
  }),
  recipes: () => request<Recipe[]>('/api/v1/planning/recipes/'),
  createRecipe: (data: Pick<Recipe, 'title' | 'instructions' | 'servings' | 'ingredients'>) => jsonMutation<Recipe>('/api/v1/planning/recipes/', 'POST', data),
  updateRecipe: (id: number, data: Pick<Recipe, 'title' | 'instructions' | 'servings' | 'ingredients'>) => jsonMutation<Recipe>(`/api/v1/planning/recipes/${id}/`, 'PATCH', data),
  deleteRecipe: (id: number) => deleteResource(`/api/v1/planning/recipes/${id}/`),
  menu: (start: string, end: string) => request<MenuEntry[]>(`/api/v1/planning/menu/?${new URLSearchParams({ start, end })}`),
  createMenuEntry: (data: Pick<MenuEntry, 'date' | 'meal' | 'recipe' | 'notes'>) => jsonMutation<MenuEntry>('/api/v1/planning/menu/', 'POST', data),
  deleteMenuEntry: (id: number) => deleteResource(`/api/v1/planning/menu/${id}/`),
  shoppingPreview: (start: string, end: string) => request<ShoppingPreview>(`/api/v1/planning/menu/shopping-preview/?${new URLSearchParams({ start, end })}`),
  trips: () => request<Trip[]>('/api/v1/planning/trips/'),
  createTrip: (data: Pick<Trip, 'title' | 'destination' | 'start_date' | 'end_date' | 'notes'>) => jsonMutation<Trip>('/api/v1/planning/trips/', 'POST', data),
  updateTrip: (id: number, data: Partial<Pick<Trip, 'title' | 'destination' | 'start_date' | 'end_date' | 'notes'>>) => jsonMutation<Trip>(`/api/v1/planning/trips/${id}/`, 'PATCH', data),
  deleteTrip: (id: number) => deleteResource(`/api/v1/planning/trips/${id}/`),
  addTripParticipant: (id: number, data: { name: string; profile?: number | null }) => jsonMutation<TripParticipant>(`/api/v1/planning/trips/${id}/participants/`, 'POST', data),
  deleteTripParticipant: (id: number, participantId: number) => deleteResource(`/api/v1/planning/trips/${id}/participants/${participantId}/`),
  addTripPreparation: (id: number, title: string) => jsonMutation<TripPreparation>(`/api/v1/planning/trips/${id}/preparations/`, 'POST', { title }),
  updateTripPreparation: (id: number, preparationId: number, done: boolean) => jsonMutation<TripPreparation>(`/api/v1/planning/trips/${id}/preparations/${preparationId}/`, 'PATCH', { done }),
  deleteTripPreparation: (id: number, preparationId: number) => deleteResource(`/api/v1/planning/trips/${id}/preparations/${preparationId}/`),
  uploadTripDocument: (id: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<TripDocument>(`/api/v1/planning/trips/${id}/documents/`, { method: 'POST', headers: { 'X-CSRFToken': csrfToken() }, body: form })
  },
  downloadTripDocument: async (id: number, documentId: number) => {
    const response = await fetch(`/api/v1/planning/trips/${id}/documents/${documentId}/`, { credentials: 'same-origin' })
    if (!response.ok) throw new Error(`No se pudo descargar el documento (HTTP ${response.status})`)
    return response.blob()
  },
  deleteTripDocument: (id: number, documentId: number) => deleteResource(`/api/v1/planning/trips/${id}/documents/${documentId}/`),
  jaimeProposals: () => request<JaimeProposal[]>('/api/v1/jaime/proposals/'),
  jaimeStatus: () => request<{ status: string }>('/api/v1/jaime/chat/'),
  jaimeChat: (conversationId: string, message: string) => jsonMutation<JaimeChatResponse>('/api/v1/jaime/chat/', 'POST', { conversation_id: conversationId, message }),
  confirmJaimeProposal: (id: string) => request<JaimeProposal>(`/api/v1/jaime/proposals/${encodeURIComponent(id)}/confirm/`, { method: 'POST', headers: { 'X-CSRFToken': csrfToken() } }),
  discardJaimeProposal: (id: string) => deleteResource(`/api/v1/jaime/proposals/${encodeURIComponent(id)}/`),
}

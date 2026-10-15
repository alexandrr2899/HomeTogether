import { useState } from 'react'
import { type ListsResponse } from './api'
import { ListsView } from './ListsView'
import { RecipesView } from './RecipesView'
import { MenuView } from './MenuView'
import { TripsView } from './TripsView'

type Section = 'listas' | 'recetas' | 'menu' | 'viajes'

export function OrganizeView({ lists, isAdmin, onChanged }: {
  lists: ListsResponse | null; isAdmin: boolean; onChanged: () => Promise<void>
}) {
  const [section, setSection] = useState<Section>('listas')
  return <>
    <div className="chips organize-tabs" role="tablist" aria-label="Secciones de Organizar">
      {([['listas', 'Listas'], ['recetas', 'Recetas'], ['menu', 'Menú'], ['viajes', 'Viajes']] as const).map(([id, label]) =>
        <button key={id} role="tab" aria-selected={section === id} className={section === id ? 'chip active' : 'chip'} onClick={() => setSection(id)}>{label}</button>,
      )}
    </div>
    {section === 'listas' && <ListsView lists={lists} isAdmin={isAdmin} onChanged={onChanged} />}
    {section === 'recetas' && <RecipesView isAdmin={isAdmin} />}
    {section === 'menu' && <MenuView isAdmin={isAdmin} onListsChanged={onChanged} />}
    {section === 'viajes' && <TripsView isAdmin={isAdmin} />}
  </>
}

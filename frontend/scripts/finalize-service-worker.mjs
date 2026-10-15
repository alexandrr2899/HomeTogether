import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const html = readFileSync(resolve(root, 'dist/index.html'), 'utf8')
const workerPath = resolve(root, 'dist/service-worker.js')
const assets = [...new Set([...html.matchAll(/(?:src|href)="(\/assets\/[^"?]+)"/g)].map((match) => match[1]))]
if (!assets.some((asset) => asset.endsWith('.js')) || !assets.some((asset) => asset.endsWith('.css'))) {
  throw new Error('No se encontraron los archivos JS y CSS del shell para la PWA.')
}

const version = createHash('sha256').update(html).digest('hex').slice(0, 12)
const source = readFileSync(workerPath, 'utf8')
const updated = source
  .replace("const CACHE = 'home-together-shell-v1'", `const CACHE = 'home-together-shell-${version}'`)
  .replace('const ASSETS = []', `const ASSETS = ${JSON.stringify(assets)}`)
if (updated === source || updated.includes('const ASSETS = []')) throw new Error('No se pudo preparar la caché de la PWA.')
writeFileSync(workerPath, updated)

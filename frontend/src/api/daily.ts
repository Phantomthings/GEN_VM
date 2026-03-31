import { apiClient } from './client'

const cacheTtlMs = 60_000
const responseCache = new Map<string, { expiresAt: number; value: unknown }>()

async function cachedGet<T>(url: string, params: Record<string, string | number>, useCache = true): Promise<T> {
  const sortedEntries = Object.entries(params).sort(([a], [b]) => a.localeCompare(b))
  const cacheKey = `${url}?${new URLSearchParams(sortedEntries.map(([k, v]) => [k, String(v)])).toString()}`

  if (useCache) {
    const hit = responseCache.get(cacheKey)
    if (hit && hit.expiresAt > Date.now()) return hit.value as T
  }

  const { data } = await apiClient.get(url, { params })
  if (useCache) {
    responseCache.set(cacheKey, { expiresAt: Date.now() + cacheTtlMs, value: data })
  }
  return data as T
}

export async function fetchSocDates(project: string) {
  const data = await cachedGet<{ dates: string[] }>('/api/daily/soc/dates', { project })
  return data.dates
}

export async function fetchSocData(project: string, date: string) {
  return cachedGet<Record<string, unknown>>('/api/daily/soc/data', { project, date })
}

export async function fetchReguDates(project: string) {
  const data = await cachedGet<{ dates: string[] }>('/api/daily/regu/dates', { project })
  return data.dates
}

export async function fetchReguData(project: string, date: string) {
  return cachedGet<Record<string, unknown>>('/api/daily/regu/data', { project, date })
}

export async function fetchEnergyDates(project: string) {
  const data = await cachedGet<{ dates: string[] }>('/api/daily/energy/dates', { project })
  return data.dates
}

export async function fetchEnergyData(project: string, date: string) {
  return cachedGet<Record<string, unknown>>('/api/daily/energy/data', { project, date })
}

export async function fetchPowerLimitationDates(project: string) {
  const data = await cachedGet<{ dates: string[] }>('/api/daily/power-limitation/dates', { project })
  return data.dates
}

export async function fetchPowerLimitationData(project: string, date: string) {
  return cachedGet<Record<string, unknown>>('/api/daily/power-limitation/data', { project, date })
}

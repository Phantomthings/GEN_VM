import { apiClient } from './client'

export async function fetchSignalsConfig() {
  const { data } = await apiClient.get('/api/signals/config')
  return data
}

export async function fetchSignalsData(project: string, date: string, signals: string[]) {
  const { data } = await apiClient.get('/api/signals/data', {
    params: { project, date, signals: signals.join(',') },
  })
  return data
}

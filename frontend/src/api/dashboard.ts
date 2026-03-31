import { apiClient } from './client'

export async function fetchAlertsJ1() {
  const { data } = await apiClient.get('/api/dashboard/alerts-j1')
  return data
}

export async function fetchSocMorning() {
  const { data } = await apiClient.get('/api/dashboard/soc-morning')
  return data
}

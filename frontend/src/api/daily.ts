import { apiClient } from './client'

export async function fetchSocDates(project: string) {
  const { data } = await apiClient.get('/api/daily/soc/dates', { params: { project } })
  return data.dates as string[]
}

export async function fetchSocData(project: string, date: string) {
  const { data } = await apiClient.get('/api/daily/soc/data', { params: { project, date } })
  return data
}

export async function fetchReguDates(project: string) {
  const { data } = await apiClient.get('/api/daily/regu/dates', { params: { project } })
  return data.dates as string[]
}

export async function fetchReguData(project: string, date: string) {
  const { data } = await apiClient.get('/api/daily/regu/data', { params: { project, date } })
  return data
}

export async function fetchEnergyDates(project: string) {
  const { data } = await apiClient.get('/api/daily/energy/dates', { params: { project } })
  return data.dates as string[]
}

export async function fetchEnergyData(project: string, date: string) {
  const { data } = await apiClient.get('/api/daily/energy/data', { params: { project, date } })
  return data
}

export async function fetchPowerLimitationDates(project: string) {
  const { data } = await apiClient.get('/api/daily/power-limitation/dates', { params: { project } })
  return data.dates as string[]
}

export async function fetchPowerLimitationData(project: string, date: string) {
  const { data } = await apiClient.get('/api/daily/power-limitation/data', { params: { project, date } })
  return data
}

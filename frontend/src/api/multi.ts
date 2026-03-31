import { apiClient } from './client'

export async function fetchComparisonDates(sites: string[]) {
  const { data } = await apiClient.get('/api/multi/comparison/dates', {
    params: { sites: sites.join(',') },
  })
  return data.dates as string[]
}

export async function fetchComparisonData(sites: string[], date: string) {
  const { data } = await apiClient.get('/api/multi/comparison/data', {
    params: { sites: sites.join(','), date },
  })
  return data
}

export async function fetchIntervalDates(sites: string[]) {
  const { data } = await apiClient.get('/api/multi/interval/dates', {
    params: { sites: sites.join(',') },
  })
  return data.dates as string[]
}

export async function fetchIntervalData(sites: string[], startDate: string, endDate: string) {
  const { data } = await apiClient.get('/api/multi/interval/data', {
    params: { sites: sites.join(','), start_date: startDate, end_date: endDate },
  })
  return data
}

export async function fetchStatsDates(sites: string[]) {
  const { data } = await apiClient.get('/api/multi/stats/dates', {
    params: { sites: sites.join(',') },
  })
  return data.dates as string[]
}

export async function fetchStatsData(sites: string[], startDate: string, endDate: string) {
  const { data } = await apiClient.get('/api/multi/stats/data', {
    params: { sites: sites.join(','), start_date: startDate, end_date: endDate },
  })
  return data
}

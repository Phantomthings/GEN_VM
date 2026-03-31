import { apiClient } from './client'

export async function fetchAlarmDates(sites: string[]) {
  const { data } = await apiClient.get('/api/alarms/dates', {
    params: { sites: sites.join(',') },
  })
  return data.dates as string[]
}

export async function fetchAlarmData(sites: string[], dates: string[]) {
  const { data } = await apiClient.get('/api/alarms/data', {
    params: { sites: sites.join(','), dates: dates.join(',') },
  })
  return data
}
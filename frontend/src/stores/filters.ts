import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useFiltersStore = defineStore('filters', () => {
  const dailyProject = ref<string | null>(null)
  const dailyDate = ref<string | null>(null)

  const multiSites = ref<string[]>([])
  const multiDateStart = ref<string | null>(null)
  const multiDateEnd = ref<string | null>(null)

  function setDailyProject(p: string) {
    dailyProject.value = p
  }

  function setDailyDate(d: string) {
    dailyDate.value = d
  }

  /** Returns a Date from the saved dailyDate if present in availableDates, else the last date. */
  function resolveDailyDate(availableDates: string[]): Date | null {
    if (!availableDates.length) return null
    const target = dailyDate.value && availableDates.includes(dailyDate.value)
      ? dailyDate.value
      : availableDates[availableDates.length - 1]
    return new Date(target + 'T12:00:00')
  }

  function setMultiSites(s: string[]) {
    multiSites.value = s
  }

  function setMultiDateRange(start: string, end: string) {
    multiDateStart.value = start
    multiDateEnd.value = end
  }

  return {
    dailyProject, dailyDate,
    multiSites, multiDateStart, multiDateEnd,
    setDailyProject, setDailyDate, resolveDailyDate, setMultiSites, setMultiDateRange,
  }
})

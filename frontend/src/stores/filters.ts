import { defineStore } from 'pinia'
import { ref } from 'vue'

function parseYmdToLocalNoon(ymd: string): Date {
  return new Date(`${ymd}T12:00:00`)
}

function formatDateToYmdLocal(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

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
    return parseYmdToLocalNoon(target)
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
    parseYmdToLocalNoon, formatDateToYmdLocal,
  }
})

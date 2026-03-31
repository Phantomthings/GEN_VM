import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiClient } from '@/api/client'

interface Project {
  code: string
  label: string
}

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<Project[]>([])
  const sites = ref<Record<string, string>>({})
  const loaded = ref(false)

  async function fetchProjects() {
    if (loaded.value) return
    const { data } = await apiClient.get('/api/projects')
    projects.value = data.projects
    sites.value = data.sites
    loaded.value = true
  }

  function labelSite(code: string): string {
    const suffix = code.split('_').pop() ?? code
    return sites.value[suffix] ?? code
  }

  return { projects, sites, loaded, fetchProjects, labelSite }
})

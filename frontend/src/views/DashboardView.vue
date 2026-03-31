<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import StatusBadge from '@/components/common/StatusBadge.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import { fetchAlertsJ1, fetchSocMorning } from '@/api/dashboard'
import { fmtDate } from '@/utils/format'

interface SocRow {
  date: string
  site: string
  soc_below_85: boolean | null
  soc_5h10: number | null
}

interface AlertRow {
  date: string
  site: string
  soc_below_85: boolean
  soc_diff_gt_8: boolean | null
  temp_over_28: boolean | null
  water_level_low: boolean | null
  energy_ev_low: boolean | null
}

const loading = ref(true)
const socRows = ref<SocRow[]>([])
const alertRows = ref<AlertRow[]>([])
const alertDate = ref('')
const socDate = ref('')
const summary = ref<{ soc_mgmt_ok?: boolean; critiques_ok?: boolean }>({})

onMounted(async () => {
  try {
    const [socData, alertData] = await Promise.all([
      fetchSocMorning(),
      fetchAlertsJ1(),
    ])
    socRows.value = socData.rows
    socDate.value = socData.date
    alertRows.value = alertData.rows
    alertDate.value = alertData.date
    summary.value = alertData.summary ?? {}
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <LoadingOverlay v-if="loading" />

  <template v-else>
    <!-- SOC Morning Section -->
    <div class="section">
      <h2 class="section-title">Analyse du SOC Management du {{ fmtDate(socDate) }}</h2>

      <div v-if="socRows.length === 0" style="color: #94a3b8; padding: 1rem;">
        Aucune donnée SOC à 05:10 disponible.
      </div>

      <DataTable v-else :value="socRows" stripedRows size="small">
        <Column field="date" header="Date" sortable>
          <template #body="{ data }">{{ fmtDate(data.date) }}</template>
        </Column>
        <Column field="site" header="Site" sortable />
        <Column field="soc_below_85" header="SOC Batterie &lt; 85% à 05:10" sortable>
          <template #body="{ data }">
            <StatusBadge :alert="data.soc_below_85" />
          </template>
        </Column>
        <Column field="soc_5h10" header="SOC à 5h10" sortable>
          <template #body="{ data }">
            {{ data.soc_5h10 != null ? `${data.soc_5h10}%` : '' }}
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Alerts J-1 Section -->
    <div class="section">
      <h2 class="section-title">Analyse des alertes du {{ fmtDate(alertDate) }}</h2>

      <div v-if="alertRows.length === 0" style="color: #94a3b8; padding: 1rem;">
        Aucune donnée disponible pour J-1.
      </div>

      <template v-else>
        <!-- Summary cards -->
        <div class="two-columns" style="margin-bottom: 1.5rem;">
          <div class="kpi-card" :class="summary.soc_mgmt_ok ? 'green' : 'red'">
            <div class="kpi-title">SOC Management</div>
            <div class="kpi-value">
              <i :class="summary.soc_mgmt_ok ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'"></i>
              {{ summary.soc_mgmt_ok ? 'OK' : 'Anomalie' }}
            </div>
          </div>
          <div class="kpi-card" :class="summary.critiques_ok ? 'green' : 'red'">
            <div class="kpi-title">Autres alarmes critiques</div>
            <div class="kpi-value">
              <i :class="summary.critiques_ok ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'"></i>
              {{ summary.critiques_ok ? 'OK' : 'Anomalie' }}
            </div>
          </div>
        </div>

        <!-- Detail table -->
        <h3 style="font-size: 1rem; margin-bottom: 0.75rem;">Détail par site</h3>
        <DataTable :value="alertRows" stripedRows size="small">
          <Column field="date" header="Date" sortable>
            <template #body="{ data }">{{ fmtDate(data.date) }}</template>
          </Column>
          <Column field="site" header="Site" sortable />
          <Column field="soc_below_85" header="SOC &lt; 85% à 05:10" sortable>
            <template #body="{ data }">
              <StatusBadge :alert="data.soc_below_85" />
            </template>
          </Column>
          <Column field="soc_diff_gt_8" header="ΔSOC racks > 8%" sortable>
            <template #body="{ data }">
              <StatusBadge :alert="data.soc_diff_gt_8" />
            </template>
          </Column>
          <Column field="temp_over_28" header="Temp. > 28°C" sortable>
            <template #body="{ data }">
              <StatusBadge :alert="data.temp_over_28" />
            </template>
          </Column>
          <Column field="water_level_low" header="Niveau eau KKT" sortable>
            <template #body="{ data }">
              <StatusBadge :alert="data.water_level_low" />
            </template>
          </Column>
          <Column field="energy_ev_low" header="Énergie EV &lt; 35 kWh" sortable>
            <template #body="{ data }">
              <StatusBadge :alert="data.energy_ev_low" />
            </template>
          </Column>
        </DataTable>
      </template>
    </div>
  </template>
</template>

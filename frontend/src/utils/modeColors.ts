/**
 * Palette canonique des modes — une seule source de vérité pour toute l'app.
 * Même couleur = même sens, partout.
 *
 * PlantRunMode (régulation) :
 *   1 = OFF     → rouge
 *   2 = Stand-by → gris ardoise
 *   3 = AC       → bleu
 *   4 = Batterie → ambre
 *
 * SOC Management (batterie) :
 *   0 = OFF/Désactivé → gris clair
 *   1 = RUN EV (1)    → bleu acier
 *   2 = RUN (2)       → vert (#2ca55c)
 *   3 = Stand-by (3)  → violet
 *   4 = Enable (4)    → ambre
 */

export const REG_MODE_COLORS: Record<number, string> = {
  1: '#ef4444', // OFF      → rouge
  2: '#94a3b8', // Stand-by → gris ardoise
  3: '#3b82f6', // AC       → bleu
  4: '#f59e0b', // Batterie → ambre
}

export const REG_MODE_LABELS: Record<number, string> = {
  1: 'OFF (1)',
  2: 'Stand-by (2)',
  3: 'AC (3)',
  4: 'Batterie (4)',
}

export const SOC_STATE_COLORS: Record<number, string> = {
  0: '#cbd5e1', // OFF/Désactivé → gris clair
  1: '#1d4ed8', // RUN EV (1)    → bleu acier
  2: '#2ca55c', // RUN (2)       → vert
  3: '#8b5cf6', // Stand-by (3)  → violet
  4: '#f59e0b', // Enable (4)    → ambre
}

export const SOC_STATE_LABELS: Record<number, string> = {
  0: 'OFF/Désactivé (0)',
  1: 'RUN EV (1)',
  2: 'RUN (2)',
  3: 'Stand-by (3)',
  4: 'Enable (4)',
}

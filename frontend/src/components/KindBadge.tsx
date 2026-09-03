import type { CategoryKind } from '../api/types'

const KIND_LABELS: Record<CategoryKind, string> = {
  fixed: 'Fixkosten',
  variable: 'Variable Kosten',
  income: 'Einnahmen',
  debt: 'Schuldentilgung',
  savings: 'Sparen',
}

export function KindBadge({ kind }: { kind: CategoryKind }) {
  return <span className={`badge ${kind}`}>{KIND_LABELS[kind]}</span>
}

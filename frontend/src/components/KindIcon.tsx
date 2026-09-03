import { CreditCard, FileText, PiggyBank, ShoppingCart, TrendUp, type Icon } from '@phosphor-icons/react'
import type { CategoryKind } from '../api/types'

const ICONS: Record<CategoryKind, Icon> = {
  fixed: FileText,
  variable: ShoppingCart,
  income: TrendUp,
  debt: CreditCard,
  savings: PiggyBank,
}

export function KindIcon({ kind, color }: { kind: CategoryKind; color?: string }) {
  const IconComponent = ICONS[kind]
  return (
    <div className="row-icon" style={color ? { background: `${color}1a`, color } : undefined}>
      <IconComponent size={18} weight="regular" aria-hidden="true" />
    </div>
  )
}

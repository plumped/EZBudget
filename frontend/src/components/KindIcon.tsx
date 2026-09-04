import { CreditCard, FileText, PiggyBank, ShoppingCart, TrendUp, type Icon } from '@phosphor-icons/react'
import type { CategoryKind } from '../api/types'
import { ICON_COMPONENTS } from './iconCatalog'

const KIND_FALLBACK_ICONS: Record<CategoryKind, Icon> = {
  fixed: FileText,
  variable: ShoppingCart,
  income: TrendUp,
  debt: CreditCard,
  savings: PiggyBank,
}

export function KindIcon({ kind, color, icon }: { kind: CategoryKind; color?: string; icon?: string }) {
  const IconComponent = (icon && ICON_COMPONENTS[icon]) || KIND_FALLBACK_ICONS[kind]
  return (
    <div className="row-icon" style={color ? { background: `${color}1a`, color } : undefined}>
      <IconComponent size={18} weight="regular" aria-hidden="true" />
    </div>
  )
}

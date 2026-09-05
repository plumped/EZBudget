export interface User {
  id: number
  username: string
  email: string
}

export type AccountType = 'checking' | 'savings' | 'cash' | 'credit'

export interface Account {
  id: number
  name: string
  account_type: AccountType
  iban: string
  starting_balance: string
  is_archived: boolean
  balance: string
  created_at: string
}

export type CategoryKind = 'fixed' | 'variable' | 'income' | 'debt' | 'savings'

export interface CategoryBudgetHistoryEntry {
  year: number
  month: number
  monthly_budget: string
}

export interface Category {
  id: number
  name: string
  kind: CategoryKind
  monthly_budget: string
  keywords: string
  color: string
  icon: string
  target_amount: string | null
  target_date: string | null
  target_progress_percent: number | null
  budget_history: CategoryBudgetHistoryEntry[]
  is_archived: boolean
  created_at: string
  spent: string
  available: string
  rollover: string
  progress: number
}

export interface Transaction {
  id: number
  account: number
  account_name: string
  category: number | null
  category_name: string | null
  category_color: string | null
  category_icon: string | null
  date: string
  amount: string
  description: string
  counterparty: string
  import_ref: string | null
  is_expense: boolean
  is_transfer: boolean
  transfer_pair: number | null
  created_at: string
}

export type RecurringFrequency = 'weekly' | 'biweekly' | 'monthly' | 'yearly'

export interface RecurringTransaction {
  id: number
  account: number
  account_name: string
  category: number | null
  category_name: string | null
  category_color: string | null
  description: string
  counterparty: string
  amount: string
  frequency: RecurringFrequency
  day_of_month: number
  month_of_year: number
  weekday: number
  start_date: string
  is_active: boolean
  created_at: string
}

export interface Debt {
  id: number
  name: string
  creditor: string
  principal: string
  current_balance: string
  interest_rate: string
  minimum_payment: string
  is_paid_off: boolean
  category: number | null
  category_name: string | null
  account: number | null
  account_name: string | null
  created_at: string
  paid_so_far: string
  progress_percent: number
}

export type PayoffStrategy = 'avalanche' | 'snowball'

export interface PayoffResult {
  strategy: PayoffStrategy
  extra_budget: string
  total_balance: string
  total_minimum: string
  total_monthly: string
  months: number
  total_interest: string
  payoff_order: string[]
  debt_free_date: string | null
  reached_max: boolean
  schedule: { month: number; date: string | null; total_balance: string }[]
}

export interface CategoryGroup {
  budgeted: string
  spent: string
  categories: Category[]
}

export interface DashboardData {
  year: number
  month: number
  month_name: string
  period_start: string
  period_end: string
  prev: { year: number; month: number }
  next: { year: number; month: number }
  days_in_month: number
  total_balance: string
  income_total: string
  expense_total: string
  net_total: string
  fixed: CategoryGroup
  variable: CategoryGroup
  debt_categories: Category[]
  savings: Category[]
  total_debt: string
  total_minimum: string
  open_debts_count: number
  recent_transactions: Transaction[]
  generated_recurring: Transaction[]
  uncategorized_count: number
}

export interface TrendMonth {
  year: number
  month: number
}

export interface TrendCategory {
  id: number
  name: string
  kind: CategoryKind
  color: string
  icon: string
  spent_by_month: string[]
}

export interface TrendTopCategory {
  id: number
  name: string
  color: string
  total_spent: string
}

export interface TrendYearOverYear {
  current_year: number
  current_month: number
  current_income: string
  current_expense: string
  previous_year: number
  previous_income: string
  previous_expense: string
}

export interface TrendsData {
  months: TrendMonth[]
  income_by_month: string[]
  expense_by_month: string[]
  net_by_month: string[]
  categories: TrendCategory[]
  top_categories: TrendTopCategory[]
  year_over_year: TrendYearOverYear
}

export interface ImportBatch {
  id: number
  account: number
  account_name: string
  filename: string
  imported_at: string
  transactions_created: number
  transactions_skipped: number
}

export interface ImportRow {
  date: string | null
  amount: string
  currency: string
  description: string
  counterparty: string
  entry_ref: string
  account_iban: string
  suggested_category_id: number | null
  is_duplicate: boolean
}

export type RuleMatchType = 'contains' | 'startswith' | 'exact'

export interface RuleConditions {
  description_match_type: RuleMatchType
  description_value: string
  counterparty_match_type: RuleMatchType
  counterparty_value: string
  amount_min: string | null
  amount_max: string | null
}

export interface Rule extends RuleConditions {
  id: number
  name: string
  category: number
  category_name: string
  category_color: string
  priority: number
  is_active: boolean
  created_at: string
}

export interface RulePreviewResult {
  count: number
  transactions: Transaction[]
  preview_limit: number
}

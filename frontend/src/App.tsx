import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { AccountDetailPage } from './pages/AccountDetailPage'
import { AccountFormPage } from './pages/AccountFormPage'
import { AccountsPage } from './pages/AccountsPage'
import { DashboardPage } from './pages/DashboardPage'
import { DebtDetailPage } from './pages/DebtDetailPage'
import { DebtFormPage } from './pages/DebtFormPage'
import { DebtsPage } from './pages/DebtsPage'
import { EnvelopeDetailPage } from './pages/EnvelopeDetailPage'
import { EnvelopeFormPage } from './pages/EnvelopeFormPage'
import { EnvelopesPage } from './pages/EnvelopesPage'
import { ImportHistoryPage } from './pages/ImportHistoryPage'
import { ImportPage } from './pages/ImportPage'
import { LoginPage } from './pages/LoginPage'
import { RecurringFormPage } from './pages/RecurringFormPage'
import { RecurringPage } from './pages/RecurringPage'
import { SignupPage } from './pages/SignupPage'
import { TransactionFormPage } from './pages/TransactionFormPage'
import { TransactionsPage } from './pages/TransactionsPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />

              <Route path="/envelopes" element={<EnvelopesPage />} />
              <Route path="/envelopes/new" element={<EnvelopeFormPage />} />
              <Route path="/envelopes/:id" element={<EnvelopeDetailPage />} />
              <Route path="/envelopes/:id/edit" element={<EnvelopeFormPage />} />

              <Route path="/transactions" element={<TransactionsPage />} />
              <Route path="/transactions/add" element={<TransactionFormPage />} />

              <Route path="/accounts" element={<AccountsPage />} />
              <Route path="/accounts/new" element={<AccountFormPage />} />
              <Route path="/accounts/:id" element={<AccountDetailPage />} />
              <Route path="/accounts/:id/edit" element={<AccountFormPage />} />

              <Route path="/recurring" element={<RecurringPage />} />
              <Route path="/recurring/new" element={<RecurringFormPage />} />
              <Route path="/recurring/:id/edit" element={<RecurringFormPage />} />

              <Route path="/debts" element={<DebtsPage />} />
              <Route path="/debts/new" element={<DebtFormPage />} />
              <Route path="/debts/:id" element={<DebtDetailPage />} />

              <Route path="/import" element={<ImportPage />} />
              <Route path="/import/history" element={<ImportHistoryPage />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

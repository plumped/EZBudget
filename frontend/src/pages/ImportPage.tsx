import { ClockCounterClockwise } from '@phosphor-icons/react'
import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
import type { Account, Category, ImportRow } from '../api/types'
import { FieldError } from '../components/FieldError'
import { useToast } from '../context/ToastContext'
import { formatMoney } from '../utils/format'

interface PreviewRow extends ImportRow {
  include: boolean
  category_id: number | null
}

export function ImportPage() {
  const navigate = useNavigate()
  const push = useToast()
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [accountId, setAccountId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [filename, setFilename] = useState('')
  const [rows, setRows] = useState<PreviewRow[] | null>(null)
  const [parsing, setParsing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<Account[]>('/accounts/', { params: { active_only: 1 } }).then((res) => {
      setAccounts(res.data)
      if (res.data.length > 0) setAccountId(String(res.data[0].id))
    })
    api.get<Category[]>('/categories/', { params: { active_only: 1 } }).then((res) => setCategories(res.data))
  }, [])

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null)
  }

  async function handleParse(event: FormEvent) {
    event.preventDefault()
    if (!file) {
      setError('Bitte eine CAMT.053-XML-Datei auswählen.')
      return
    }
    setError(null)
    setParsing(true)
    try {
      const formData = new FormData()
      formData.append('account', accountId)
      formData.append('camt_file', file)
      const res = await api.post<{ account: number; filename: string; rows: ImportRow[] }>('/import/parse/', formData)
      if (res.data.rows.length === 0) {
        push('info', 'Keine Buchungen in der Datei gefunden.')
        return
      }
      setFilename(res.data.filename)
      setRows(
        res.data.rows.map((r) => ({
          ...r,
          include: !r.is_duplicate && !r.is_possible_duplicate,
          category_id: r.suggested_category_id,
        })),
      )
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setParsing(false)
    }
  }

  async function handleConfirm() {
    if (!rows) return
    setConfirming(true)
    try {
      const res = await api.post<{ created: number; skipped: number }>('/import/confirm/', {
        account: Number(accountId),
        filename,
        rows: rows.map((r) => ({
          date: r.date,
          amount: r.amount,
          description: r.description,
          counterparty: r.counterparty,
          entry_ref: r.entry_ref,
          category_id: r.category_id,
          include: r.include,
          is_duplicate: r.is_duplicate,
        })),
      })
      push('success', `Import abgeschlossen: ${res.data.created} Buchungen importiert, ${res.data.skipped} übersprungen.`)
      navigate('/transactions')
    } catch (err) {
      push('error', extractErrorMessage(err))
    } finally {
      setConfirming(false)
    }
  }

  function updateRow(index: number, patch: Partial<PreviewRow>) {
    setRows((current) => current?.map((r, i) => (i === index ? { ...r, ...patch } : r)) ?? null)
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>CAMT.053-Import</h1>
          <p>ISO-20022-Kontoauszug hochladen und Buchungen prüfen.</p>
        </div>
        <Link to="/import/history" className="btn secondary">
          <ClockCounterClockwise size={16} weight="bold" aria-hidden="true" />
          Import-Historie
        </Link>
      </div>

      {!rows ? (
        <div className="card card-form">
          <form onSubmit={handleParse} noValidate>
            <div className="field">
              <label htmlFor="account">Konto</label>
              <select id="account" value={accountId} onChange={(e) => setAccountId(e.target.value)} required>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="file">CAMT.053-XML-Datei</label>
              <input id="file" type="file" accept=".xml" onChange={handleFileChange} required />
            </div>
            {error && <FieldError id="file-error" message={error} />}
            <button type="submit" className="btn" disabled={parsing}>
              {parsing ? 'Datei wird geprüft …' : 'Datei prüfen'}
            </button>
          </form>
        </div>
      ) : (
        <>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th />
                  <th>Datum</th>
                  <th>Beschreibung</th>
                  <th>Gegenpartei</th>
                  <th className="text-right">Betrag</th>
                  <th>Umschlag</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={row.entry_ref + index}>
                    <td>
                      <input
                        type="checkbox"
                        checked={row.include}
                        disabled={row.is_duplicate}
                        onChange={(e) => updateRow(index, { include: e.target.checked })}
                      />
                    </td>
                    <td>{row.date ?? '—'}</td>
                    <td>{row.description}</td>
                    <td>{row.counterparty || '—'}</td>
                    <td className={`amount-cell ${parseFloat(row.amount) < 0 ? 'negative' : 'positive'}`}>
                      {formatMoney(row.amount)}
                    </td>
                    <td>
                      <select
                        value={row.category_id ?? ''}
                        onChange={(e) => updateRow(index, { category_id: e.target.value ? Number(e.target.value) : null })}
                        className="category-select"
                      >
                        <option value="">— ohne —</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      {row.is_duplicate && <span className="badge">Duplikat</span>}
                      {!row.is_duplicate && row.is_possible_duplicate && (
                        <span className="badge warning" title="Datum und Betrag stimmen mit einer bereits erfassten Buchung überein — z.B. wenn du diese Zahlung schon manuell eingetragen hast.">
                          Evtl. schon erfasst?
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="form-actions spaced">
            <button type="button" className="btn" disabled={confirming} onClick={() => void handleConfirm()}>
              {confirming ? 'Importiere …' : 'Import bestätigen'}
            </button>
            <button type="button" className="btn secondary" onClick={() => setRows(null)}>
              Abbrechen
            </button>
          </div>
        </>
      )}
    </>
  )
}

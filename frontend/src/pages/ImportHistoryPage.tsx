import { UploadSimple } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import type { ImportBatch } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { Skeleton } from '../components/Skeleton'

export function ImportHistoryPage() {
  const [batches, setBatches] = useState<ImportBatch[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<ImportBatch[]>('/import/history/')
      .then((res) => setBatches(res.data))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Import-Historie</h1>
          <p>Bisherige CAMT.053-Importe.</p>
        </div>
        <Link to="/import" className="btn secondary">
          <UploadSimple size={16} weight="bold" aria-hidden="true" />
          Neuer Import
        </Link>
      </div>

      {loading ? (
        <div className="table-wrap" aria-busy="true">
          <div className="content-pad">
            <Skeleton lines={4} />
          </div>
        </div>
      ) : batches.length === 0 ? (
        <EmptyState>Noch keine Importe durchgeführt.</EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Datum</th>
                <th>Datei</th>
                <th>Konto</th>
                <th>Importiert</th>
                <th>Übersprungen</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((b) => (
                <tr key={b.id}>
                  <td>{new Date(b.imported_at).toLocaleString('de-CH')}</td>
                  <td>{b.filename}</td>
                  <td>{b.account_name}</td>
                  <td>{b.transactions_created}</td>
                  <td>{b.transactions_skipped}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

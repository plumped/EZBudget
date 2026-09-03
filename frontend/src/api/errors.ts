import axios from 'axios'

export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as unknown
    if (typeof data === 'string' && data) {
      return data
    }
    if (data && typeof data === 'object') {
      const obj = data as Record<string, unknown>
      if (typeof obj.detail === 'string') {
        return obj.detail
      }
      const parts: string[] = []
      for (const [key, value] of Object.entries(obj)) {
        const text = Array.isArray(value) ? value.join(' ') : String(value)
        parts.push(key === 'non_field_errors' ? text : `${key}: ${text}`)
      }
      if (parts.length) {
        return parts.join(' | ')
      }
    }
    if (err.message) {
      return err.message
    }
  }
  return 'Unbekannter Fehler.'
}

export interface FieldErrors {
  general?: string
  fields: Record<string, string>
}

/**
 * Splits a DRF error response into per-field messages (for aria-describedby
 * wiring next to the relevant input) and a general/non-field message.
 */
export function extractFieldErrors(err: unknown): FieldErrors {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as unknown
    if (typeof data === 'string' && data) {
      return { general: data, fields: {} }
    }
    if (data && typeof data === 'object') {
      const obj = data as Record<string, unknown>
      const fields: Record<string, string> = {}
      let general: string | undefined
      for (const [key, value] of Object.entries(obj)) {
        const text = Array.isArray(value) ? value.join(' ') : String(value)
        if (key === 'detail' || key === 'non_field_errors') {
          general = general ? `${general} ${text}` : text
        } else {
          fields[key] = text
        }
      }
      if (general || Object.keys(fields).length) {
        return { general, fields }
      }
    }
    if (err.message) {
      return { general: err.message, fields: {} }
    }
  }
  return { general: 'Unbekannter Fehler.', fields: {} }
}

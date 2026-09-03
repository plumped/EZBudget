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

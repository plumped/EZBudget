import { WarningCircle } from '@phosphor-icons/react'

export function FieldError({ id, message }: { id: string; message: string }) {
  return (
    <p className="error-text" id={id} role="alert">
      <WarningCircle size={14} weight="fill" aria-hidden="true" />
      <span>{message}</span>
    </p>
  )
}

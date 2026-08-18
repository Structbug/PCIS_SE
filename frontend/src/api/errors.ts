/**
 * Maps an API error to a safe, hard-coded message (H-12).
 *
 * The backend `response.data.message` is never shown verbatim: a leaky backend
 * (stack trace, SQL error, "user X not found") must not be echoed into the UI.
 * Instead, the HTTP status is mapped to generic copy. Callers may override
 * specific statuses or supply a per-call fallback.
 */
export function apiErrorMessage(
  err: unknown,
  fallback = 'Something went wrong',
  overrides: Partial<Record<number, string>> = {},
): string {
  const status = (err as { response?: { status?: number } })?.response?.status
  if (status != null && status in overrides) return overrides[status]!
  switch (status) {
    case 400: return 'Invalid request. Please check your input and try again.'
    case 401: return 'Your session has expired. Please sign in again.'
    case 403: return 'You are not allowed to do that.'
    case 404: return 'The requested record was not found.'
    case 409: return 'That record already exists.'
    case 429: return 'Too many attempts. Please try again later.'
    case 500: return 'Server error. Please try again later.'
    default: return fallback
  }
}
export interface OptionItem {
  _id: string
}

export function optionLabels<T extends OptionItem>(
  items: T[],
  primary: (item: T) => string,
  context: (item: T) => string | null | undefined,
): Record<string, string> {
  const counts = new Map<string, number>()
  for (const item of items) {
    const key = (primary(item) || '').trim().toLowerCase()
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  const labels: Record<string, string> = {}
  for (const item of items) {
    const name = primary(item) || ''
    const key = name.trim().toLowerCase()
    const detail = context(item)?.trim()
    labels[item._id] = detail && counts.get(key)! > 1 ? `${name} (${detail})` : name
  }
  return labels
}
interface Slice {
  label: string
  value: number
  color: string
}

interface DonutChartProps {
  data: Slice[]
  size?: number
  thickness?: number
}

export function DonutChart({ data, size = 180, thickness = 26 }: DonutChartProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0)
  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius

  let offset = 0
  const segments = data
    .filter((d) => d.value > 0)
    .map((d) => {
      const fraction = d.value / total
      const seg = { ...d, dash: fraction * circumference, offset: offset * circumference }
      offset += fraction
      return seg
    })

  return (
    <div className="chart-donut">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border-light)"
          strokeWidth={thickness}
        />
        {segments.map((seg) => (
          <circle
            key={seg.label}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={seg.color}
            strokeWidth={thickness}
            strokeDasharray={`${seg.dash} ${circumference - seg.dash}`}
            strokeDashoffset={-seg.offset}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        ))}
      </svg>
      <div className="chart-center">
        <span className="chart-total">{total}</span>
        <span className="chart-total-label">Items</span>
      </div>
    </div>
  )
}

interface BarDatum {
  label: string
  value: number
  color?: string
}

interface BarChartProps {
  data: BarDatum[]
  height?: number
}

export function BarChart({ data, height = 180 }: BarChartProps) {
  const max = Math.max(1, ...data.map((d) => d.value))

  return (
    <div className="chart-bars" style={{ height }}>
      {data.map((d) => (
        <div key={d.label} className="chart-bar-col" title={`${d.label}: ${d.value}`}>
          <div className="chart-bar-value">{d.value}</div>
          <div className="chart-bar-track">
            <div
              className="chart-bar-fill"
              style={{
                height: `${Math.max(2, (d.value / max) * 100)}%`,
                background: d.color || 'var(--accent)',
              }}
            />
          </div>
          <div className="chart-bar-label">{d.label}</div>
        </div>
      ))}
    </div>
  )
}

interface LegendProps {
  items: Slice[]
}

export function ChartLegend({ items }: LegendProps) {
  return (
    <ul className="chart-legend">
      {items.map((item) => (
        <li key={item.label}>
          <span className="chart-legend-swatch" style={{ background: item.color }} />
          <span className="chart-legend-label">{item.label}</span>
          <span className="chart-legend-value">{item.value}</span>
        </li>
      ))}
    </ul>
  )
}
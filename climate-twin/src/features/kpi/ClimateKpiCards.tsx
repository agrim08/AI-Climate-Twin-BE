import {
  Thermometer,
  Droplets,
  Wind,
  Flame,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react"
import { WEEKLY_FORECAST, aqiLabel } from "@/mock/forecast"

/* ═══════════════════════════════════════════════════════════════════════════
   DATA SLICES FROM MOCK
═══════════════════════════════════════════════════════════════════════════ */

const TEMPS_7D  = WEEKLY_FORECAST.map((d) => d.tempMax)   // [34.0, 35.4, 37.1, ...]
const RAINS_7D  = WEEKLY_FORECAST.map((d) => d.rainfall)  // [12, 4, 0, 0, 22, 38, 18]
const DAYS_7D   = WEEKLY_FORECAST.map((d) => d.label)     // ["Today", "Tue", ...]

/* ═══════════════════════════════════════════════════════════════════════════
   SHARED PRIMITIVES
═══════════════════════════════════════════════════════════════════════════ */

/** Inline SVG polyline sparkline */
function Sparkline({
  values,
  stroke,
  fill,
}: {
  values: number[]
  stroke: string
  fill: string
}) {
  const W = 180, H = 44, pad = 3
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const pts = values.map((v, i) => ({
    x: pad + (i / (values.length - 1)) * (W - pad * 2),
    y: H - pad - ((v - min) / range) * (H - pad * 2),
  }))

  const linePath = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")
  const areaPath = `${linePath} L ${pts[pts.length - 1].x.toFixed(1)} ${H} L ${pts[0].x.toFixed(1)} ${H} Z`

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      fill="none"
      aria-hidden
      className="w-full overflow-visible"
    >
      {/* Area fill */}
      <defs>
        <linearGradient id={`sg-${stroke.replace(/[^a-z]/gi, "")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={fill} stopOpacity="0.35" />
          <stop offset="100%" stopColor={fill} stopOpacity="0"    />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#sg-${stroke.replace(/[^a-z]/gi, "")})`} />
      {/* Line */}
      <path d={linePath} stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* Last dot */}
      <circle cx={pts[pts.length - 1].x} cy={pts[pts.length - 1].y} r="3" fill={stroke} />
    </svg>
  )
}

/** 7-day mini vertical bar chart */
function MiniBarChart({
  values,
  labels,
  accentColor,
}: {
  values: number[]
  labels: string[]
  accentColor: string
}) {
  const max = Math.max(...values, 1)
  return (
    <div className="flex items-end gap-1 w-full" style={{ height: 44 }} aria-hidden>
      {values.map((v, i) => {
        const heightPct = (v / max) * 100
        const isToday = i === 0
        return (
          <div key={i} className="flex flex-1 flex-col items-center gap-1">
            <div className="relative w-full flex-1 flex items-end">
              <div
                className="w-full rounded-t-sm transition-all duration-300"
                style={{
                  height: `${Math.max(heightPct, 4)}%`,
                  background: isToday ? accentColor : `${accentColor}55`,
                  boxShadow: isToday ? `0 0 6px ${accentColor}80` : undefined,
                }}
              />
            </div>
            <span className="text-[9px] text-muted-foreground/70 leading-none">{labels[i]}</span>
          </div>
        )
      })}
    </div>
  )
}

/** SVG semicircular gauge — uses pathLength="1" trick for clean fill */
function ArcGauge({
  value,
  max,
  color,
  trackColor = "#1e293b",
}: {
  value: number
  max: number
  color: string
  trackColor?: string
}) {
  const pct  = Math.min(value / max, 1)
  const r    = 68
  const cx   = 100
  const cy   = 88
  const arc  = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`

  return (
    <svg viewBox="0 0 200 96" fill="none" aria-hidden className="w-full">
      {/* Track */}
      <path
        d={arc}
        stroke={trackColor}
        strokeWidth="10"
        strokeLinecap="round"
      />
      {/* Fill — pathLength normalises the half-circle to 1 */}
      <path
        d={arc}
        stroke={color}
        strokeWidth="10"
        strokeLinecap="round"
        pathLength="1"
        strokeDasharray={`${pct} 1`}
        style={{ filter: `drop-shadow(0 0 6px ${color}60)` }}
      />
      {/* Tick labels */}
      <text x={cx - r - 2} y={cy + 16} fill="#64748b" fontSize="9" fontFamily="inherit">0</text>
      <text x={cx + r + 2} y={cy + 16} fill="#64748b" fontSize="9" fontFamily="inherit" textAnchor="end">{max}</text>
    </svg>
  )
}

/** Card shell with colored top accent bar */
function KpiCard({
  accent,
  children,
  className = "",
}: {
  accent: string    // CSS color string for the 2px top bar
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={`group relative flex flex-col overflow-hidden rounded-2xl border border-border bg-card transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20 ${className}`}
      style={{ borderTop: `2px solid ${accent}` }}
    >
      {/* Subtle inner glow matching accent */}
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-24 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: `radial-gradient(ellipse 80% 60% at 50% 0%, ${accent}14 0%, transparent 70%)` }}
        aria-hidden
      />
      <div className="relative flex flex-1 flex-col gap-0 p-5">{children}</div>
    </div>
  )
}

/** Live pulse indicator */
function LiveDot() {
  return (
    <span className="relative flex size-2 shrink-0" aria-label="Live data">
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-climate-emerald opacity-60" />
      <span className="relative inline-flex size-2 rounded-full bg-climate-emerald" />
    </span>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   1. TEMPERATURE CARD
═══════════════════════════════════════════════════════════════════════════ */
function TemperatureCard() {
  const current   = WEEKLY_FORECAST[0].tempMax        // 34.0
  const anomaly   = +1.2                               // +1.2°C vs 30-yr mean
  const weekMin   = Math.min(...TEMPS_7D)              // 30.2
  const weekMax   = Math.max(...TEMPS_7D)              // 37.1
  const ACCENT    = "oklch(0.82 0.165 68)"             // amber

  return (
    <KpiCard accent={ACCENT}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-climate-amber/15">
            <Thermometer className="size-3.5 text-climate-amber" aria-hidden />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Temperature
          </span>
        </div>
        <LiveDot />
      </div>

      {/* Hero value */}
      <div className="flex items-end gap-3 mb-1">
        <span
          className="font-heading text-4xl font-black tabular-nums leading-none text-foreground"
          aria-label={`${current} degrees Celsius`}
        >
          {current.toFixed(1)}
        </span>
        <span className="mb-1 text-sm font-medium text-muted-foreground">°C</span>
        {/* Anomaly badge */}
        <div className="mb-1 ml-auto flex items-center gap-1 rounded-full border border-climate-rose/30 bg-climate-rose/10 px-2 py-0.5 text-[11px] font-bold text-climate-rose">
          <TrendingUp className="size-3" aria-hidden />
          +{anomaly}° anomaly
        </div>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">Land surface temperature · India avg</p>

      {/* 7-day sparkline */}
      <div className="mb-2">
        <Sparkline
          values={TEMPS_7D}
          stroke="oklch(0.82 0.165 68)"
          fill="oklch(0.82 0.165 68)"
        />
      </div>

      {/* Week range footer */}
      <div className="flex items-center justify-between rounded-lg bg-secondary/40 px-3 py-2 text-xs">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <TrendingDown className="size-3 text-climate-sky" aria-hidden />
          Low <span className="font-bold text-foreground">{weekMin}°C</span>
        </div>
        <div className="h-px flex-1 mx-3 bg-border/60" aria-hidden />
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <TrendingUp className="size-3 text-climate-rose" aria-hidden />
          High <span className="font-bold text-foreground">{weekMax}°C</span>
        </div>
      </div>
    </KpiCard>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   2. RAINFALL CARD
═══════════════════════════════════════════════════════════════════════════ */
function RainfallCard() {
  const cumulative  = 750       // mm this season
  const normal      = 850       // mm normal
  const deviation   = Math.round(((cumulative - normal) / normal) * 100) // -12
  const deficit     = deviation < 0
  const ACCENT      = "oklch(0.68 0.150 188)"   // teal

  return (
    <KpiCard accent={ACCENT}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-climate-teal/15">
            <Droplets className="size-3.5 text-climate-teal" aria-hidden />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Rainfall
          </span>
        </div>
        <LiveDot />
      </div>

      {/* Hero value */}
      <div className="flex items-end gap-3 mb-1">
        <span
          className="font-heading text-4xl font-black tabular-nums leading-none text-foreground"
          aria-label={`${cumulative} millimetres`}
        >
          {cumulative}
        </span>
        <span className="mb-1 text-sm font-medium text-muted-foreground">mm</span>
        {/* Deviation badge */}
        <div
          className={`mb-1 ml-auto flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-bold ${
            deficit
              ? "border-climate-rose/30 bg-climate-rose/10 text-climate-rose"
              : "border-climate-emerald/30 bg-climate-emerald/10 text-climate-emerald"
          }`}
        >
          {deficit ? <TrendingDown className="size-3" /> : <TrendingUp className="size-3" />}
          {deviation > 0 ? "+" : ""}{deviation}% from normal
        </div>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">Season cumulative · Normal {normal} mm</p>

      {/* 7-day bar chart */}
      <div className="mb-2 flex-1">
        <MiniBarChart
          values={RAINS_7D}
          labels={DAYS_7D}
          accentColor="oklch(0.68 0.150 188)"
        />
      </div>

      {/* Summary footer */}
      <div className="flex items-center justify-between rounded-lg bg-secondary/40 px-3 py-2 text-xs">
        <div className="text-muted-foreground">
          7-day total <span className="font-bold text-foreground">{RAINS_7D.reduce((a, b) => a + b, 0)} mm</span>
        </div>
        <div className="text-muted-foreground">
          Rain days <span className="font-bold text-foreground">{RAINS_7D.filter((r) => r > 0).length} / 7</span>
        </div>
      </div>
    </KpiCard>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   3. AQI CARD
═══════════════════════════════════════════════════════════════════════════ */
const AQI_RANGES = [
  { max:  50, label: "Good",                 color: "oklch(0.72 0.185 162)", cls: "text-climate-emerald", bg: "bg-climate-emerald/10 border-climate-emerald/30" },
  { max: 100, label: "Moderate",             color: "oklch(0.85 0.18  85)",  cls: "text-yellow-400",      bg: "bg-yellow-400/10 border-yellow-400/30"            },
  { max: 150, label: "Unhealthy (Sensitive)",color: "oklch(0.82 0.165  68)", cls: "text-climate-amber",   bg: "bg-climate-amber/10 border-climate-amber/30"      },
  { max: 200, label: "Unhealthy",            color: "oklch(0.72 0.20   45)", cls: "text-orange-400",      bg: "bg-orange-400/10 border-orange-400/30"            },
  { max: 300, label: "Very Unhealthy",       color: "oklch(0.65 0.20   18)", cls: "text-climate-rose",    bg: "bg-climate-rose/10 border-climate-rose/30"        },
  { max: 500, label: "Hazardous",            color: "oklch(0.50 0.22   18)", cls: "text-red-600",         bg: "bg-red-600/10 border-red-600/30"                  },
]

function getAqiRange(aqi: number) {
  return AQI_RANGES.find((r) => aqi <= r.max) ?? AQI_RANGES[AQI_RANGES.length - 1]
}

function AqiCard() {
  const aqi    = 110
  const range  = getAqiRange(aqi)
  const ACCENT = range.color

  return (
    <KpiCard accent={ACCENT}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg" style={{ background: `${ACCENT}22` }}>
            <Wind className="size-3.5" style={{ color: ACCENT }} aria-hidden />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Air Quality Index
          </span>
        </div>
        <LiveDot />
      </div>

      {/* Gauge + value overlay */}
      <div className="relative -mx-1 -mb-1">
        <ArcGauge value={aqi} max={300} color={ACCENT} />
        {/* Central overlay value */}
        <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ paddingBottom: "10%" }}>
          <span
            className="font-heading text-3xl font-black tabular-nums leading-none"
            style={{ color: ACCENT }}
            aria-label={`AQI ${aqi}`}
          >
            {aqi}
          </span>
          <span className="text-[10px] text-muted-foreground mt-0.5">AQI</span>
        </div>
      </div>

      {/* Level badge + color scale */}
      <div className="mt-1 flex flex-col gap-2">
        <div className={`flex items-center justify-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-bold ${range.bg} ${range.cls}`}>
          {aqi <= 100 ? <Minus className="size-3" /> : <TrendingUp className="size-3" />}
          {range.label}
        </div>
        {/* Color scale bar */}
        <div className="flex h-1.5 w-full overflow-hidden rounded-full" aria-hidden>
          {AQI_RANGES.map((r) => (
            <div
              key={r.label}
              className="flex-1 first:rounded-l-full last:rounded-r-full"
              style={{ background: r.color }}
            />
          ))}
        </div>
        <div className="flex justify-between text-[9px] text-muted-foreground/70">
          <span>Good</span>
          <span>Hazardous</span>
        </div>
      </div>
    </KpiCard>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   4. DROUGHT RISK CARD
═══════════════════════════════════════════════════════════════════════════ */
const DROUGHT_SEGMENTS = [
  { label: "Normal",   max: 1, color: "bg-climate-emerald" },
  { label: "Mild",     max: 2, color: "bg-yellow-400"      },
  { label: "Moderate", max: 3, color: "bg-climate-amber"   },
  { label: "Severe",   max: 4, color: "bg-orange-400"      },
  { label: "Extreme",  max: 5, color: "bg-climate-rose"    },
]

function getDroughtSeverity(dri: number) {
  return DROUGHT_SEGMENTS.find((s) => dri < s.max) ?? DROUGHT_SEGMENTS[DROUGHT_SEGMENTS.length - 1]
}

function DroughtRiskCard() {
  const dri        = 1.8     // Palmer Drought Severity Index
  const severity   = getDroughtSeverity(dri)
  const pctOnScale = (dri / 5) * 100
  const ACCENT     = "oklch(0.82 0.165 68)"   // amber

  const factors = [
    { label: "Soil Moisture", value: "34%",   icon: Droplets,    warn: true  },
    { label: "NDVI",          value: "0.42",  icon: TrendingDown,warn: false },
    { label: "Rain Deficit",  value: "−12%",  icon: Droplets,    warn: true  },
  ]

  return (
    <KpiCard accent={ACCENT}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-climate-amber/15">
            <Flame className="size-3.5 text-climate-amber" aria-hidden />
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Drought Risk
          </span>
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
          Palmer DRI
        </span>
      </div>

      {/* Hero value + severity */}
      <div className="flex items-center gap-3 mb-1">
        <span
          className="font-heading text-4xl font-black tabular-nums leading-none text-foreground"
          aria-label={`Drought risk index ${dri}`}
        >
          {dri.toFixed(1)}
        </span>
        <div className="flex flex-col">
          <span className="text-xs text-muted-foreground">/ 5.0</span>
        </div>
        <div className="ml-auto flex items-center gap-1.5 rounded-full border border-climate-amber/30 bg-climate-amber/10 px-2.5 py-1 text-xs font-bold text-climate-amber">
          {severity.label}
        </div>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">India aggregate · Kharif season 2025</p>

      {/* Segment scale */}
      <div className="mb-1.5 flex gap-0.5 overflow-hidden rounded-full" style={{ height: 6 }} aria-hidden>
        {DROUGHT_SEGMENTS.map((seg) => (
          <div key={seg.label} className={`flex-1 ${seg.color} opacity-30`} />
        ))}
      </div>
      {/* Marker */}
      <div className="relative mb-1 h-3" aria-hidden>
        <div
          className="absolute top-0 size-3 rounded-full border-2 border-background bg-climate-amber shadow-md shadow-climate-amber/40"
          style={{ left: `calc(${pctOnScale}% - 6px)` }}
        />
      </div>
      <div className="mb-3 flex justify-between text-[9px] text-muted-foreground/60">
        {DROUGHT_SEGMENTS.map((s) => <span key={s.label}>{s.label}</span>)}
      </div>

      {/* Contributing factors */}
      <div className="flex flex-col gap-1.5 rounded-lg bg-secondary/40 px-3 py-2">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mb-1">
          Drivers
        </p>
        {factors.map(({ label, value, icon: Icon, warn }) => (
          <div key={label} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Icon className={`size-3 ${warn ? "text-climate-amber" : "text-muted-foreground"}`} aria-hidden />
              {label}
            </div>
            <span className={`font-bold tabular-nums ${warn ? "text-climate-amber" : "text-foreground"}`}>
              {value}
            </span>
          </div>
        ))}
      </div>
    </KpiCard>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   EXPORT — 4-card responsive grid
═══════════════════════════════════════════════════════════════════════════ */
/**
 * ClimateKpiCards
 *
 * Drop-in 4-card KPI row for the dashboard.
 * Data sourced from `@/mock` — swap for real API later.
 *
 * @example
 * <ClimateKpiCards />
 */
export function ClimateKpiCards() {
  return (
    <section
      aria-label="Key climate performance indicators"
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
    >
      <TemperatureCard />
      <RainfallCard />
      <AqiCard />
      <DroughtRiskCard />
    </section>
  )
}

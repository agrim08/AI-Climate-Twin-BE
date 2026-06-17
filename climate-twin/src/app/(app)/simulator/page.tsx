import { PageHeader } from "@/components/PageHeader"
import { Card } from "@/components/Card"
import { StatCard } from "@/components/StatCard"
import { SectionHeading } from "@/components/SectionHeading"
import { Button } from "@/components/Button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  FlaskConical,
  Play,
  Square,
  RotateCcw,
  Sliders,
  Clock,
  TrendingUp,
  Thermometer,
  Droplets,
  Wind,
  Leaf,
  ChevronRight,
  Info,
} from "lucide-react"

/* ── Scenario presets ──────────────────────────────────────────────────── */
const SCENARIOS = [
  {
    id: "baseline",
    label: "2025 Baseline",
    desc: "Current observed conditions",
    badge: "Active",
    badgeColor: "bg-climate-emerald/15 text-climate-emerald border-climate-emerald/30",
  },
  {
    id: "rcp45",
    label: "RCP 4.5 — Moderate",
    desc: "+2°C by 2050, moderate mitigation",
    badge: "Preset",
    badgeColor: "bg-climate-teal/15 text-climate-teal border-climate-teal/30",
  },
  {
    id: "rcp85",
    label: "RCP 8.5 — Severe",
    desc: "+4°C by 2080, no mitigation",
    badge: "Preset",
    badgeColor: "bg-climate-rose/15 text-climate-rose border-climate-rose/30",
  },
  {
    id: "custom",
    label: "Custom Scenario",
    desc: "Define your own parameters",
    badge: "Custom",
    badgeColor: "bg-climate-amber/15 text-climate-amber border-climate-amber/30",
  },
]

/* ── Parameter sliders (mock) ──────────────────────────────────────────── */
const PARAMETERS = [
  { label: "CO₂ Emissions",      icon: Wind,        unit: "GtC/yr", value: 10.2, min: 0,   max: 20,  step: 0.1, color: "accent-climate-rose"    },
  { label: "Global Temp. Delta", icon: Thermometer, unit: "°C",     value: 1.3,  min: -2,  max: 6,   step: 0.1, color: "accent-climate-amber"   },
  { label: "Deforestation Rate", icon: Leaf,        unit: "Mha/yr", value: 5.4,  min: 0,   max: 15,  step: 0.1, color: "accent-climate-teal"    },
  { label: "Monsoon Variation",  icon: Droplets,    unit: "%",      value: -8,   min: -50, max: 50,  step: 1,   color: "accent-climate-cyan"    },
]

/* ── Simulation output stats ───────────────────────────────────────────── */
const OUTPUT_STATS = [
  { label: "Projected NDVI 2030",  value: "0.51",  unit: "index",  change: "-19%",   trend: "down" as const, upTrendIsGood: true,  accent: "emerald" as const },
  { label: "Temp Anomaly 2030",    value: "+2.1",  unit: "°C",     change: "+0.8°C", trend: "up"   as const, upTrendIsGood: false, accent: "amber"   as const },
  { label: "Drought Risk Index",   value: "0.72",  unit: "DRI",    change: "+28%",   trend: "up"   as const, upTrendIsGood: false, accent: "rose"    as const },
  { label: "Crop Yield Impact",    value: "−18",   unit: "%",      change: "−18%",   trend: "down" as const, upTrendIsGood: true,  accent: "teal"    as const },
]

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function SimulatorPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span>Climate <span className="text-gradient-climate">Simulator</span></span>}
        subtitle="Run predictive climate models · Adjust parameters · Compare scenarios"
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Simulator" }]}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" leftIcon={<RotateCcw className="size-3.5" />}>Reset</Button>
            <Button variant="secondary" size="sm" leftIcon={<Square className="size-3.5" />}>Stop</Button>
            <Button appVariant="glow" leftIcon={<Play className="size-3.5" />}>Run Simulation</Button>
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        {/* ── Left: Scenario + Parameters ──────────────────────────── */}
        <div className="flex flex-col gap-4">
          {/* Scenario selector */}
          <Card title={<SectionHeading title="Scenario" subtitle="Choose a climate pathway" accent="bar" />}>
            <div className="flex flex-col gap-2">
              {SCENARIOS.map((s) => (
                <label
                  key={s.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border px-3 py-2.5 transition-colors ${
                    s.id === "baseline"
                      ? "border-primary/30 bg-primary/10"
                      : "border-border bg-secondary/30 hover:bg-secondary/60"
                  }`}
                >
                  <input type="radio" name="scenario" defaultChecked={s.id === "baseline"} className="mt-1 accent-primary shrink-0" />
                  <div className="flex flex-1 min-w-0 flex-col gap-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold text-foreground">{s.label}</span>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-bold ${s.badgeColor}`}>
                        {s.badge}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">{s.desc}</span>
                  </div>
                </label>
              ))}
            </div>
          </Card>

          {/* Parameters */}
          <Card title={<SectionHeading title="Parameters" subtitle="Drag to adjust inputs" accent="bar" actions={<Sliders className="size-4 text-muted-foreground" />} />}>
            <div className="flex flex-col gap-4">
              {PARAMETERS.map(({ label, icon: Icon, unit, value, min, max, step }) => (
                <div key={label} className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                      <Icon className="size-3.5 text-muted-foreground" aria-hidden />
                      {label}
                    </div>
                    <span className="text-sm font-bold text-primary tabular-nums">
                      {value > 0 && min < 0 ? "+" : ""}{value} <span className="text-xs font-normal text-muted-foreground">{unit}</span>
                    </span>
                  </div>
                  <input
                    type="range"
                    min={min}
                    max={max}
                    step={step}
                    defaultValue={value}
                    className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-secondary accent-primary"
                    aria-label={label}
                  />
                  <div className="flex justify-between text-[10px] text-muted-foreground">
                    <span>{min}{unit}</span>
                    <span>{max}{unit}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* ── Right: Output area ───────────────────────────────────── */}
        <div className="flex flex-col gap-4 lg:col-span-2">
          {/* Status bar */}
          <div className="flex items-center gap-3 rounded-xl border border-climate-emerald/20 bg-climate-emerald/5 px-4 py-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-climate-emerald/15">
              <FlaskConical className="size-4 text-climate-emerald" />
            </div>
            <div className="flex flex-1 min-w-0 flex-col">
              <span className="text-sm font-semibold text-foreground">Simulation Ready</span>
              <span className="text-xs text-muted-foreground">2025–2050 · India subcontinent · 5km resolution</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="size-3.5" aria-hidden />
              ~3 min
            </div>
          </div>

          {/* Output stats */}
          <div className="grid gap-3 sm:grid-cols-2">
            {OUTPUT_STATS.map((s) => <StatCard key={s.label} {...s} />)}
          </div>

          {/* Output tabs */}
          <Card>
            <Tabs defaultValue="projection">
              <TabsList className="w-full">
                <TabsTrigger value="projection" className="flex-1">Projection Chart</TabsTrigger>
                <TabsTrigger value="comparison" className="flex-1">Scenario Compare</TabsTrigger>
                <TabsTrigger value="map"        className="flex-1">Spatial Output</TabsTrigger>
              </TabsList>

              {["projection","comparison","map"].map((tab) => (
                <TabsContent key={tab} value={tab}>
                  <div className="flex h-48 items-center justify-center rounded-lg border border-dashed border-border bg-secondary/20">
                    <div className="flex flex-col items-center gap-2 text-center">
                      <TrendingUp className="size-8 text-muted-foreground/40" />
                      <p className="text-sm text-muted-foreground capitalize">
                        {tab === "projection" ? "Recharts time-series goes here" :
                         tab === "comparison" ? "Multi-scenario comparison chart" :
                         "Spatial heatmap output"}
                      </p>
                    </div>
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </Card>

          {/* Info note */}
          <div className="flex items-start gap-2 rounded-lg border border-border bg-secondary/30 px-3 py-2.5 text-xs text-muted-foreground">
            <Info className="mt-0.5 size-3.5 shrink-0 text-climate-sky" aria-hidden />
            Model based on CMIP6 ensemble. Results are probabilistic projections, not forecasts.
          </div>
        </div>
      </div>
    </div>
  )
}

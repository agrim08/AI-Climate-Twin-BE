import { PageHeader } from "@/components/PageHeader"
import { Card, CardContent } from "@/components/Card"
import { StatCard } from "@/components/StatCard"
import { SectionHeading } from "@/components/SectionHeading"
import { Button } from "@/components/Button"
import { Badge } from "@/components/ui/badge"
import {
  Globe2,
  Layers,
  Thermometer,
  Droplets,
  Wind,
  Leaf,
  ZoomIn,
  ZoomOut,
  Locate,
  Satellite,
  Download,
} from "lucide-react"

/* ── Layer controls ────────────────────────────────────────────────────── */
const LAYERS = [
  { id: "ndvi",    label: "NDVI",         color: "bg-climate-emerald", active: true  },
  { id: "temp",    label: "Temperature",  color: "bg-climate-amber",   active: true  },
  { id: "precip",  label: "Precipitation",color: "bg-climate-cyan",    active: false },
  { id: "co2",     label: "CO₂ Flux",     color: "bg-climate-rose",    active: false },
  { id: "soil",    label: "Soil Moisture",color: "bg-climate-teal",    active: false },
]

const REGION_STATS = [
  { label: "Avg. NDVI",       value: "0.63",  unit: "index",  change: "+2.1%", trend: "up" as const, upTrendIsGood: true,  accent: "emerald" as const },
  { label: "Land Surface Temp",value: "34.2", unit: "°C",     change: "+1.4%", trend: "up" as const, upTrendIsGood: false, accent: "amber"   as const },
  { label: "Rainfall Anomaly", value: "-12",  unit: "%",      change: "-12%",  trend: "down" as const, upTrendIsGood: true, accent: "teal"   as const },
  { label: "Carbon Flux",      value: "2.14", unit: "GtC/yr", change: "+0.3%", trend: "up" as const, upTrendIsGood: false, accent: "rose"   as const },
]

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function ClimateTwinPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span>Climate <span className="text-gradient-climate">Twin</span></span>}
        subtitle="Satellite-derived digital earth model · India subcontinent · June 2025"
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Climate Twin" }]}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" leftIcon={<Download className="size-3.5" />}>
              Export GeoTIFF
            </Button>
            <Button appVariant="glow" leftIcon={<Satellite className="size-3.5" />} size="sm">
              Live Feed
            </Button>
          </div>
        }
      />

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {REGION_STATS.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      {/* Main area — map + controls */}
      <div className="grid gap-4 lg:grid-cols-4">
        {/* Map canvas */}
        <div className="lg:col-span-3">
          <div className="relative overflow-hidden rounded-xl border border-border bg-card" style={{ minHeight: 480 }}>
            {/* Map placeholder background */}
            <div
              className="absolute inset-0"
              style={{
                background: `
                  radial-gradient(ellipse 60% 40% at 40% 55%, oklch(0.22 0.08 162 / 40%) 0%, transparent 60%),
                  radial-gradient(ellipse 40% 30% at 70% 30%, oklch(0.20 0.06 210 / 30%) 0%, transparent 55%),
                  radial-gradient(ellipse 50% 60% at 20% 70%, oklch(0.18 0.05 188 / 25%) 0%, transparent 60%),
                  oklch(0.10 0.02 245)
                `,
              }}
            />

            {/* Grid overlay */}
            <div
              className="absolute inset-0 opacity-10"
              style={{
                backgroundImage: "linear-gradient(oklch(0.5 0.05 210) 1px, transparent 1px), linear-gradient(90deg, oklch(0.5 0.05 210) 1px, transparent 1px)",
                backgroundSize: "40px 40px",
              }}
            />

            {/* India outline SVG hint */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="flex flex-col items-center gap-3 text-center">
                <Globe2 className="size-16 text-climate-emerald/30" />
                <p className="text-sm text-muted-foreground">
                  Mapbox GL map renders here
                </p>
                <code className="rounded bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                  import mapboxgl from &apos;mapbox-gl&apos;
                </code>
              </div>
            </div>

            {/* Map toolbar */}
            <div className="absolute right-3 top-3 flex flex-col gap-1">
              {[
                { icon: ZoomIn,  label: "Zoom in"  },
                { icon: ZoomOut, label: "Zoom out" },
                { icon: Locate,  label: "My location" },
              ].map(({ icon: Icon, label }) => (
                <button
                  key={label}
                  aria-label={label}
                  className="flex size-8 items-center justify-center rounded-lg border border-border bg-card/90 text-muted-foreground shadow-sm backdrop-blur-sm transition-colors hover:bg-secondary hover:text-foreground"
                >
                  <Icon className="size-4" aria-hidden />
                </button>
              ))}
            </div>

            {/* Legend */}
            <div className="absolute bottom-3 left-3 glass-panel rounded-lg px-3 py-2">
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">NDVI Legend</p>
              <div className="flex items-center gap-1">
                {["bg-climate-rose","bg-climate-amber","bg-yellow-500","bg-climate-teal","bg-climate-emerald"].map((c, i) => (
                  <div key={i} className={`h-3 w-7 rounded-sm ${c} opacity-80`} />
                ))}
              </div>
              <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                <span>−1</span><span>0</span><span>+1</span>
              </div>
            </div>

            {/* Coordinates overlay */}
            <div className="absolute bottom-3 right-3 glass-panel rounded-lg px-3 py-1.5 text-[11px] text-muted-foreground font-mono">
              20.5937°N &nbsp;78.9629°E
            </div>
          </div>
        </div>

        {/* Layer controls panel */}
        <div className="flex flex-col gap-4">
          <Card title={<SectionHeading title="Layers" accent="dot" />}>
            <div className="flex flex-col gap-2">
              {LAYERS.map((layer) => (
                <label
                  key={layer.id}
                  className="flex cursor-pointer items-center gap-3 rounded-lg border border-border bg-secondary/40 px-3 py-2.5 transition-colors hover:bg-secondary"
                >
                  <input
                    type="checkbox"
                    defaultChecked={layer.active}
                    className="sr-only"
                    id={`layer-${layer.id}`}
                  />
                  <div className={`size-3 shrink-0 rounded-sm ${layer.color} ${layer.active ? "opacity-100" : "opacity-30"}`} aria-hidden />
                  <span className="flex-1 text-sm font-medium text-foreground">{layer.label}</span>
                  {layer.active && (
                    <span className="text-[10px] text-climate-emerald font-semibold">ON</span>
                  )}
                </label>
              ))}
            </div>
          </Card>

          <Card title={<SectionHeading title="Data Source" accent="dot" />}>
            <div className="flex flex-col gap-2 text-xs text-muted-foreground">
              {[
                { label: "Satellite",   value: "RESOURCESAT-2A" },
                { label: "Resolution",  value: "5.8m / pixel"   },
                { label: "Date",        value: "Jun 15, 2025"   },
                { label: "Projection",  value: "WGS84 / EPSG:4326" },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between gap-2 border-b border-border/50 pb-1.5 last:border-0 last:pb-0">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="font-medium text-foreground">{value}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

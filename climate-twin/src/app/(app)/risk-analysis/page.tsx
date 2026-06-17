import { PageHeader } from "@/components/PageHeader"
import { Card } from "@/components/Card"
import { StatCard } from "@/components/StatCard"
import { SectionHeading } from "@/components/SectionHeading"
import { Button } from "@/components/Button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ShieldAlert,
  AlertTriangle,
  TrendingUp,
  MapPin,
  Thermometer,
  Droplets,
  Wind,
  Flame,
  Waves,
  Skull,
  Download,
  Filter,
  RefreshCw,
} from "lucide-react"

/* ── Risk summary stats ────────────────────────────────────────────────── */
const RISK_STATS = [
  { label: "Critical Risk Zones",  value: "7",    unit: "regions", change: "+2",    trend: "up"   as const, upTrendIsGood: false, accent: "rose"    as const, icon: <Skull className="size-4" />        },
  { label: "Extreme Heat Events",  value: "18",   unit: "alerts",  change: "+5",    trend: "up"   as const, upTrendIsGood: false, accent: "amber"   as const, icon: <Flame className="size-4" />        },
  { label: "Flood Risk Index",     value: "0.64", unit: "FRI",     change: "+0.12", trend: "up"   as const, upTrendIsGood: false, accent: "teal"    as const, icon: <Waves className="size-4" />        },
  { label: "Regions Monitored",    value: "642",  unit: "districts",change: "Live", trend: "neutral" as const, upTrendIsGood: true, accent: "emerald" as const, icon: <MapPin className="size-4" />     },
]

/* ── Active risk events ────────────────────────────────────────────────── */
const RISK_EVENTS = [
  {
    id: 1,
    region: "Rajasthan",
    subregion: "Barmer, Jaisalmer, Bikaner",
    type: "Extreme Heat Wave",
    icon: Flame,
    severity: "Critical",
    riskScore: 0.91,
    affectedPop: "4.2M",
    forecast: "72h sustained >45°C",
    color: "border-l-climate-rose",
    badgeColor: "bg-climate-rose/15 text-climate-rose border-climate-rose/30",
  },
  {
    id: 2,
    region: "Assam",
    subregion: "Kaziranga, Majuli, Dibrugarh",
    type: "Flash Flood Risk",
    icon: Waves,
    severity: "High",
    riskScore: 0.82,
    affectedPop: "2.8M",
    forecast: "River breach probability 78%",
    color: "border-l-climate-teal",
    badgeColor: "bg-climate-teal/15 text-climate-teal border-climate-teal/30",
  },
  {
    id: 3,
    region: "Vidarbha",
    subregion: "Yavatmal, Wardha, Amravati",
    type: "Agricultural Drought",
    icon: AlertTriangle,
    severity: "High",
    riskScore: 0.77,
    affectedPop: "3.1M",
    forecast: "Kharif crop loss est. −25%",
    color: "border-l-climate-amber",
    badgeColor: "bg-climate-amber/15 text-climate-amber border-climate-amber/30",
  },
  {
    id: 4,
    region: "Tamil Nadu Coast",
    subregion: "Chennai, Cuddalore, Nagapattinam",
    type: "Cyclone Watch",
    icon: Wind,
    severity: "Moderate",
    riskScore: 0.61,
    affectedPop: "5.6M",
    forecast: "Category 1–2 landfall probability 45%",
    color: "border-l-climate-sky",
    badgeColor: "bg-climate-sky/15 text-climate-sky border-climate-sky/30",
  },
  {
    id: 5,
    region: "Himachal Pradesh",
    subregion: "Kullu, Manali, Chamba",
    type: "Glacial Lake Outburst",
    icon: Droplets,
    severity: "Warning",
    riskScore: 0.49,
    affectedPop: "0.3M",
    forecast: "GLOF risk elevated post melt",
    color: "border-l-climate-cyan",
    badgeColor: "bg-climate-cyan/15 text-climate-cyan border-climate-cyan/30",
  },
]

/* ── Risk score bar ────────────────────────────────────────────────────── */
function RiskBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    pct >= 80 ? "bg-climate-rose" :
    pct >= 60 ? "bg-climate-amber" :
    "bg-climate-teal"

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-secondary">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="tabular-nums text-xs font-bold text-foreground">{pct}</span>
    </div>
  )
}

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function RiskAnalysisPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span>Risk <span className="text-gradient-climate">Analysis</span></span>}
        subtitle="AI-powered climate risk scoring · 642 districts monitored in real-time"
        breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Risk Analysis" }]}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" leftIcon={<Filter className="size-3.5" />}>Filter</Button>
            <Button variant="outline" size="sm" leftIcon={<Download className="size-3.5" />}>Export PDF</Button>
            <Button appVariant="glow" leftIcon={<RefreshCw className="size-3.5" />} size="sm">Refresh</Button>
          </div>
        }
      />

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {RISK_STATS.map((s) => <StatCard key={s.label} {...s} />)}
      </div>

      <Tabs defaultValue="events">
        <TabsList>
          <TabsTrigger value="events">Active Events</TabsTrigger>
          <TabsTrigger value="heatmap">Risk Heatmap</TabsTrigger>
          <TabsTrigger value="forecast">7-Day Forecast</TabsTrigger>
          <TabsTrigger value="history">Historical</TabsTrigger>
        </TabsList>

        {/* ── Active events ─────────────────────────────────────── */}
        <TabsContent value="events" className="mt-4">
          <div className="grid gap-4 lg:grid-cols-3">
            {/* Events list */}
            <div className="flex flex-col gap-3 lg:col-span-2">
              <SectionHeading
                title="Active Climate Risk Events"
                subtitle="Sorted by risk severity · Updated 4 min ago"
                accent="bar"
                actions={
                  <Badge className="border border-climate-rose/30 bg-climate-rose/10 text-climate-rose">
                    {RISK_EVENTS.length} Active
                  </Badge>
                }
              />

              {RISK_EVENTS.map((event) => {
                const Icon = event.icon
                return (
                  <div
                    key={event.id}
                    className={`relative overflow-hidden rounded-xl border border-border border-l-4 ${event.color} bg-card transition-shadow hover:shadow-md dark:hover:shadow-black/30`}
                  >
                    <div className="flex items-start gap-4 p-4">
                      <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-secondary">
                        <Icon className="size-4 text-muted-foreground" aria-hidden />
                      </div>

                      <div className="flex flex-1 min-w-0 flex-col gap-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-foreground">{event.region}</span>
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${event.badgeColor}`}
                          >
                            {event.severity}
                          </span>
                          <span className="text-sm font-medium text-muted-foreground">{event.type}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">{event.subregion}</p>
                        <p className="text-xs text-foreground/80 mt-0.5">⚠ {event.forecast}</p>
                      </div>

                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <RiskBar score={event.riskScore} />
                        <span className="text-xs text-muted-foreground">
                          Pop: <b className="text-foreground">{event.affectedPop}</b>
                        </span>
                        <Button variant="ghost" size="xs">Details →</Button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Summary panel */}
            <div className="flex flex-col gap-4">
              <Card title={<SectionHeading title="Risk Distribution" accent="dot" />}>
                {[
                  { label: "Critical (>80)",  count: 2,  color: "bg-climate-rose",  pct: "28%" },
                  { label: "High (60–80)",     count: 3,  color: "bg-climate-amber", pct: "42%" },
                  { label: "Moderate (40–60)", count: 5,  color: "bg-climate-teal",  pct: "20%" },
                  { label: "Watch (<40)",      count: 8,  color: "bg-secondary",     pct: "10%" },
                ].map(({ label, count, color, pct }) => (
                  <div key={label} className="flex items-center gap-3 py-2 border-b border-border/50 last:border-0">
                    <div className={`size-2.5 shrink-0 rounded-full ${color}`} aria-hidden />
                    <span className="flex-1 text-xs text-muted-foreground">{label}</span>
                    <span className="text-xs font-bold text-foreground tabular-nums">{count}</span>
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-secondary">
                      <div className={`h-full ${color} rounded-full`} style={{ width: pct }} />
                    </div>
                  </div>
                ))}
              </Card>

              <Card title={<SectionHeading title="Risk Drivers" accent="dot" />}>
                {[
                  { label: "Temperature anomaly", icon: Thermometer, weight: "High"   },
                  { label: "Precipitation deficit", icon: Droplets, weight: "High"    },
                  { label: "NDVI decline",          icon: TrendingUp, weight: "Medium" },
                  { label: "Soil moisture loss",    icon: Wind, weight: "Medium"       },
                ].map(({ label, icon: Icon, weight }) => (
                  <div key={label} className="flex items-center gap-2 py-2 border-b border-border/50 last:border-0 text-xs">
                    <Icon className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
                    <span className="flex-1 text-muted-foreground">{label}</span>
                    <span className={`font-semibold ${weight === "High" ? "text-climate-rose" : "text-climate-amber"}`}>
                      {weight}
                    </span>
                  </div>
                ))}
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* ── Placeholder tabs ──────────────────────────────────── */}
        {["heatmap","forecast","history"].map((tab) => (
          <TabsContent key={tab} value={tab} className="mt-4">
            <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-border bg-card">
              <div className="flex flex-col items-center gap-2 text-center">
                <ShieldAlert className="size-10 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground capitalize">
                  {tab === "heatmap"  ? "District-level risk heatmap (Mapbox GL)"  :
                   tab === "forecast" ? "7-day probabilistic risk forecast chart"   :
                   "Historical risk trend and event archive"}
                </p>
              </div>
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}

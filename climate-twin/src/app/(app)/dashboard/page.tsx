import { PageHeader } from "@/components/PageHeader"
import { SectionHeading } from "@/components/SectionHeading"
import { Card } from "@/components/Card"
import { Button } from "@/components/Button"
import { Badge } from "@/components/ui/badge"
import { ClimateKpiCards } from "@/features/kpi/ClimateKpiCards"
import { ClimateTrendCharts } from "@/features/charts/ClimateTrendCharts"
import {
  Satellite,
  AlertTriangle,
  ArrowRight,
  Activity,
} from "lucide-react"


const ALERTS = [
  { id: 1, region: "Rajasthan", type: "Heat Wave",       severity: "Critical", time: "2h ago"  },
  { id: 2, region: "Kerala",    type: "Excess Rainfall", severity: "Moderate", time: "5h ago"  },
  { id: 3, region: "Punjab",    type: "Drought Risk",    severity: "Warning",  time: "12h ago" },
]

const severityStyle: Record<string, string> = {
  Critical: "bg-climate-rose/15 text-climate-rose border-climate-rose/30",
  Moderate: "bg-climate-amber/15 text-climate-amber border-climate-amber/30",
  Warning:  "bg-climate-teal/15 text-climate-teal border-climate-teal/30",
}

const SATELLITES = [
  { name: "Cartosat-3",      status: "Active", pass: "14 min",  swath: "16 km"  },
  { name: "RESOURCESAT-2A",  status: "Active", pass: "1h 32m",  swath: "141 km" },
  { name: "INSAT-3DR",       status: "Active", pass: "Geo",     swath: "Full"   },
]

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title={<span>Climate <span className="text-gradient-climate">Intelligence</span> Dashboard</span>}
        subtitle="India · Live satellite-derived analysis · Last synced 2 min ago"
        breadcrumbs={[{ label: "Dashboard" }]}
        actions={
          <div className="flex items-center gap-2">
            <Badge className="border border-climate-emerald/30 bg-climate-emerald/10 text-climate-emerald hover:bg-climate-emerald/15">
              <span className="mr-1.5 inline-flex size-1.5 animate-pulse rounded-full bg-climate-emerald" />
              Live Feed
            </Badge>
            <Button appVariant="glow" rightIcon={<ArrowRight className="size-4" />}>Run Simulation</Button>
          </div>
        }
      />

      {/* ── KPI Cards ─────────────────────────────────────────── */}
      <ClimateKpiCards />

      <div className="grid gap-6 lg:grid-cols-3">
        <section aria-label="Active climate alerts" className="lg:col-span-2">
          <Card title={<SectionHeading title="Active Alerts" subtitle="Real-time anomaly detection across Indian regions" accent="dot" actions={<Button variant="ghost" size="sm" rightIcon={<ArrowRight className="size-3.5" />}>View all</Button>} />}>
            <div className="flex flex-col gap-2">
              {ALERTS.map((alert) => (
                <div key={alert.id} className="flex items-center gap-3 rounded-lg border border-border bg-secondary/40 px-4 py-3 transition-colors hover:bg-secondary/70">
                  <AlertTriangle className="size-4 shrink-0 text-climate-amber" aria-hidden />
                  <div className="flex flex-1 min-w-0 items-center gap-2">
                    <span className="font-medium text-foreground">{alert.region}</span>
                    <span className="text-sm text-muted-foreground truncate">— {alert.type}</span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${severityStyle[alert.severity]}`}>{alert.severity}</span>
                    <span className="text-xs text-muted-foreground">{alert.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </section>

        <section aria-label="Satellite status">
          <Card title={<SectionHeading title="Satellites" subtitle="ISRO active orbital assets" accent="dot" />}>
            <div className="flex flex-col gap-3">
              {SATELLITES.map((sat) => (
                <div key={sat.name} className="flex items-start gap-3 rounded-lg border border-border bg-secondary/40 px-4 py-3">
                  <Satellite className="mt-0.5 size-4 shrink-0 text-climate-sky" aria-hidden />
                  <div className="flex flex-1 min-w-0 flex-col gap-1">
                    <span className="text-sm font-semibold text-foreground">{sat.name}</span>
                    <div className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                      <span>Next pass: <b className="text-foreground">{sat.pass}</b></span>
                      <span>Swath: <b className="text-foreground">{sat.swath}</b></span>
                    </div>
                  </div>
                  <span className="flex items-center gap-1 text-xs text-climate-emerald">
                    <Activity className="size-3" aria-hidden />{sat.status}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </section>
      </div>

      <section aria-label="Climate trends">
        <ClimateTrendCharts />
      </section>
    </div>
  )
}

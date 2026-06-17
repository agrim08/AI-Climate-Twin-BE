"use client"

import * as React from "react"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts"
import { Thermometer, Droplets, TrendingUp, Calendar } from "lucide-react"
import { Card } from "@/components/Card"
import { SectionHeading } from "@/components/SectionHeading"
import { Button } from "@/components/Button"
import { ChartContainer } from "@/components/ChartContainer"
import { WEEKLY_FORECAST, ANNUAL_HISTORICAL } from "@/mock/forecast"

type Period = "7D" | "30D" | "90D" | "1Y"

interface ChartDataPoint {
  label: string
  tempMax: number
  tempMin?: number
  temperature?: number // used for annual baseline mean temp
  tempAnomaly: number
  rainfall: number
}

/* ─────────────────────────────────────────────────────────────────────────────
   DETERMINISTIC DATA GENERATION FOR INTERACTIVE PERIODS
───────────────────────────────────────────────────────────────────────────── */

const generate30DData = (): ChartDataPoint[] => {
  const data: ChartDataPoint[] = []
  const start = new Date(2025, 4, 19) // May 19, 2025
  for (let i = 0; i < 30; i++) {
    const d = new Date(start)
    d.setDate(start.getDate() + i)
    const label = d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    
    // Realistic temperature trend: summer heat in India (peaks in late May, slightly drops mid-June)
    const baseTemp = 34.5 + Math.sin(i * 0.2) * 2
    const tempMax = Math.round((baseTemp + (i % 3) * 0.4) * 10) / 10
    const tempMin = Math.round((baseTemp - 6.5 + Math.cos(i * 0.15) * 1) * 10) / 10
    
    // Anomaly trend corresponding to India heatwave
    const tempAnomaly = Math.round((1.1 + Math.sin(i * 0.1) * 0.4 + (i % 2) * 0.1) * 10) / 10
    
    // Rains start mid-June (monsoon onset)
    let rainfall = 0
    if (i >= 20) {
      // Periodic monsoon showers
      rainfall = i % 4 === 0 ? Math.round((18 + Math.sin(i) * 22) * 10) / 10 : 0
    } else {
      // Dry season, minor pre-monsoon dust storm/shower
      rainfall = i === 8 ? 4.2 : 0
    }

    data.push({
      label,
      tempMax,
      tempMin,
      tempAnomaly,
      rainfall,
    })
  }
  return data
}

const generate90DData = (): ChartDataPoint[] => {
  const data: ChartDataPoint[] = []
  const start = new Date(2025, 2, 20) // March 20, 2025
  for (let i = 0; i < 13; i++) { // 13 weeks
    const d = new Date(start)
    d.setDate(start.getDate() + i * 7)
    const label = `Wk ${i + 1} (${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })})`
    
    const tempMax = Math.round((32 + (i * 0.5) + Math.sin(i * 0.6) * 2) * 10) / 10
    const tempMin = Math.round((22 + (i * 0.4) + Math.cos(i * 0.6) * 1.5) * 10) / 10
    const tempAnomaly = Math.round((0.8 + (i * 0.06) + Math.sin(i * 0.4) * 0.25) * 10) / 10
    
    // Early summer dry, increasing rain in June weeks
    const rainfall = i >= 9
      ? Math.round((15 + Math.sin(i) * 35) * 10) / 10
      : i === 4 ? 8.5 : 0

    data.push({
      label,
      tempMax,
      tempMin,
      tempAnomaly,
      rainfall: rainfall < 0 ? 0 : rainfall,
    })
  }
  return data
}

const getChartData = (period: Period): ChartDataPoint[] => {
  switch (period) {
    case "7D":
      return WEEKLY_FORECAST.map((d) => ({
        label: d.label,
        tempMax: d.tempMax,
        tempMin: d.tempMin,
        tempAnomaly: 1.2, // average anomaly for the week
        rainfall: d.rainfall,
      }))
    case "30D":
      return generate30DData()
    case "90D":
      return generate90DData()
    case "1Y":
      return ANNUAL_HISTORICAL.map((d) => ({
        label: d.month,
        temperature: d.temperature, // mean monthly temp
        tempMax: d.temperature + 4.5, // approximate peak temp
        tempMin: d.temperature - 5.5, // approximate trough temp
        tempAnomaly: d.tempAnomaly,
        rainfall: d.rainfall,
      }))
  }
}

/* ─────────────────────────────────────────────────────────────────────────────
   CUSTOM STYLED TOOLTIP (Matches Climate Twin Dark Theme)
───────────────────────────────────────────────────────────────────────────── */

interface CustomTooltipProps {
  active?: boolean
  payload?: any[]
  label?: string
  unit?: string
}

const CustomTooltip = ({ active, payload, label, unit = "" }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-border bg-card/95 p-3.5 shadow-xl backdrop-blur-md ring-1 ring-white/10">
        <p className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">
          <Calendar className="size-3 text-climate-sky" />
          {label}
        </p>
        <div className="flex flex-col gap-1.5">
          {payload.map((item: any, idx: number) => (
            <div key={idx} className="flex items-center gap-6 justify-between">
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="size-2 rounded-full" style={{ backgroundColor: item.color || item.fill }} />
                {item.name}
              </span>
              <span className="text-xs font-bold text-foreground">
                {typeof item.value === "number" ? item.value.toFixed(1) : item.value}
                <span className="text-[10px] text-muted-foreground ml-0.5">{unit}</span>
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }
  return null
}

/* ─────────────────────────────────────────────────────────────────────────────
   CLIMATE TREND CHARTS COMPONENT
───────────────────────────────────────────────────────────────────────────── */

export function ClimateTrendCharts() {
  const [period, setPeriod] = React.useState<Period>("30D")
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  const chartData = React.useMemo(() => getChartData(period), [period])

  // Custom colors matching theme
  const colors = {
    tempMax: "#f59e0b", // climate-amber
    tempMin: "#38bdf8", // climate-sky
    tempMean: "#10b981", // climate-emerald
    tempAnomaly: "#f43f5e", // climate-rose
    rainfall: "#14b8a6", // climate-teal
    grid: "#1e293b", // border/60
    axis: "#64748b", // muted-foreground
  }

  // Helper values for dashboard stats
  const stats = React.useMemo(() => {
    const temps = chartData.map((d) => d.temperature || d.tempMax)
    const rains = chartData.map((d) => d.rainfall)
    const anomalies = chartData.map((d) => d.tempAnomaly)

    return {
      maxTemp: Math.max(...temps),
      avgAnomaly: +(anomalies.reduce((sum, val) => sum + val, 0) / anomalies.length).toFixed(2),
      totalRainfall: Math.round(rains.reduce((sum, val) => sum + val, 0)),
    }
  }, [chartData])

  if (!mounted) {
    return (
      <Card
        title={
          <SectionHeading
            title="Climate & Rainfall Trends"
            subtitle="Interactive atmospheric readouts and anomalies"
            accent="bar"
            actions={
              <div className="flex gap-1.5 bg-secondary/50 p-1 rounded-lg border border-border">
                {(["7D", "30D", "90D", "1Y"] as Period[]).map((p) => (
                  <Button
                    key={p}
                    variant={p === period ? "secondary" : "ghost"}
                    size="xs"
                    className="h-7 min-w-10 px-2"
                  >
                    {p}
                  </Button>
                ))}
              </div>
            }
          />
        }
      >
        <div className="flex h-96 items-center justify-center rounded-lg border border-dashed border-border bg-secondary/10">
          <span className="text-sm text-muted-foreground animate-pulse">Initializing charts engine...</span>
        </div>
      </Card>
    )
  }

  return (
    <Card
      title={
        <SectionHeading
          title="Climate & Rainfall Trends"
          subtitle="Multi-scale atmospheric analytics and anomalies"
          accent="bar"
          actions={
            <div className="flex gap-1 bg-secondary/60 p-1 rounded-lg border border-border">
              {(["7D", "30D", "90D", "1Y"] as Period[]).map((p) => (
                <Button
                  key={p}
                  variant={p === period ? "secondary" : "ghost"}
                  size="xs"
                  onClick={() => setPeriod(p)}
                  className="h-7 min-w-10 px-2 font-medium transition-all"
                >
                  {p}
                </Button>
              ))}
            </div>
          }
        />
      }
    >
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-2">
        
        {/* ── Temperature & Anomaly Chart ─────────────────────────────────────── */}
        <ChartContainer
          title={
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-lg bg-climate-amber/15">
                <Thermometer className="size-4 text-climate-amber" />
              </div>
              <span className="text-sm font-semibold text-foreground">Temperature & Anomaly</span>
            </div>
          }
          subtitle="Land surface measurements & baseline deviations"
          actions={
            <div className="flex items-center gap-3 text-right">
              <div>
                <span className="text-[9px] uppercase tracking-wider text-muted-foreground block leading-none">Max Record</span>
                <span className="text-xs font-bold text-climate-amber">{stats.maxTemp.toFixed(1)}°C</span>
              </div>
              <div className="h-6 w-px bg-border" />
              <div>
                <span className="text-[9px] uppercase tracking-wider text-muted-foreground block leading-none">Avg Anomaly</span>
                <span className="text-xs font-bold text-climate-rose">+{stats.avgAnomaly.toFixed(2)}°C</span>
              </div>
            </div>
          }
          minHeight="260px"
          className="bg-secondary/20 border border-border/40 transition-all hover:bg-secondary/30"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 5, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="tempMaxGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.tempMax} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={colors.tempMax} stopOpacity={0} />
                </linearGradient>
                {period !== "1Y" && (
                  <linearGradient id="tempMinGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colors.tempMin} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={colors.tempMin} stopOpacity={0} />
                  </linearGradient>
                )}
                {period === "1Y" && (
                  <linearGradient id="tempMeanGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={colors.tempMean} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={colors.tempMean} stopOpacity={0} />
                  </linearGradient>
                )}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
              <XAxis
                dataKey="label"
                stroke={colors.axis}
                fontSize={10}
                tickLine={false}
                axisLine={false}
                dy={8}
              />
              <YAxis
                stroke={colors.axis}
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={["dataMin - 2", "dataMax + 2"]}
              />
              <Tooltip content={<CustomTooltip unit="°C" />} />
              <Legend
                verticalAlign="top"
                height={36}
                iconType="circle"
                iconSize={6}
                wrapperStyle={{ fontSize: "11px", color: "#64748b" }}
              />
              
              {period === "1Y" ? (
                <Area
                  name="Mean Temp"
                  type="monotone"
                  dataKey="temperature"
                  stroke={colors.tempMean}
                  strokeWidth={2}
                  fill="url(#tempMeanGrad)"
                />
              ) : (
                <>
                  <Area
                    name="Max Temp"
                    type="monotone"
                    dataKey="tempMax"
                    stroke={colors.tempMax}
                    strokeWidth={2}
                    fill="url(#tempMaxGrad)"
                  />
                  <Area
                    name="Min Temp"
                    type="monotone"
                    dataKey="tempMin"
                    stroke={colors.tempMin}
                    strokeWidth={1.5}
                    fill="url(#tempMinGrad)"
                  />
                </>
              )}

              <Area
                name="Temperature Anomaly"
                type="monotone"
                dataKey="tempAnomaly"
                stroke={colors.tempAnomaly}
                strokeWidth={2}
                strokeDasharray="4 4"
                fill="none"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* ── Rainfall Trend Chart ────────────────────────────────────────────── */}
        <ChartContainer
          title={
            <div className="flex items-center gap-2">
              <div className="flex size-7 items-center justify-center rounded-lg bg-climate-teal/15">
                <Droplets className="size-4 text-climate-teal" />
              </div>
              <span className="text-sm font-semibold text-foreground">Rainfall Trend</span>
            </div>
          }
          subtitle="Precipitation volume over selected timeframe"
          actions={
            <div className="flex items-center gap-3 text-right">
              <div>
                <span className="text-[9px] uppercase tracking-wider text-muted-foreground block leading-none">Total Volume</span>
                <span className="text-xs font-bold text-climate-teal">{stats.totalRainfall} mm</span>
              </div>
              <div className="h-6 w-px bg-border" />
              <div>
                <span className="text-[9px] uppercase tracking-wider text-muted-foreground block leading-none">Deviation Status</span>
                <span className="text-xs font-bold text-climate-emerald flex items-center gap-0.5">
                  <TrendingUp className="size-3 inline" />
                  +4%
                </span>
              </div>
            </div>
          }
          minHeight="260px"
          className="bg-secondary/20 border border-border/40 transition-all hover:bg-secondary/30"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 5, left: -25, bottom: 0 }}>
              <defs>
                <linearGradient id="rainGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.rainfall} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={colors.rainfall} stopOpacity={0.2} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.grid} vertical={false} />
              <XAxis
                dataKey="label"
                stroke={colors.axis}
                fontSize={10}
                tickLine={false}
                axisLine={false}
                dy={8}
              />
              <YAxis
                stroke={colors.axis}
                fontSize={10}
                tickLine={false}
                axisLine={false}
                domain={[0, "dataMax + 20"]}
              />
              <Tooltip content={<CustomTooltip unit=" mm" />} />
              <Legend
                verticalAlign="top"
                height={36}
                iconType="circle"
                iconSize={6}
                wrapperStyle={{ fontSize: "11px", color: "#64748b" }}
              />
              <Bar
                name="Rainfall Volume"
                dataKey="rainfall"
                fill="url(#rainGrad)"
                radius={[4, 4, 0, 0]}
                maxBarSize={period === "7D" ? 40 : period === "30D" ? 14 : period === "90D" ? 24 : 32}
              />
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>

      </div>
    </Card>
  )
}

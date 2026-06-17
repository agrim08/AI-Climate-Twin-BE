/* ─────────────────────────────────────────────────────────────────────────────
   mock/simulation.ts
   Scenario definitions, parameter presets, and projected output data
   for the Climate Simulator page.
   Used by: Simulator page, AI Copilot context, Risk Analysis forecast tab.
───────────────────────────────────────────────────────────────────────────── */

export type ScenarioId = "baseline" | "rcp26" | "rcp45" | "rcp85" | "custom"
export type ScenarioStatus = "active" | "preset" | "custom"

/* ── Parameter types ─────────────────────────────────────────────────────── */
export interface SimulationParameters {
  /** Global CO₂ emissions (GtC/yr) */
  co2Emissions: number
  /** Global mean temperature delta from pre-industrial (°C) */
  tempDelta: number
  /** Annual deforestation rate (Mha/yr — India) */
  deforestationRate: number
  /** Monsoon variation from normal (%) */
  monsoonVariation: number
  /** Population growth rate (% per year) */
  populationGrowthRate: number
  /** Renewable energy share (%) */
  renewableShare: number
  /** Urban heat island intensity (°C extra) */
  urbanHeatIsland: number
}

/* ── Scenario definition ─────────────────────────────────────────────────── */
export interface SimulationScenario {
  id: ScenarioId
  label: string
  description: string
  status: ScenarioStatus
  /** IPCC reference name */
  ipccRef?: string
  parameters: SimulationParameters
  /** Color accent for charts */
  color: string
}

/* ── Projected output per year ───────────────────────────────────────────── */
export interface SimulationYearOutput {
  year: number
  /** Projected national mean temperature (°C) */
  temperature: number
  /** Temperature anomaly vs 2025 baseline (°C) */
  tempAnomaly: number
  /** National average NDVI */
  ndvi: number
  /** Drought Risk Index (0–1) */
  droughtRisk: number
  /** Flood Risk Index (0–1) */
  floodRisk: number
  /** Crop yield change vs baseline (%) */
  cropYieldChange: number
  /** Population exposed to extreme heat >40°C (millions) */
  extremeHeatExposureM: number
  /** CO₂ concentration (ppm) */
  co2Ppm: number
  /** Estimated GDP impact (% of India GDP) */
  gdpImpactPct: number
}

/* ── Scenario presets ────────────────────────────────────────────────────── */
export const SCENARIOS: SimulationScenario[] = [
  {
    id: "baseline",
    label: "2025 Baseline",
    description: "Current observed conditions. No additional mitigation or acceleration.",
    status: "active",
    ipccRef: "Historical",
    color: "#10b981",   // emerald
    parameters: {
      co2Emissions:       10.2,
      tempDelta:           1.3,
      deforestationRate:   5.4,
      monsoonVariation:   -8,
      populationGrowthRate: 0.8,
      renewableShare:     22,
      urbanHeatIsland:     1.2,
    },
  },
  {
    id: "rcp26",
    label: "RCP 2.6 — Best Case",
    description: "Strong global mitigation. Emissions peak before 2020 and decline sharply. +1.5°C by 2100.",
    status: "preset",
    ipccRef: "RCP 2.6",
    color: "#06b6d4",   // cyan
    parameters: {
      co2Emissions:        4.5,
      tempDelta:           1.5,
      deforestationRate:   1.2,
      monsoonVariation:   +4,
      populationGrowthRate: 0.6,
      renewableShare:     68,
      urbanHeatIsland:     0.8,
    },
  },
  {
    id: "rcp45",
    label: "RCP 4.5 — Moderate",
    description: "Moderate mitigation. Emissions peak around 2040 then decline. +2.0–2.5°C by 2100.",
    status: "preset",
    ipccRef: "RCP 4.5",
    color: "#f59e0b",   // amber
    parameters: {
      co2Emissions:        7.8,
      tempDelta:           2.0,
      deforestationRate:   3.5,
      monsoonVariation:   -5,
      populationGrowthRate: 0.9,
      renewableShare:     42,
      urbanHeatIsland:     1.5,
    },
  },
  {
    id: "rcp85",
    label: "RCP 8.5 — Severe",
    description: "Business as usual. No major mitigation. Emissions rise throughout 21st century. +4.0–5.0°C by 2100.",
    status: "preset",
    ipccRef: "RCP 8.5",
    color: "#f43f5e",   // rose
    parameters: {
      co2Emissions:       16.2,
      tempDelta:           4.0,
      deforestationRate:   8.8,
      monsoonVariation:  -18,
      populationGrowthRate: 1.2,
      renewableShare:     14,
      urbanHeatIsland:     2.8,
    },
  },
]

/* ── Projected outputs by scenario (2025–2050) ───────────────────────────── */

export const PROJECTION_BASELINE: SimulationYearOutput[] = [
  { year: 2025, temperature: 28.4, tempAnomaly: +1.3, ndvi: 0.63, droughtRisk: 0.38, floodRisk: 0.32, cropYieldChange:   0, extremeHeatExposureM: 210, co2Ppm: 421, gdpImpactPct: -0.8 },
  { year: 2027, temperature: 28.8, tempAnomaly: +1.5, ndvi: 0.61, droughtRisk: 0.40, floodRisk: 0.34, cropYieldChange:  -3, extremeHeatExposureM: 225, co2Ppm: 424, gdpImpactPct: -1.0 },
  { year: 2030, temperature: 29.4, tempAnomaly: +1.9, ndvi: 0.58, droughtRisk: 0.44, floodRisk: 0.36, cropYieldChange:  -7, extremeHeatExposureM: 260, co2Ppm: 430, gdpImpactPct: -1.4 },
  { year: 2035, temperature: 30.1, tempAnomaly: +2.3, ndvi: 0.55, droughtRisk: 0.50, floodRisk: 0.40, cropYieldChange: -11, extremeHeatExposureM: 310, co2Ppm: 440, gdpImpactPct: -2.0 },
  { year: 2040, temperature: 30.8, tempAnomaly: +2.7, ndvi: 0.51, droughtRisk: 0.56, floodRisk: 0.42, cropYieldChange: -16, extremeHeatExposureM: 370, co2Ppm: 452, gdpImpactPct: -2.8 },
  { year: 2045, temperature: 31.4, tempAnomaly: +3.1, ndvi: 0.48, droughtRisk: 0.62, floodRisk: 0.45, cropYieldChange: -21, extremeHeatExposureM: 440, co2Ppm: 462, gdpImpactPct: -3.6 },
  { year: 2050, temperature: 32.0, tempAnomaly: +3.5, ndvi: 0.44, droughtRisk: 0.68, floodRisk: 0.48, cropYieldChange: -26, extremeHeatExposureM: 520, co2Ppm: 474, gdpImpactPct: -4.5 },
]

export const PROJECTION_RCP45: SimulationYearOutput[] = [
  { year: 2025, temperature: 28.4, tempAnomaly: +1.3, ndvi: 0.63, droughtRisk: 0.38, floodRisk: 0.32, cropYieldChange:   0, extremeHeatExposureM: 210, co2Ppm: 421, gdpImpactPct: -0.8 },
  { year: 2027, temperature: 28.7, tempAnomaly: +1.4, ndvi: 0.62, droughtRisk: 0.39, floodRisk: 0.33, cropYieldChange:  -2, extremeHeatExposureM: 218, co2Ppm: 426, gdpImpactPct: -0.9 },
  { year: 2030, temperature: 29.1, tempAnomaly: +1.7, ndvi: 0.60, droughtRisk: 0.42, floodRisk: 0.35, cropYieldChange:  -5, extremeHeatExposureM: 240, co2Ppm: 435, gdpImpactPct: -1.2 },
  { year: 2035, temperature: 29.6, tempAnomaly: +2.0, ndvi: 0.57, droughtRisk: 0.46, floodRisk: 0.38, cropYieldChange:  -8, extremeHeatExposureM: 275, co2Ppm: 448, gdpImpactPct: -1.6 },
  { year: 2040, temperature: 30.0, tempAnomaly: +2.4, ndvi: 0.55, droughtRisk: 0.50, floodRisk: 0.40, cropYieldChange: -12, extremeHeatExposureM: 310, co2Ppm: 460, gdpImpactPct: -2.1 },
  { year: 2045, temperature: 30.3, tempAnomaly: +2.6, ndvi: 0.53, droughtRisk: 0.52, floodRisk: 0.42, cropYieldChange: -14, extremeHeatExposureM: 340, co2Ppm: 468, gdpImpactPct: -2.5 },
  { year: 2050, temperature: 30.6, tempAnomaly: +2.8, ndvi: 0.51, droughtRisk: 0.55, floodRisk: 0.44, cropYieldChange: -17, extremeHeatExposureM: 380, co2Ppm: 475, gdpImpactPct: -3.0 },
]

export const PROJECTION_RCP85: SimulationYearOutput[] = [
  { year: 2025, temperature: 28.4, tempAnomaly: +1.3, ndvi: 0.63, droughtRisk: 0.38, floodRisk: 0.32, cropYieldChange:   0, extremeHeatExposureM: 210, co2Ppm: 421, gdpImpactPct: -0.8 },
  { year: 2027, temperature: 29.0, tempAnomaly: +1.6, ndvi: 0.60, droughtRisk: 0.42, floodRisk: 0.36, cropYieldChange:  -5, extremeHeatExposureM: 240, co2Ppm: 428, gdpImpactPct: -1.2 },
  { year: 2030, temperature: 30.0, tempAnomaly: +2.3, ndvi: 0.55, droughtRisk: 0.50, floodRisk: 0.42, cropYieldChange: -11, extremeHeatExposureM: 300, co2Ppm: 445, gdpImpactPct: -2.0 },
  { year: 2035, temperature: 31.4, tempAnomaly: +3.1, ndvi: 0.48, droughtRisk: 0.60, floodRisk: 0.50, cropYieldChange: -19, extremeHeatExposureM: 400, co2Ppm: 472, gdpImpactPct: -3.2 },
  { year: 2040, temperature: 32.8, tempAnomaly: +3.9, ndvi: 0.42, droughtRisk: 0.70, floodRisk: 0.58, cropYieldChange: -27, extremeHeatExposureM: 510, co2Ppm: 502, gdpImpactPct: -4.8 },
  { year: 2045, temperature: 34.1, tempAnomaly: +4.7, ndvi: 0.36, droughtRisk: 0.80, floodRisk: 0.65, cropYieldChange: -35, extremeHeatExposureM: 640, co2Ppm: 534, gdpImpactPct: -6.5 },
  { year: 2050, temperature: 35.5, tempAnomaly: +5.5, ndvi: 0.29, droughtRisk: 0.90, floodRisk: 0.72, cropYieldChange: -44, extremeHeatExposureM: 800, co2Ppm: 570, gdpImpactPct: -9.0 },
]

/* ── Scenario comparison table (at 2050) ────────────────────────────────── */
export interface ScenarioComparison {
  scenarioId: ScenarioId
  label: string
  color: string
  temp2050: number
  ndvi2050: number
  cropLoss2050: number
  extremeHeat2050M: number
  gdpImpact2050Pct: number
}

export const SCENARIO_COMPARISON_2050: ScenarioComparison[] = [
  { scenarioId: "rcp26",    label: "RCP 2.6",   color: "#06b6d4", temp2050: 29.2, ndvi2050: 0.58, cropLoss2050: -8,  extremeHeat2050M: 280, gdpImpact2050Pct: -1.2 },
  { scenarioId: "rcp45",    label: "RCP 4.5",   color: "#f59e0b", temp2050: 30.6, ndvi2050: 0.51, cropLoss2050: -17, extremeHeat2050M: 380, gdpImpact2050Pct: -3.0 },
  { scenarioId: "baseline", label: "Baseline",  color: "#10b981", temp2050: 32.0, ndvi2050: 0.44, cropLoss2050: -26, extremeHeat2050M: 520, gdpImpact2050Pct: -4.5 },
  { scenarioId: "rcp85",    label: "RCP 8.5",   color: "#f43f5e", temp2050: 35.5, ndvi2050: 0.29, cropLoss2050: -44, extremeHeat2050M: 800, gdpImpact2050Pct: -9.0 },
]

/** Get scenario by ID */
export function getScenario(id: ScenarioId): SimulationScenario | undefined {
  return SCENARIOS.find((s) => s.id === id)
}

/** Get projection data for a given scenario */
export function getProjection(id: ScenarioId): SimulationYearOutput[] {
  switch (id) {
    case "rcp45":    return PROJECTION_RCP45
    case "rcp85":    return PROJECTION_RCP85
    case "baseline":
    default:         return PROJECTION_BASELINE
  }
}

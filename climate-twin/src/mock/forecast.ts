/* ─────────────────────────────────────────────────────────────────────────────
   mock/forecast.ts
   7-day and 30-day climate forecast data for India.
   Used by: Dashboard (trend chart), Risk Analysis (7-day tab), Simulator.
───────────────────────────────────────────────────────────────────────────── */

export type WeatherCondition =
  | "Sunny"
  | "Partly Cloudy"
  | "Cloudy"
  | "Light Rain"
  | "Moderate Rain"
  | "Heavy Rain"
  | "Thunderstorm"
  | "Dust Storm"
  | "Foggy"
  | "Heatwave"

export interface DailyForecast {
  /** ISO date string e.g. "2025-06-17" */
  date: string
  /** Display label e.g. "Mon", "Today" */
  label: string
  /** Max temperature (°C) */
  tempMax: number
  /** Min temperature (°C) */
  tempMin: number
  /** Total rainfall (mm) */
  rainfall: number
  /** Probability of precipitation (%) */
  rainChance: number
  /** Air Quality Index */
  aqi: number
  /** Relative humidity (%) */
  humidity: number
  /** Wind speed (km/h) */
  windSpeed: number
  /** UV Index (0–11+) */
  uvIndex: number
  /** Weather condition label */
  condition: WeatherCondition
}

export interface MonthlyDataPoint {
  /** Month label e.g. "Jan 25" */
  month: string
  /** Mean temperature (°C) */
  temperature: number
  /** Total rainfall (mm) */
  rainfall: number
  /** Mean NDVI */
  ndvi: number
  /** Mean AQI */
  aqi: number
  /** Mean CO₂ (ppm) */
  co2: number
  /** Temperature anomaly vs 30-yr mean */
  tempAnomaly: number
}

/* ── 7-day national forecast (India average) ─────────────────────────────── */
export const WEEKLY_FORECAST: DailyForecast[] = [
  {
    date: "2025-06-17", label: "Today",
    tempMax: 34.0, tempMin: 26.2, rainfall: 12,  rainChance: 45, aqi: 110, humidity: 68, windSpeed: 14, uvIndex: 9,  condition: "Partly Cloudy",
  },
  {
    date: "2025-06-18", label: "Tue",
    tempMax: 35.4, tempMin: 27.0, rainfall: 4,   rainChance: 20, aqi: 128, humidity: 60, windSpeed: 18, uvIndex: 10, condition: "Sunny",
  },
  {
    date: "2025-06-19", label: "Wed",
    tempMax: 37.1, tempMin: 28.3, rainfall: 0,   rainChance: 8,  aqi: 148, humidity: 52, windSpeed: 22, uvIndex: 11, condition: "Heatwave",
  },
  {
    date: "2025-06-20", label: "Thu",
    tempMax: 36.8, tempMin: 27.8, rainfall: 0,   rainChance: 10, aqi: 142, humidity: 50, windSpeed: 20, uvIndex: 11, condition: "Heatwave",
  },
  {
    date: "2025-06-21", label: "Fri",
    tempMax: 34.2, tempMin: 26.5, rainfall: 22,  rainChance: 60, aqi: 105, humidity: 72, windSpeed: 16, uvIndex: 7,  condition: "Thunderstorm",
  },
  {
    date: "2025-06-22", label: "Sat",
    tempMax: 31.8, tempMin: 24.9, rainfall: 38,  rainChance: 75, aqi:  88, humidity: 82, windSpeed: 12, uvIndex: 5,  condition: "Heavy Rain",
  },
  {
    date: "2025-06-23", label: "Sun",
    tempMax: 30.2, tempMin: 23.8, rainfall: 18,  rainChance: 55, aqi:  78, humidity: 80, windSpeed: 10, uvIndex: 6,  condition: "Moderate Rain",
  },
]

/* ── 30-day time-series (for Recharts line charts) ───────────────────────── */
export const MONTHLY_TIMESERIES: MonthlyDataPoint[] = [
  { month: "Jan 25", temperature: 18.2, rainfall:  28, ndvi: 0.55, aqi:  98, co2: 419.2, tempAnomaly: +0.6 },
  { month: "Feb 25", temperature: 21.4, rainfall:  14, ndvi: 0.51, aqi: 105, co2: 419.5, tempAnomaly: +0.8 },
  { month: "Mar 25", temperature: 27.8, rainfall:  10, ndvi: 0.46, aqi: 122, co2: 420.0, tempAnomaly: +1.0 },
  { month: "Apr 25", temperature: 33.2, rainfall:  18, ndvi: 0.40, aqi: 135, co2: 420.4, tempAnomaly: +1.2 },
  { month: "May 25", temperature: 36.8, rainfall:  32, ndvi: 0.34, aqi: 150, co2: 421.0, tempAnomaly: +1.5 },
  { month: "Jun 25", temperature: 34.0, rainfall: 120, ndvi: 0.42, aqi: 110, co2: 421.3, tempAnomaly: +1.2 },
]

/* ── 12-month historical baseline (previous year) ────────────────────────── */
export const ANNUAL_HISTORICAL: MonthlyDataPoint[] = [
  { month: "Jul 24", temperature: 31.2, rainfall: 280, ndvi: 0.62, aqi:  82, co2: 418.8, tempAnomaly: +0.9 },
  { month: "Aug 24", temperature: 30.8, rainfall: 310, ndvi: 0.68, aqi:  78, co2: 418.5, tempAnomaly: +0.8 },
  { month: "Sep 24", temperature: 31.5, rainfall: 210, ndvi: 0.65, aqi:  88, co2: 418.9, tempAnomaly: +0.9 },
  { month: "Oct 24", temperature: 29.8, rainfall:  90, ndvi: 0.60, aqi:  95, co2: 419.0, tempAnomaly: +0.7 },
  { month: "Nov 24", temperature: 24.4, rainfall:  40, ndvi: 0.58, aqi: 100, co2: 419.1, tempAnomaly: +0.6 },
  { month: "Dec 24", temperature: 19.8, rainfall:  22, ndvi: 0.56, aqi:  95, co2: 419.2, tempAnomaly: +0.6 },
  { month: "Jan 25", temperature: 18.2, rainfall:  28, ndvi: 0.55, aqi:  98, co2: 419.2, tempAnomaly: +0.6 },
  { month: "Feb 25", temperature: 21.4, rainfall:  14, ndvi: 0.51, aqi: 105, co2: 419.5, tempAnomaly: +0.8 },
  { month: "Mar 25", temperature: 27.8, rainfall:  10, ndvi: 0.46, aqi: 122, co2: 420.0, tempAnomaly: +1.0 },
  { month: "Apr 25", temperature: 33.2, rainfall:  18, ndvi: 0.40, aqi: 135, co2: 420.4, tempAnomaly: +1.2 },
  { month: "May 25", temperature: 36.8, rainfall:  32, ndvi: 0.34, aqi: 150, co2: 421.0, tempAnomaly: +1.5 },
  { month: "Jun 25", temperature: 34.0, rainfall: 120, ndvi: 0.42, aqi: 110, co2: 421.3, tempAnomaly: +1.2 },
]

/** AQI bracket label */
export function aqiLabel(aqi: number): string {
  if (aqi <= 50)  return "Good"
  if (aqi <= 100) return "Moderate"
  if (aqi <= 150) return "Unhealthy for Sensitive"
  if (aqi <= 200) return "Unhealthy"
  if (aqi <= 300) return "Very Unhealthy"
  return "Hazardous"
}

/** AQI color class (Tailwind / CSS var) */
export function aqiColor(aqi: number): string {
  if (aqi <= 50)  return "text-climate-emerald"
  if (aqi <= 100) return "text-yellow-400"
  if (aqi <= 150) return "text-climate-amber"
  if (aqi <= 200) return "text-orange-500"
  return "text-climate-rose"
}

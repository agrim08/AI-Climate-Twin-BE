import os
import time
import logging
from typing import Optional, Dict, Any, List

import httpx

from app.core.config import settings

logger = logging.getLogger("app.gemini")

class GeminiService:
    """Service to connect directly to the Gemini API, manage prompts, and retrieve natural language summaries."""

    def __init__(self, api_key: Optional[str] = None):
        # Allow passing api_key directly or fall back to application settings
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = "gemini-2.5-flash"
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        # Check if API key is present
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Gemini integration will fall back to rule-based answers.")

    def is_available(self) -> bool:
        """Returns True if the API key is configured."""
        return bool(self.api_key)

    def generate_response(self, prompt: str, retries: int = 3, backoff_seconds: float = 1.0) -> str:
        """
        Sends a prompt to the Gemini API using httpx synchronously.
        Includes automatic retry handling for transient network issues or rate limits (HTTP 429).
        """
        if not self.is_available():
            raise ValueError("Gemini API key is not configured.")

        url = f"{self.endpoint}?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.95,
                "maxOutputTokens": 800
            }
        }

        # Keep a separate client for request execution to avoid leaking connections
        with httpx.Client(timeout=5.0) as client:
            for attempt in range(1, retries + 1):
                try:
                    logger.debug("Sending request to Gemini (Attempt %d/%d)...", attempt, retries)
                    response = client.post(url, json=payload)

                    if response.status_code == 200:
                        data = response.json()
                        # Traverse standard Gemini response path
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts:
                                text_response = parts[0].get("text", "")
                                if text_response:
                                    return text_response.strip()
                        raise ValueError(f"Malformed Gemini API response: {data}")

                    elif response.status_code == 429:
                        logger.warning("Gemini API Rate Limited (429) on attempt %d. Retrying...", attempt)
                        if attempt == retries:
                            response.raise_for_status()
                        time.sleep(backoff_seconds * attempt)

                    elif response.status_code >= 500:
                        logger.warning("Gemini Server Error (%d) on attempt %d. Retrying...", response.status_code, attempt)
                        if attempt == retries:
                            response.raise_for_status()
                        time.sleep(backoff_seconds * attempt)

                    else:
                        logger.error("Gemini API returned unhandled status code %d: %s", response.status_code, response.text)
                        response.raise_for_status()

                except (httpx.HTTPError, ValueError) as ex:
                    logger.warning("Gemini API attempt %d failed: %s", attempt, str(ex))
                    if attempt == retries:
                        raise ex
                    time.sleep(backoff_seconds * attempt)

        raise ValueError("Failed to retrieve a response from Gemini API.")

    # --- Prompt Templates Section ---

    @staticmethod
    def get_crop_suitability_prompt(crop_name: str, temp: float, rainfall: float, rule_reason: str) -> str:
        """Creates a prompt to evaluate suitability for a specific crop."""
        return (
            "You are an expert Indian agricultural AI advisor. Help a farmer understand if they can grow a crop.\n\n"
            f"Crop to Check: {crop_name}\n"
            f"Current Temperature: {temp}°C\n"
            f"Current Rainfall: {rainfall} mm\n"
            f"Rule-Based Suitability Outcome: {rule_reason}\n\n"
            "Instructions:\n"
            "1. Explain to the farmer why the crop is or is not suitable in a simple, friendly tone.\n"
            "2. Provide 2-3 specific, actionable recommendations (e.g. irrigation techniques, soil amendments, or alternative sowing periods) based on the temperature and rainfall.\n"
            "3. Keep the response concise, actionable, and formatted in clean Markdown with bullet points."
        )

    @staticmethod
    def get_climate_report_prompt(temp: float, rainfall: float, drought_risk: str, suitable_crops: List[str], recommendations_rule: str) -> str:
        """Creates a prompt to interpret a general climate summary report."""
        crops_str = ", ".join(suitable_crops) if suitable_crops else "None"
        return (
            "You are an expert Indian agricultural advisor. Generate a highly readable, encouraging, and actionable Climate & Crop Summary Report for a farmer.\n\n"
            f"Current Conditions:\n"
            f"- Temperature: {temp}°C\n"
            f"- Rainfall: {rainfall} mm\n"
            f"- Drought Risk: {drought_risk}\n"
            f"- Rule-Based Suitable Crops: [{crops_str}]\n"
            f"- Rule-Based Recommendations: {recommendations_rule}\n\n"
            "Instructions:\n"
            "1. Generate a structured Markdown report.\n"
            "2. Under a 'Climate Assessment' header, explain what these temperature and rainfall figures mean for general farming conditions.\n"
            "3. Under a 'Crop Planning' header, list the suitable crops and highlight 1 or 2 that would perform exceptionally well under these conditions.\n"
            "4. Under an 'Action Plan' header, provide actionable advice (e.g. water conservation, mulching, or drainage management) based on the conditions.\n"
            "5. Keep the vocabulary simple, encouraging, and farmer-friendly."
        )

    @staticmethod
    def get_forecast_interpretation_prompt(temp: float, rainfall: float, forecasts: List[Dict[str, Any]]) -> str:
        """Creates a prompt to interpret future forecasts for a farmer."""
        forecasts_str = "\n".join(
            f"- Period/Date: {f.get('date', 'Unknown')}, Expected Temp: {f.get('temp', 'N/A')}°C, Expected Rainfall: {f.get('rainfall', 'N/A')} mm"
            for f in forecasts
        ) if forecasts else "No upcoming forecast records."

        return (
            "You are an expert agricultural AI. Interpret the following upcoming climate forecast for a farmer.\n\n"
            f"Current Conditions: Temperature {temp}°C, Rainfall {rainfall} mm.\n"
            f"Upcoming Forecast:\n{forecasts_str}\n\n"
            "Instructions:\n"
            "1. Explain to the farmer what trends they should prepare for (e.g. rising heat, approaching dry spells, or heavy rains).\n"
            "2. Detail exactly how this impact their crop scheduling or water management.\n"
            "3. Give 2 practical steps they should take this week to prepare."
        )

    @staticmethod
    def get_farmer_recommendations_prompt(temp: float, rainfall: float, drought_risk: str, suitable_crops: List[str]) -> str:
        """Creates a prompt to build custom recommendations for the farmer."""
        crops_str = ", ".join(suitable_crops) if suitable_crops else "None"
        return (
            "You are a compassionate agricultural advisor talking directly to a smallholder farmer.\n\n"
            f"Farming Conditions:\n"
            f"- Temperature: {temp}°C\n"
            f"- Rainfall: {rainfall} mm\n"
            f"- Drought Risk: {drought_risk}\n"
            f"- Recommended Crops: {crops_str}\n\n"
            "Provide 3-4 bulleted, highly specific tips on how they can maximize their yield, conserve soil health, and manage water resources. Keep the tone warm, respectful, and direct."
        )

    @staticmethod
    def get_climate_scenario_prompt(temp: float, rainfall: float, scenario_shift: str) -> str:
        """Creates a prompt to analyze a hypothetical climate change scenario shift."""
        return (
            "You are a climate scientist and agricultural resilience advisor.\n\n"
            f"Base Conditions: Temperature {temp}°C, Rainfall {rainfall} mm.\n"
            f"Hypothetical Scenario Shift: {scenario_shift}\n\n"
            "Instructions:\n"
            "1. Analyze what risks this scenario shift introduces (e.g. heat stress, waterlogging, or crop failure).\n"
            "2. Outline adaptation strategies (e.g. transition to heat-tolerant varieties, precision farming, crop diversification).\n"
            "3. Format the response cleanly in Markdown for planners and agricultural extension officers."
        )

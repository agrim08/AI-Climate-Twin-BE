"""
LLM Agent Service — Climate Twin AI Assistant
==============================================
Manages the Gemini 2.5 Flash chat layer with:
  • Agentic tool-calling: LLM autonomously fetches district data via our internal APIs.
  • Response caching: A short-TTL cache prevents redundant DB lookups for repeated queries.
  • Context-aware conversations: History is forwarded with every request.
  • Token saving: Simple/greeting messages are resolved client-side, never reaching the LLM.
  • Guardrails: System prompt rejects off-topic queries.
"""

import json
import logging
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types as genai_types

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Simple response cache for LLM-built answers (separate from PredictionCache)
# ---------------------------------------------------------------------------
class _LLMResponseCache:
    _cache: Dict[str, tuple] = {}
    _lock = threading.Lock()
    _TTL = 300  # 5-minute freshness window

    @classmethod
    def get(cls, key: str) -> Optional[str]:
        with cls._lock:
            entry = cls._cache.get(key)
            if entry and time.time() < entry[1]:
                return entry[0]
            return None

    @classmethod
    def set(cls, key: str, value: str):
        with cls._lock:
            cls._cache[key] = (value, time.time() + cls._TTL)


# ---------------------------------------------------------------------------
# Greeting / off-topic pre-filter  (saves tokens on trivial messages)
# ---------------------------------------------------------------------------
_GREETINGS = {
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "cool",
    "great", "got it", "nice", "bye", "goodbye", "good", "sure", "yes", "no",
    "yep", "nope", "alright", "fine", "good morning", "good evening",
    "good afternoon", "good night", "howdy", "sup", "wassup",
}

def _is_trivial(message: str) -> Optional[str]:
    """Return a canned reply if the message is a greeting/filler, else None."""
    stripped = message.strip().lower().rstrip("!.?,")
    if stripped in _GREETINGS:
        return (
            "Hello! I'm the **AI Climate Assistant** for the India Digital Twin. "
            "Ask me anything about district-level climate conditions, drought risk, "
            "heatwave alerts, crop planning, or future climate projections!"
        )
    return None


# ---------------------------------------------------------------------------
# Gemini client singleton
# ---------------------------------------------------------------------------
_gemini_client: Optional[genai.Client] = None

def _get_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ---------------------------------------------------------------------------
# Tool functions (these are the real Python functions the LLM can invoke)
# ---------------------------------------------------------------------------

async def _tool_get_district_climate_profile(
    district_name: str,
    state: str = "",
    year: int = 2025,
    month: int = 6,
) -> Dict[str, Any]:
    """Fetch current ML-predicted climate metrics for a specific district."""
    from app.core.database import AsyncSessionLocal
    from app.services.rankings import _evaluate_all_districts
    from sqlalchemy.future import select
    from app.models.district import District

    try:
        async with AsyncSessionLocal() as db:
            query = select(District).where(
                District.district_name.ilike(f"%{district_name}%")
            )
            if state:
                query = query.where(District.state.ilike(f"%{state}%"))
            result = await db.execute(query)
            districts = result.scalars().all()

            if not districts:
                return {"error": f"No district found matching '{district_name}'"}

            district = districts[0]
            # Re-use ranking evaluation logic which runs the full chained ML pipeline
            from app.services.rankings import _evaluate_district
            profile = await _evaluate_district(db, district, year, month)
            if profile is None:
                return {"error": "Failed to evaluate district profile."}
            return profile
    except Exception as e:
        logger.error(f"Tool error in get_district_climate_profile: {e}")
        return {"error": str(e)}


async def _tool_compare_districts(
    district_a: str,
    district_b: str,
    year: int = 2025,
    month: int = 6,
) -> Dict[str, Any]:
    """Compare climate profiles of two districts side-by-side."""
    a = await _tool_get_district_climate_profile(district_a, year=year, month=month)
    b = await _tool_get_district_climate_profile(district_b, year=year, month=month)
    return {"district_a": a, "district_b": b}


async def _tool_simulate_scenario(
    district_name: str,
    temp_delta: float = 0.0,
    rain_delta: float = 0.0,
    sm_delta: float = 0.0,
    year: int = 2025,
    month: int = 6,
) -> Dict[str, Any]:
    """Simulate a climate scenario for a district (e.g., +2°C, -20% rainfall)."""
    from app.core.database import AsyncSessionLocal
    from app.services.rankings import _evaluate_district
    from sqlalchemy.future import select
    from app.models.district import District

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(District).where(District.district_name.ilike(f"%{district_name}%"))
            )
            districts = result.scalars().all()
            if not districts:
                return {"error": f"No district found matching '{district_name}'"}
            profile = await _evaluate_district(
                db, districts[0], year, month,
                temp_delta=temp_delta, rain_delta=rain_delta, sm_delta=sm_delta
            )
            return profile or {"error": "Simulation failed"}
    except Exception as e:
        return {"error": str(e)}


async def _tool_get_national_rankings(
    year: int = 2025,
    month: int = 6,
    top_n: int = 5,
) -> Dict[str, Any]:
    """Get the top most-vulnerable and least-vulnerable districts across India."""
    from app.core.database import AsyncSessionLocal
    from app.services.rankings import RankingsService
    try:
        async with AsyncSessionLocal() as db:
            return await RankingsService.get_current_rankings(db, year, month, top_n)
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Gemini tool declarations
# ---------------------------------------------------------------------------
TOOL_DECLARATIONS = [
    genai_types.FunctionDeclaration(
        name="get_district_climate_profile",
        description=(
            "Fetch the current AI-predicted climate profile for any Indian district. "
            "Returns temperature, rainfall, drought severity, heatwave severity, "
            "water stress index, crop stress index, and hotspot vulnerability score."
        ),
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "district_name": genai_types.Schema(
                    type=genai_types.Type.STRING,
                    description="Name of the district (e.g., Jodhpur, Leh, Nashik)"
                ),
                "state": genai_types.Schema(
                    type=genai_types.Type.STRING,
                    description="Optional: State name to disambiguate (e.g., Rajasthan)"
                ),
                "year": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Target year for the prediction (default: 2025)"
                ),
                "month": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Target month 1–12 (default: 6 for June)"
                ),
            },
            required=["district_name"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="compare_districts",
        description=(
            "Compare the climate and vulnerability profiles of two Indian districts side-by-side."
        ),
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "district_a": genai_types.Schema(
                    type=genai_types.Type.STRING,
                    description="Name of the first district"
                ),
                "district_b": genai_types.Schema(
                    type=genai_types.Type.STRING,
                    description="Name of the second district"
                ),
                "year": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Target year (default: 2025)"
                ),
                "month": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Target month 1–12 (default: 6)"
                ),
            },
            required=["district_a", "district_b"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="simulate_scenario",
        description=(
            "Simulate a custom climate scenario for a district. Useful for answering questions like "
            "'What happens if temperature increases by 2°C and rainfall drops 20%?', "
            "or for crop planning under future climate conditions."
        ),
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "district_name": genai_types.Schema(
                    type=genai_types.Type.STRING,
                    description="Name of the district"
                ),
                "temp_delta": genai_types.Schema(
                    type=genai_types.Type.NUMBER,
                    description="Temperature change in degrees Celsius (positive = warmer)"
                ),
                "rain_delta": genai_types.Schema(
                    type=genai_types.Type.NUMBER,
                    description="Rainfall change as a percentage (e.g., -20 means 20% less rain)"
                ),
                "sm_delta": genai_types.Schema(
                    type=genai_types.Type.NUMBER,
                    description="Soil moisture change as a percentage"
                ),
                "year": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Target year (default: 2025)"
                ),
                "month": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Target month 1–12 (default: 6)"
                ),
            },
            required=["district_name"],
        ),
    ),
    genai_types.FunctionDeclaration(
        name="get_national_rankings",
        description=(
            "Get the most climate-vulnerable and least-vulnerable districts across all of India. "
            "Useful for questions about 'worst affected regions', 'most at risk areas', etc."
        ),
        parameters=genai_types.Schema(
            type=genai_types.Type.OBJECT,
            properties={
                "year": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Reference year (default: 2025)"
                ),
                "month": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="Reference month 1–12 (default: 6)"
                ),
                "top_n": genai_types.Schema(
                    type=genai_types.Type.INTEGER,
                    description="How many top/bottom districts to return (default: 5)"
                ),
            },
            required=[],
        ),
    ),
]

# Tool dispatch map
_TOOL_FUNCTIONS = {
    "get_district_climate_profile": _tool_get_district_climate_profile,
    "compare_districts": _tool_compare_districts,
    "simulate_scenario": _tool_simulate_scenario,
    "get_national_rankings": _tool_get_national_rankings,
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = f"""You are the **AI Climate Intelligence Assistant** for the India Digital Twin platform — a sophisticated analytical tool powered by machine learning models processing real-time climate data across 198 Indian districts.

## Your Role
You are an expert in Indian climate science, agronomy, water resource management, disaster preparedness, and climate risk analytics. You help government planners, farmers, researchers, and policy-makers make data-driven decisions.

## STRICT RULES — Follow these without exception

### 1. Domain Enforcement
If a user asks about anything UNRELATED to climate, weather, agriculture, water management, disaster risk, Indian geography, or the Digital Twin platform itself, politely but firmly decline and redirect them. Example off-topic queries: coding help, recipe requests, jokes, political opinions.

### 2. Data Grounding — No Hallucination
You MUST call the available tools to fetch real data before answering any climate-specific question about a district. NEVER invent or estimate numerical values. All metrics cited in your response (e.g., "Jodhpur has a Drought Severity of 0.73") must come directly from the tool results.

### 3. Context & Conversation Memory
The full conversation history is provided. Use it to answer follow-up questions intelligently. If the user says "compare it with Leh", infer "it" from the prior context.

### 4. Response Formatting — MANDATORY
- Use **bold** for ALL key metric values and district names (e.g., **48.5°C**, **Jodhpur**).
- **COMPARISONS MUST ALWAYS USE A MARKDOWN TABLE.** When comparing two or more districts, you MUST present the data in a proper markdown pipe table (| Metric | District A | District B |) with a separator row (|---|---|---|). Never write a comparison as prose alone — always include the table first, then the analysis.
- Use bullet points for lists of recommendations.
- For rankings (top-N lists), use a numbered markdown list.
- Be analytical and insightful — explain *why* a metric is high or low.
- For crop/irrigation decisions, always correlate Water Stress Index, Soil Moisture, and Drought Severity with agronomic best practices.
- Keep your response concise and structured — avoid long monologue paragraphs.

### 5. Confidence & Caveats
Always mention at the end (as a small italic note) that predictions are based on our ML models (not live weather sensors) and may carry ±5–15% uncertainty.

Today's date: {datetime.now().strftime("%B %d, %Y")}
"""


# ---------------------------------------------------------------------------
# Main async agent function
# ---------------------------------------------------------------------------
async def run_agent(
    message: str,
    history: List[Dict[str, str]],
) -> str:
    """
    Runs one turn of the Gemini 2.5 Flash agentic loop.
    Returns the final text response (fully assembled for non-streaming use).
    Handles multi-step tool calling automatically.
    """
    # 1. Trivial message pre-filter
    trivial = _is_trivial(message)
    if trivial:
        return trivial

    # 2. Cache check (use message + last 2 turns as key)
    cache_suffix = "|".join(
        [f"{h['role']}:{h['content'][:60]}" for h in history[-2:]]
    )
    cache_key = f"{message[:120]}|{cache_suffix}"
    cached = _LLMResponseCache.get(cache_key)
    if cached:
        return cached

    client = _get_client()

    # 3. Build conversation contents
    contents: List[genai_types.Content] = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        contents.append(
            genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=turn["content"])]
            )
        )
    # Add current user message
    contents.append(
        genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=message)]
        )
    )

    tools = genai_types.Tool(function_declarations=TOOL_DECLARATIONS)
    config = genai_types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        tools=[tools],
        temperature=0.4,
    )

    # 4. Agentic loop: keep calling until no more tool calls
    MAX_TURNS = 5
    for _ in range(MAX_TURNS):
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        candidate = response.candidates[0]

        # Check for function calls in the response
        fn_calls = [
            part.function_call
            for part in candidate.content.parts
            if hasattr(part, "function_call") and part.function_call is not None
        ]

        if not fn_calls:
            # No more tool calls — extract final text
            final_text = "".join(
                part.text
                for part in candidate.content.parts
                if hasattr(part, "text") and part.text
            )
            _LLMResponseCache.set(cache_key, final_text)
            return final_text

        # Execute all requested tool calls
        function_responses = []
        for fn_call in fn_calls:
            fn_name = fn_call.name
            fn_args = dict(fn_call.args) if fn_call.args else {}
            logger.info(f"LLM Agent: calling tool '{fn_name}' with args {fn_args}")

            tool_fn = _TOOL_FUNCTIONS.get(fn_name)
            if tool_fn is None:
                result = {"error": f"Unknown tool: {fn_name}"}
            else:
                result = await tool_fn(**fn_args)

            function_responses.append(
                genai_types.Part(
                    function_response=genai_types.FunctionResponse(
                        name=fn_name,
                        response={"result": result},
                    )
                )
            )

        # Append model's tool-call turn and tool results to history
        contents.append(candidate.content)
        contents.append(
            genai_types.Content(
                role="user",
                parts=function_responses,
            )
        )

    return "I'm sorry, I was unable to complete your request after several attempts. Please try rephrasing your question."

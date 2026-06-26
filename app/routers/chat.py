"""
Chat Router — AI Climate Intelligence Assistant
================================================
POST /api/v1/chat        → standard JSON response
POST /api/v1/chat/stream → SSE streaming response (token-by-token)
"""

import logging
import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.llm_agent import run_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["AI Climate Assistant"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's current message")
    history: List[ChatMessage] = Field(
        default=[],
        description="Prior conversation turns (most recent last). Max 20 turns."
    )


class ChatResponse(BaseModel):
    reply: str
    cached: bool = False


# ---------------------------------------------------------------------------
# Standard (non-streaming) endpoint
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_200_OK, response_model=ChatResponse)
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """
    Single-turn chat endpoint.
    Handles trivial greeting pre-filtering, caching, and agentic tool calling.
    """
    try:
        history = [{"role": m.role, "content": m.content} for m in request.history[-20:]]
        reply = await run_agent(message=request.message, history=history)
        return {"reply": reply, "cached": False}
    except RuntimeError as e:
        # Configuration errors (e.g., missing API key)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request. Please try again.",
        )


# ---------------------------------------------------------------------------
# Streaming endpoint (SSE — Server-Sent Events)
# ---------------------------------------------------------------------------

@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint using Server-Sent Events.
    The LLM response is streamed token-by-token for a real-time typing effect.
    Each SSE event is: `data: <json>\\n\\n`
    Final event: `data: [DONE]\\n\\n`
    """
    async def event_generator():
        try:
            history = [{"role": m.role, "content": m.content} for m in request.history[-20:]]

            from app.services.llm_agent import (
                _is_trivial, _LLMResponseCache, _get_client, _SYSTEM_PROMPT,
                TOOL_DECLARATIONS, _TOOL_FUNCTIONS
            )
            from google.genai import types as genai_types

            # Pre-filter trivial messages
            trivial = _is_trivial(request.message)
            if trivial:
                # Stream the pre-canned reply word by word
                for word in trivial.split(" "):
                    payload = json.dumps({"token": word + " "})
                    yield f"data: {payload}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Check cache
            cache_suffix = "|".join(
                [f"{h['role']}:{h['content'][:60]}" for h in history[-2:]]
            )
            cache_key = f"{request.message[:120]}|{cache_suffix}"
            cached = _LLMResponseCache.get(cache_key)
            if cached:
                # Stream the cached response
                for word in cached.split(" "):
                    payload = json.dumps({"token": word + " "})
                    yield f"data: {payload}\n\n"
                yield "data: [DONE]\n\n"
                return

            client = _get_client()

            # Build conversation
            contents = []
            for turn in history:
                role = "user" if turn["role"] == "user" else "model"
                contents.append(
                    genai_types.Content(
                        role=role,
                        parts=[genai_types.Part(text=turn["content"])]
                    )
                )
            contents.append(
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=request.message)]
                )
            )

            tools = genai_types.Tool(function_declarations=TOOL_DECLARATIONS)
            config = genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                tools=[tools],
                temperature=0.4,
            )

            # Agentic loop with streaming on the final answer step
            MAX_TURNS = 5
            for turn_idx in range(MAX_TURNS):
                if turn_idx < MAX_TURNS - 1:
                    # Non-streaming for tool-call turns (so we can intercept function calls)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=config,
                    )
                    candidate = response.candidates[0]
                    fn_calls = [
                        part.function_call
                        for part in candidate.content.parts
                        if hasattr(part, "function_call") and part.function_call is not None
                    ]

                    if not fn_calls:
                        # No tool call — stream final text
                        final_text = "".join(
                            part.text
                            for part in candidate.content.parts
                            if hasattr(part, "text") and part.text
                        )
                        _LLMResponseCache.set(cache_key, final_text)
                        for word in final_text.split(" "):
                            payload = json.dumps({"token": word + " "})
                            yield f"data: {payload}\n\n"
                        break

                    # Execute tool calls
                    function_responses = []
                    for fn_call in fn_calls:
                        fn_name = fn_call.name
                        fn_args = dict(fn_call.args) if fn_call.args else {}
                        logger.info(f"Stream Agent: calling tool '{fn_name}' with args {fn_args}")
                        # Emit a status ping so the UI can show a loading indicator
                        status_payload = json.dumps({"status": f"Fetching data: {fn_name}({', '.join(fn_args.keys())})"})
                        yield f"data: {status_payload}\n\n"

                        tool_fn = _TOOL_FUNCTIONS.get(fn_name)
                        result = await tool_fn(**fn_args) if tool_fn else {"error": f"Unknown tool: {fn_name}"}
                        function_responses.append(
                            genai_types.Part(
                                function_response=genai_types.FunctionResponse(
                                    name=fn_name,
                                    response={"result": result},
                                )
                            )
                        )

                    contents.append(candidate.content)
                    contents.append(
                        genai_types.Content(role="user", parts=function_responses)
                    )

                else:
                    # Last resort non-streaming fallback
                    fallback = await run_agent(request.message, history)
                    for word in fallback.split(" "):
                        payload = json.dumps({"token": word + " "})
                        yield f"data: {payload}\n\n"

            yield "data: [DONE]\n\n"

        except RuntimeError as e:
            err = json.dumps({"error": str(e)})
            yield f"data: {err}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Stream chat error: {e}", exc_info=True)
            err = json.dumps({"error": "An error occurred. Please try again."})
            yield f"data: {err}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

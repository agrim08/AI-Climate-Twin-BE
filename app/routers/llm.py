import os
import time
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.llm_service import LLMService
from app.schemas.llm import ChatbotRequest, ChatbotResponse

# Configure logger for Chatbot Router
logger = logging.getLogger("app.chatbot")

router = APIRouter(prefix="/chatbot", tags=["AI Climate Chatbot"])

# Singleton cache for LLMService
_llm_service_instance = None

def get_llm_service() -> LLMService:
    """
    Dependency injection helper to obtain and reuse a singleton LLMService instance.
    This prevents reconstructing the service and reloading crops.json on every API request.
    """
    global _llm_service_instance
    if _llm_service_instance is None:
        try:
            logger.info("Initializing LLMService singleton instance...")
            _llm_service_instance = LLMService()
            logger.info("LLMService singleton instance initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize LLMService: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize chatbot reasoning engine."
            )
    return _llm_service_instance

@router.post(
    "/query",
    response_model=ChatbotResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a natural language question to the Climate Twin Chatbot",
    description=(
        "Processes user inquiries (e.g. crop recommendations, specific crop suitability check, "
        "or general climate report generation) based on localized climate parameters: temperature, "
        "rainfall, and drought risk."
    )
)
async def query_chatbot(
    request: ChatbotRequest,
    llm_service: LLMService = Depends(get_llm_service)
) -> ChatbotResponse:
    """
    Process a chatbot query with the given temperature, rainfall, and drought risk parameters.
    """
    start_time = time.time()
    logger.info(
        "Received chatbot query - Question: '%s', Temp: %.1f°C, Rainfall: %.1f mm, Drought Risk: '%s'",
        request.question,
        request.temperature,
        request.rainfall,
        request.drought_risk
    )

    try:
        # Centralized Request Validation Check
        if request.temperature < -50.0 or request.temperature > 60.0:
            raise ValueError("Temperature must be a realistic value between -50°C and 60°C.")
        if request.rainfall < 0.0:
            raise ValueError("Rainfall must be a non-negative number.")
        if not request.question.strip():
            raise ValueError("The question field cannot be empty.")

        # Process the question
        answer = llm_service.answer_user_question(
            question=request.question,
            temperature=request.temperature,
            rainfall=request.rainfall,
            drought_risk=request.drought_risk
        )

        # Check for unknown crops response
        if answer == "Crop not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"The requested crop could not be found in our database."
            )

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Chatbot query succeeded - Duration: %.2fms, HTTP Status: 200",
            duration_ms
        )

        metadata = {
            "processing_time_ms": round(duration_ms, 2),
            "crops_in_database": len(llm_service.crop_data)
        }

        return ChatbotResponse(
            success=True,
            answer=answer,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )

    except HTTPException as http_ex:
        # Re-raise HTTP exceptions to let FastAPI handle response statuses
        raise http_ex
    except ValueError as val_ex:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            "Chatbot query validation failed - Duration: %.2fms, Error: %s",
            duration_ms,
            str(val_ex)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_ex)
        )
    except Exception as ex:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Internal error processing chatbot query - Duration: %.2fms, Error: %s",
            duration_ms,
            str(ex),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred on the server while processing the query."
        )

@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Get Chatbot Health Status",
    description="Verifies the loading of crops metadata and LLMService engine health."
)
async def check_chatbot_health(
    llm_service: LLMService = Depends(get_llm_service)
) -> Dict[str, Any]:
    """
    FastAPI health check endpoint specifically for the Chatbot service.
    """
    try:
        crops_count = len(llm_service.crop_data)
        if crops_count == 0:
            raise ValueError("Crops database loaded 0 records.")

        return {
            "status": "healthy",
            "crops_loaded": crops_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Chatbot service health check failed: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chatbot reasoning service is unhealthy: {str(e)}"
        )

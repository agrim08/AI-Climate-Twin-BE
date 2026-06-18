from pydantic import BaseModel, Field
from typing import Optional, Any, Union, List
from datetime import datetime

class ChatbotRequest(BaseModel):
    question: str = Field(
        ...,
        description="The natural language question or request from the user",
        examples=["Can I grow rice?", "What crops can I grow in this area?", "Could you give me a climate report?"]
    )
    temperature: float = Field(
        ...,
        description="The ambient temperature in Celsius",
        examples=[22.0, 30.5]
    )
    rainfall: float = Field(
        ...,
        description="The annual or seasonal rainfall in mm",
        examples=[600.0, 1200.0]
    )
    drought_risk: str = Field(
        ...,
        description="The drought risk level (e.g., Low, Medium, High)",
        examples=["Low", "High"]
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Can I grow rice?",
                "temperature": 22.0,
                "rainfall": 600.0,
                "drought_risk": "Low"
            }
        }
    }

class ChatbotResponse(BaseModel):
    success: bool = Field(
        ...,
        description="Indicates if the query was processed successfully"
    )
    answer: Union[str, List[str]] = Field(
        ...,
        description="The generated answer from the chatbot reasoning engine"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="The UTC timestamp of when the response was generated"
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Optional execution or context metadata"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "answer": "Rice is not suitable because rainfall is below required range.",
                "timestamp": "2026-06-18T12:00:00Z",
                "metadata": {
                    "question_type": "suitability_check",
                    "crop_extracted": "Rice"
                }
            }
        }
    }

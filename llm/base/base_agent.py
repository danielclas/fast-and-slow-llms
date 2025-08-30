from typing import Protocol, Dict, Type, TypeVar, List, Any, Optional, Literal
from pydantic import BaseModel, Field
import json

T = TypeVar("T", bound=BaseModel)

class APIAction(BaseModel):
    """API action specification."""
    endpoint: str = Field(..., description="API endpoint path")
    method: Literal["GET", "POST", "PUT", "DELETE"] = Field(..., description="HTTP method")
    params: str = Field(..., description="Query parameters as query string")
    payload: str = Field(..., description="Request payload as JSON string")
    
class AgentResponse(BaseModel):
    """Agent response with structured API actions."""
    action_sequence: List[APIAction] = Field(..., description="List of API actions to perform")
    reasoning: str = Field(..., description="Reasoning for the decisions")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")

class LLMClient(Protocol):
    def complete(self, system: str, user: str, schema: Type[T]) -> T: ...

class BaseAgent:
    """
    Generic email processing agent: defines a consistent .run(email_text) API.
    Analyzes emails and determines appropriate API action sequences.
    """
    def __init__(self, llm: LLMClient, api_context: Optional[str] = None):
        self.llm = llm
        self.model_name = getattr(self, "model_name", None)
        base_system_prompt = getattr(self, "system_prompt")
        self.user_template = getattr(self, "user_template")
        
        # Include API context in system prompt if provided
        if api_context:
            self.system_prompt = f"{base_system_prompt}\n\n{api_context}"
        else:
            self.system_prompt = base_system_prompt

    def run(self, email_text: str) -> str:
        """
        Process email and return the API action sequence as a string.
        Uses structured output internally but returns JSON string for compatibility.
        """
        user = self.user_template.format(email_text=email_text)
        structured_response = self.llm.complete(
            system=self.system_prompt, 
            user=user, 
            schema=AgentResponse
        )
        # Return the full structured response as JSON string for compatibility with runner
        return json.dumps(structured_response.model_dump(), ensure_ascii=False)

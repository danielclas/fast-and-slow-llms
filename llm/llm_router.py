from __future__ import annotations
from typing import Literal, List, Dict, Any
from pydantic import BaseModel, Field, ValidationError

from llm.client import LLMClient

Route = Literal["S1", "S2"]

class RouteDecision(BaseModel):
    route: Route = Field(..., description="The routing decision (S1 or S2)")
    reasons: List[str] = Field(..., description="List of reasons for the decision")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level")

ROUTER_SYSTEM_PROMPT = """You are an intelligent email routing system. Your job is to analyze incoming business emails and decide whether they should be handled by:

S1 (Fast Agent): For simple, straightforward requests that can be handled quickly
- Simple queries (account balances, basic lookups)
- Standard transactions
- Clear, unambiguous requests
- Routine operations

S2 (Deliberative Agent): For complex requests requiring careful analysis
- Multi-step processes
- Ambiguous or unclear requests
- Complex business logic
- Cases requiring additional context or clarification

Analyze the email content, complexity, and urgency to make the best routing decision."""

ROUTER_USER_TEMPLATE = """Email to route:

{email_text}

Analyze this email and determine:
1. Which agent (S1 or S2) should handle it
2. Your reasoning for this decision
3. Key signals that influenced your choice
4. Your confidence level (0.0 to 1.0)

Consider factors like:
- Complexity of the request
- Clarity of the information provided
- Number of steps required
- Potential for ambiguity
- Urgency indicators"""


# ---- router ----
class LLMAgentsRouter:
    """
    LLM-based email router that intelligently routes emails to appropriate agents.
    
    Uses structured output from LLM to make routing decisions with reasoning,
    confidence scores, and extracted signals from the email content.
    """
    
    def __init__(self, llm: LLMClient):
        """
        Initialize the router with an LLM client.
        
        Args:
            llm: LLMClient instance for making structured completions
        """
        self.llm = llm

    def decide(self, email_text: str) -> RouteDecision:
        """
        Analyze email and return full routing decision with reasoning.
        
        Args:
            email_text: The email content to analyze for routing
            
        Returns:
            RouteDecision: Structured decision with route, reasons, signals, and confidence
        """
        user = ROUTER_USER_TEMPLATE.format(email_text=email_text)
        return self.llm.complete(ROUTER_SYSTEM_PROMPT, user, RouteDecision)
     
class SingleAgentRouter:
    """
    Baseline router that always routes to a specific agent.
    Used for measuring individual agent performance without intelligent routing.
    """
    
    def __init__(self, agent: Route):
        """
        Initialize router to always route to the specified agent.
        
        Args:
            agent: Either "S1" or "S2" - the agent to always route to
        """
        if agent not in ["S1", "S2"]:
            raise ValueError(f"Agent must be 'S1' or 'S2', got '{agent}'")
        self.agent = agent
    
    def decide(self, email_text: str) -> RouteDecision:
        """
        Always return the same agent, regardless of email content.
        
        Args:
            email_text: The email content (ignored for baseline routing)
            
        Returns:
            RouteDecision: Hardcoded decision for the specified agent
        """
        return RouteDecision(
            route=self.agent,
            reasons=[f"Baseline routing: always using agent {self.agent}"],
            confidence=1.0
        )
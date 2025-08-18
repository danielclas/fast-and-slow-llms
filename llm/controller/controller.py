from typing import Protocol, Literal
from llm.llm_router import RouteDecision

Route = Literal["S1", "S2"]

class Router(Protocol):
    """Protocol defining the interface that routers must implement."""
    def decide(self, email_text: str) -> RouteDecision:
        """Analyze email and return full routing decision with reasoning."""
        ...

class Controller:
    """
    Email routing controller that coordinates routing decisions.
    
    Acts as a facade over routing logic, providing a clean interface
    for the runner. Always returns full RouteDecision objects with
    reasoning, confidence, and signals for transparency and debugging.
    
    Could be extended to support multiple routers, fallback strategies,
    or routing policies.
    """
    def __init__(self, router: Router):
        self.router = router
    
    def route(self, email_text: str) -> RouteDecision:
        """
        Route an email and return the full routing decision.
        
        Args:
            email_text: The email content to analyze
            
        Returns:
            RouteDecision: Full decision including route, reasons, signals, and confidence
        """
        return self.router.decide(email_text)

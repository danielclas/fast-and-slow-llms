from typing import Protocol, Literal
from llm.llm_router import RouteDecision

Route = Literal["S1", "S2"]

class Router(Protocol):
    def decide(self, email_text: str) -> RouteDecision:
        """Analyze email and return full routing decision with reasoning."""
        ...

class Controller:
    """
    Email routing controller that coordinates routing decisions.
    
    Acts as a facade over routing logic, providing a clean interface
    for the runner. Always returns full RouteDecision objects with
    reasoning, confidence, and signals for transparency and debugging.
    """
    def __init__(self, router: Router, confidence_threshold: float = 0.5):
        """
        Initialize the controller with a router and confidence threshold.
        
        Args:
            router: The routing implementation to use
            confidence_threshold: Minimum confidence required to trust routing decision
        """
        self.router = router
        self.confidence_threshold = confidence_threshold
    
    def route(self, email_text: str) -> RouteDecision:
        """
        Route an email and return the full routing decision.
        
        Args:
            email_text: The email content to analyze
            
        Returns:
            RouteDecision: Full decision including route, reasons, signals, and confidence
        """
        decision = self.router.decide(email_text)
        if decision.confidence < self.confidence_threshold:
            decision.route = "S2"
            decision.reasons = ["Low confidence in routing decision"]
        return decision

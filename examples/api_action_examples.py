# examples/api_action_examples.py
"""
Simple examples of API actions using the clean schema.
"""

from llm.base.base_agent import APIAction, AgentResponse

# Example 1: Customer balance inquiry
balance_inquiry = APIAction(
    endpoint="accounts-receivable/customer",
    method="GET",
    params={
        "customer_id": "CUST123",
        "include_aging": True
    }
)

# Example 2: Payment lookup
payment_lookup = APIAction(
    endpoint="accounts-receivable/payments",
    method="GET", 
    params={
        "reference": "PAY-456789",
        "status": "posted"
    }
)

# Example 3: Create new invoice (with payload)
create_invoice = APIAction(
    endpoint="accounts-receivable/invoices",
    method="POST",
    params={},
    payload={
        "customer_id": "CUST123",
        "amount": 1500.00,
        "due_date": "2024-02-15",
        "description": "Monthly service fee"
    }
)

# Example agent response for: "How much does customer ABC owe?"
simple_response = AgentResponse(
    action_sequence=[balance_inquiry],
    reasoning="Customer is asking for their current balance. Single API call to get balance and aging info.",
    confidence=0.95
)

# Example agent response for: "Did payment PAY-456789 go through and update customer CUST123's balance?"
complex_response = AgentResponse(
    action_sequence=[payment_lookup, balance_inquiry],
    reasoning="Need to check payment status first, then get updated customer balance to confirm.",
    confidence=0.85
)

if __name__ == "__main__":
    # Show what the JSON output looks like
    import json
    
    print("Simple balance inquiry:")
    print(json.dumps(simple_response.dict(), indent=2))
    
    print("\nComplex payment + balance check:")
    print(json.dumps(complex_response.dict(), indent=2))

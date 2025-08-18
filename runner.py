import argparse
from pathlib import Path
from typing import Dict
from pydantic import BaseModel
from io_utils import read_jsonl
from llm.base.base_agent import BaseAgent
from llm.controller.controller import Controller
from llm.llm_router import LLMRouter
from llm.s1.s1_agent import AgentS1
from llm.s2.s2_agent import AgentS2
from llm.client import LLMClient
import json 

class EmailRecord(BaseModel):
    """Simple email record from dataset."""
    id: str
    email_text: str

def process_dataset(
    dataset_path: str,
    run_dir: str,
    controller: Controller,               # has .route(email_text) -> "S1"/"S2"
    agents: Dict[str, BaseAgent],   # {"S1": AgentS1(...), "S2": AgentS2(...)} with .run(email_text)->str
) -> None:
    """
    Process the entire dataset at once, writing enriched results to merged.jsonl
    """
    out_merged = str(Path(run_dir) / "merged.jsonl")
    
    # Ensure output directory exists
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    
    # Clear output file if it exists (overwrite mode)
    if Path(out_merged).exists():
        Path(out_merged).unlink()

    processed = 0
    for sample_data in read_jsonl(dataset_path):
        try:
            # Validate and parse the email record
            sample = EmailRecord.model_validate(sample_data)
        except Exception as e:
            print(f"Warning: Invalid email record format: {e}")
            print(f"Skipping: {sample_data}")
            continue

        email_text = sample.email_text
        
        # Get full routing decision with reasoning
        route_decision = controller.route(email_text)
        route = route_decision.route

        # Select agent based on route, fallback to S2 then S1
        agent = agents.get(route) or agents.get("S2") or agents.get("S1")
        raw_response = agent.run(email_text)

        # Parse the structured agent response
        try:
            agent_response = json.loads(raw_response)
            
            # Extract structured components
            action_sequence = agent_response.get("action_sequence", [])
            reasoning = agent_response.get("reasoning", "")
            agent_confidence = agent_response.get("confidence", 0.0)
            
            # Build enriched response with both raw and parsed data
            enriched = {
                **sample.model_dump(),
                "run": {
                    "route_pred": route,
                    "route_decision": {
                        "route": route_decision.route,
                        "reasons": route_decision.reasons,

                        "confidence": route_decision.confidence
                    },
                    "agent": {
                        "name": agent.__class__.__name__,
                        "raw": raw_response,  # Original JSON string
                        "parsed": {
                            "action_sequence": action_sequence,
                            "reasoning": reasoning,
                            "confidence": agent_confidence,
                            "num_actions": len(action_sequence)
                        }
                    }
                }
            }
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback if parsing fails
            print(f"Warning: Failed to parse agent response for {sample.id}: {e}")
            enriched = {
                **sample.model_dump(),
                "run": {
                    "route_pred": route,
                    "route_decision": {
                        "route": route_decision.route,
                        "reasons": route_decision.reasons,

                        "confidence": route_decision.confidence
                    },
                    "agent": {
                        "name": agent.__class__.__name__,
                        "raw": raw_response,
                        "parsed": None,
                        "parse_error": str(e)
                    }
                }
            }
        
        # Write enriched result
        with open(out_merged, "a", encoding="utf-8") as f:
            f.write(json.dumps(enriched, ensure_ascii=False) + "\n")
        
        processed += 1
        if processed % 10 == 0:
            print(f"Processed {processed} samples...")

    print(f"Completed processing {processed} samples. Results written to {out_merged}")


def main():
    ap = argparse.ArgumentParser(description="Process email dataset through LLM router and agents")
    ap.add_argument("--dataset", required=True, help="Path to input JSONL dataset")
    ap.add_argument("--run-dir", required=True, help="Output directory for results")
    args = ap.parse_args()

    # Initialize LLM client and components
    router_llm_client = LLMClient()
    router = LLMRouter(llm=router_llm_client)
    controller = Controller(router=router)
    
    # Create separate LLM clients for each agent with their preferred models
    s1_llm_client = LLMClient(model="gpt-4o-mini")  # Fast model for S1
    s2_llm_client = LLMClient(model="gpt-4o")       # Deliberative model for S2
    
    agents = {
        "S1": AgentS1(llm=s1_llm_client),
        "S2": AgentS2(llm=s2_llm_client),
    }

    process_dataset(
        dataset_path=args.dataset,
        run_dir=args.run_dir,
        controller=controller,
        agents=agents,
    )


if __name__ == "__main__":
    main()
